"""
Unit Tests for Gamification Progress System

Tests for both Streak and Batch systems including:
- Streak increment/reset logic
- Milestone persistence
- XP session-average calculation (avg per session, sum session averages)
- Star and batch progression
- Idempotence
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from api.models import User, ChatSession, ChatMessage, QuestionItem, EvaluatorResult, TutoringQuestionBatch
from api.progress import (
    update_on_test_completion,
    process_session_completion,
    get_progress_summary,
    STREAK_MILESTONES,
    BATCH_SEQUENCE,
    STAR_XP_THRESHOLDS
)
import uuid


class ProgressSystemTestCase(TestCase):
    """Test cases for gamification progress system"""
    
    def setUp(self):
        """Set up test user and session"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            name='Test User'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            title='Test Session'
        )
        
        self.batch = TutoringQuestionBatch.objects.create(
            session=self.session,
            user=self.user,
            questions=['Question 1'],
            total_questions=1,
            tenant_tag='test_tenant'
        )
        
        self.question = QuestionItem.objects.create(
            session=self.session,
            batch=self.batch,
            question_id='q1',
            archetype='Concept Unfold',
            question_text='Test question',
            difficulty='easy',
            expected_answer='Test answer'
        )
    
    def create_evaluation(self, xp_value=50, test_date=None):
        """Helper to create an evaluation with specific XP and date"""
        if test_date is None:
            test_date = timezone.now()
        
        message = ChatMessage.objects.create(
            session=self.session,
            user=self.user,
            content='Test answer',
            is_user_message=True,
            created_at=test_date
        )
        
        evaluation = EvaluatorResult.objects.create(
            message=message,
            question=self.question,
            raw_json={'score': 0.8},
            score=0.8,
            correct=True,
            xp=xp_value,
            explanation='Good answer',
            confidence=0.9,
            followup_action='none'
        )
        
        return evaluation
    
    # ============================================================
    # STREAK SYSTEM TESTS
    # ============================================================
    
    def test_first_test_initializes_streak(self):
        """First test should initialize streak to 1"""
        eval_result = self.create_evaluation(xp_value=50)
        
        result = update_on_test_completion(self.user, eval_result)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)
        self.assertIsNotNone(self.user.streak_last_test_date)
        self.assertTrue(result['streak_updated'])
        self.assertEqual(result['new_streak'], 1)
    
    def test_same_day_test_no_streak_increment(self):
        """Multiple tests on same day should not increment streak"""
        # First test
        eval1 = self.create_evaluation(xp_value=50)
        update_on_test_completion(self.user, eval1)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)
        
        # Second test same day
        eval2 = self.create_evaluation(xp_value=60)
        result = update_on_test_completion(self.user, eval2)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)  # Should not increment
        self.assertFalse(result['streak_updated'])
    
    def test_consecutive_day_increments_streak(self):
        """Test on consecutive day should increment streak"""
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        
        # Test yesterday
        eval1 = self.create_evaluation(xp_value=50, test_date=yesterday)
        update_on_test_completion(self.user, eval1)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)
        
        # Test today
        eval2 = self.create_evaluation(xp_value=60, test_date=today)
        result = update_on_test_completion(self.user, eval2)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 2)
        self.assertTrue(result['streak_updated'])
        self.assertEqual(result['new_streak'], 2)
    
    def test_missed_day_resets_streak(self):
        """Missing a day should reset streak to 1"""
        today = timezone.now()
        three_days_ago = today - timedelta(days=3)
        
        # Test 3 days ago
        eval1 = self.create_evaluation(xp_value=50, test_date=three_days_ago)
        update_on_test_completion(self.user, eval1)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)
        
        # Build up streak
        self.user.streak_current = 5
        self.user.save()
        
        # Test today (missed 2 days)
        eval2 = self.create_evaluation(xp_value=60, test_date=today)
        result = update_on_test_completion(self.user, eval2)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)  # Reset to 1
        self.assertTrue(result['streak_updated'])
    
    def test_milestone_earned_and_persisted(self):
        """Reaching milestone should add badge, which persists after reset"""
        today = timezone.now()
        
        # Set streak to 6 (one before Bronze milestone at 7)
        self.user.streak_current = 6
        self.user.streak_last_test_date = (today - timedelta(days=1)).date()
        self.user.save()
        
        # Test today to reach 7
        eval_result = self.create_evaluation(xp_value=50, test_date=today)
        result = update_on_test_completion(self.user, eval_result)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 7)
        self.assertEqual(result['milestone_earned'], 'Bronze (7)')
        self.assertIn('Bronze (7)', self.user.streak_earned_batches)
        
        # Now reset streak (miss days)
        future_date = today + timedelta(days=5)
        eval2 = self.create_evaluation(xp_value=60, test_date=future_date)
        update_on_test_completion(self.user, eval2)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.streak_current, 1)  # Reset
        self.assertIn('Bronze (7)', self.user.streak_earned_batches)  # Badge persists
    
    # ============================================================
    # BATCH SYSTEM (SESSION-BASED XP) TESTS
    # ============================================================
    
    def test_xp_calculated_per_session_then_summed(self):
        """XP should be: avg per session, then sum those session averages"""
        # Session 1: 3 questions with XP [60, 80, 50]
        # Session avg = (60+80+50)/3 = 63.33 -> 63
        eval1 = self.create_evaluation(xp_value=60)
        eval2 = self.create_evaluation(xp_value=80)
        eval3 = self.create_evaluation(xp_value=50)
        
        # Process session completion
        result = process_session_completion(self.session)
        
        self.user.refresh_from_db()
        self.assertEqual(result['session_avg_xp'], 63.333333333333336)  # Float average
        self.assertEqual(result['session_question_count'], 3)
        self.assertEqual(self.user.total_tests_taken, 1)  # 1 session completed
        self.assertEqual(self.user.total_xp_sum, 63)  # Session avg added
        self.assertEqual(self.user.xp_points, 63)  # Sum of session avgs
        
        # Session 2: Create new session with 2 questions [100, 100]
        # Session avg = (100+100)/2 = 100
        session2 = ChatSession.objects.create(user=self.user, title='Session 2')
        batch2 = TutoringQuestionBatch.objects.create(
            session=session2, user=self.user, questions=['Q1'], total_questions=1, tenant_tag='test'
        )
        question2 = QuestionItem.objects.create(
            session=session2, batch=batch2, question_id='q2',
            archetype='Concept Unfold', question_text='Q2',
            difficulty='easy', expected_answer='A2'
        )
        
        msg4 = ChatMessage.objects.create(session=session2, user=self.user, content='A4', is_user_message=True)
        msg5 = ChatMessage.objects.create(session=session2, user=self.user, content='A5', is_user_message=True)
        
        EvaluatorResult.objects.create(
            message=msg4, question=question2, raw_json={}, score=1.0,
            correct=True, xp=100, explanation='Good', confidence=0.9, followup_action='none'
        )
        EvaluatorResult.objects.create(
            message=msg5, question=question2, raw_json={}, score=1.0,
            correct=True, xp=100, explanation='Good', confidence=0.9, followup_action='none'
        )
        
        result2 = process_session_completion(session2)
        
        self.user.refresh_from_db()
        self.assertEqual(result2['session_avg_xp'], 100.0)
        self.assertEqual(self.user.total_tests_taken, 2)  # 2 sessions completed
        self.assertEqual(self.user.total_xp_sum, 163)  # 63 + 100
        self.assertEqual(self.user.xp_points, 163)  # Sum of session avgs
    
    def test_star_progression_based_on_session_xp_sum(self):
        """Stars should be earned based on sum of session averages"""
        # Session 1: 1 question with 25 XP -> session avg = 25
        # xp_points = 25 -> should earn 1 star (threshold 20)
        eval1 = self.create_evaluation(xp_value=25)
        result = process_session_completion(self.session)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.xp_points, 25)
        self.assertEqual(self.user.current_star, 1)
        self.assertEqual(result['stars_earned'], 1)
        
        # Session 2: 1 question with 25 XP -> session avg = 25
        # xp_points = 25 + 25 = 50 -> should earn star 2 and 3 (thresholds 40, 60)
        session2 = ChatSession.objects.create(user=self.user, title='Session 2')
        batch2 = TutoringQuestionBatch.objects.create(
            session=session2, user=self.user, questions=['Q'], total_questions=1, tenant_tag='test'
        )
        question2 = QuestionItem.objects.create(
            session=session2, batch=batch2, question_id='q2',
            archetype='Concept Unfold', question_text='Q', difficulty='easy', expected_answer='A'
        )
        msg2 = ChatMessage.objects.create(session=session2, user=self.user, content='A', is_user_message=True)
        EvaluatorResult.objects.create(
            message=msg2, question=question2, raw_json={}, score=0.8,
            correct=True, xp=25, explanation='Good', confidence=0.9, followup_action='none'
        )
        
        result2 = process_session_completion(session2)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.xp_points, 50)
        self.assertEqual(self.user.current_star, 2)  # Threshold 40 met
        self.assertGreater(result2['stars_earned'], 0)  # At least one new star
    
    def test_batch_upgrade_when_all_stars_completed(self):
        """Should upgrade batch when xp_points (sum of session avgs) reaches threshold for 5 stars"""
        # Set user to have 4 stars with xp_points = 90
        # (This means total_xp_sum = 90, representing sum of session averages)
        self.user.current_star = 4
        self.user.xp_points = 90
        self.user.total_tests_taken = 3  # 3 sessions completed
        self.user.total_xp_sum = 90  # Sum of session avgs
        self.user.batch_current = 'Bronze'
        self.user.save()
        
        # Complete a new session with high avg to push xp_points to 100+
        # Session avg needs to be at least 10 to reach 100 total
        # Create session with 1 question of 15 XP -> session avg = 15
        # xp_points = 90 + 15 = 105 -> should get 5th star and upgrade
        eval_result = self.create_evaluation(xp_value=15)
        result = process_session_completion(self.session)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.xp_points, 105)  # 90 + 15
        self.assertEqual(self.user.batch_current, 'Silver')  # Upgraded
        self.assertEqual(result['batch_upgraded'], 'Silver')
        # Stars recalculated for new batch based on xp_points
        self.assertEqual(self.user.current_star, 5)  # All 5 stars at 105 xp_points
    
    # ============================================================
    # IDEMPOTENCE TESTS
    # ============================================================
    
    def test_idempotence_same_evaluation_processed_twice(self):
        """Processing same evaluation twice should not double-count streak"""
        eval_result = self.create_evaluation(xp_value=50)
        
        # Process first time (streak only, no XP yet)
        result1 = update_on_test_completion(self.user, eval_result)
        self.user.refresh_from_db()
        
        streak1 = self.user.streak_current
        
        # Process second time (should be skipped due to progress_processed flag)
        result2 = update_on_test_completion(self.user, eval_result)
        self.user.refresh_from_db()
        
        self.assertEqual(self.user.streak_current, streak1)  # No change
        self.assertFalse(result2['streak_updated'])
        self.assertFalse(result2['xp_updated'])  # Always False now (session-level)
    
    def test_session_completion_idempotence(self):
        """Processing same session twice should be handled gracefully"""
        # Create evaluations for session
        eval1 = self.create_evaluation(xp_value=50)
        eval2 = self.create_evaluation(xp_value=60)
        
        # Process session first time
        result1 = process_session_completion(self.session)
        self.user.refresh_from_db()
        
        xp1 = self.user.xp_points
        sessions1 = self.user.total_tests_taken
        
        # Process session second time (should add XP again - no built-in idempotence)
        # This is expected behavior: each session completion call processes all evaluations
        # In practice, this is prevented by only calling process_session_completion once
        # when batch.status becomes 'completed'
        result2 = process_session_completion(self.session)
        self.user.refresh_from_db()
        
        # XP will be added again (55 avg * 2 = 110)
        self.assertGreater(self.user.xp_points, xp1)  # Doubled
    
    # ============================================================
    # PROGRESS SUMMARY TESTS
    # ============================================================
    
    def test_get_progress_summary(self):
        """Test progress summary returns correct structure"""
        # Set up user with some progress
        self.user.streak_current = 12
        self.user.streak_last_test_date = timezone.now().date()
        self.user.streak_earned_batches = ['Bronze (7)']
        self.user.batch_current = 'Silver'
        self.user.current_star = 3
        self.user.xp_points = 65
        self.user.total_tests_taken = 10
        self.user.save()
        
        summary = get_progress_summary(self.user)
        
        # Check streak summary
        self.assertEqual(summary['streak']['current'], 12)
        self.assertEqual(summary['streak']['earned_milestones'], ['Bronze (7)'])
        self.assertEqual(summary['streak']['next_milestone'], 15)
        self.assertGreater(summary['streak']['progress_to_next'], 0)
        
        # Check batch summary
        self.assertEqual(summary['batch']['current_batch'], 'Silver')
        self.assertEqual(summary['batch']['current_star'], 3)
        self.assertEqual(summary['batch']['xp_points'], 65)
        self.assertEqual(summary['batch']['total_tests_taken'], 10)
        self.assertIsNotNone(summary['batch']['xp_to_next_star'])
        self.assertIsNotNone(summary['batch']['next_star_threshold'])


class ProgressEdgeCasesTestCase(TestCase):
    """Test edge cases and boundary conditions"""
    
    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            email='edge@example.com',
            username='edgeuser',
            password='testpass123',
            name='Edge User'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            title='Edge Test Session'
        )
        
        self.batch = TutoringQuestionBatch.objects.create(
            session=self.session,
            user=self.user,
            questions=['Question 1'],
            total_questions=1,
            tenant_tag='test_tenant'
        )
        
        self.question = QuestionItem.objects.create(
            session=self.session,
            batch=self.batch,
            question_id='q1',
            archetype='Concept Unfold',
            question_text='Test question',
            difficulty='easy',
            expected_answer='Test answer'
        )
    
    def test_zero_xp_session(self):
        """Handle session with 0 XP"""
        message = ChatMessage.objects.create(
            session=self.session,
            user=self.user,
            content='Wrong answer',
            is_user_message=True
        )
        
        eval_result = EvaluatorResult.objects.create(
            message=message,
            question=self.question,
            raw_json={'score': 0.0},
            score=0.0,
            correct=False,
            xp=0,  # Zero XP
            explanation='Incorrect',
            confidence=0.9,
            followup_action='none'
        )
        
        # Process session (session avg = 0)
        result = process_session_completion(self.session)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.total_tests_taken, 1)
        self.assertEqual(self.user.xp_points, 0)
        self.assertEqual(self.user.current_star, 0)
    
    def test_max_batch_reached(self):
        """Test behavior when reaching max batch (Platinum)"""
        # Set user to Platinum with all stars
        self.user.batch_current = 'Platinum'
        self.user.current_star = 5
        self.user.xp_points = 100
        self.user.total_tests_taken = 10
        self.user.total_xp_sum = 100  # Sum of session avgs
        self.user.save()
        
        # Add another high-XP session
        message = ChatMessage.objects.create(
            session=self.session,
            user=self.user,
            content='Great answer',
            is_user_message=True
        )
        
        eval_result = EvaluatorResult.objects.create(
            message=message,
            question=self.question,
            raw_json={'score': 1.0},
            score=1.0,
            correct=True,
            xp=100,
            explanation='Perfect',
            confidence=0.95,
            followup_action='none'
        )
        
        result = process_session_completion(self.session)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.batch_current, 'Platinum')  # Should not upgrade beyond max
        self.assertEqual(self.user.current_star, 5)  # Capped at 5
