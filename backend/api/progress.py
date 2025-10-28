"""
Gamification Progress System

This module handles two independent gamification systems:
1. Streak System: Daily test completion tracking with milestone badges
2. Batch System: XP-based progression with stars and batch levels

Key Principles:
- XP is calculated as: SUM of all SessionInsight.xp_points across all completed sessions
  (SessionInsight.xp_points is the total XP earned in that session)
- Streak counts one test per day; missing a day resets the streak
- Earned milestone badges persist even after streak resets
- All updates use atomic transactions and idempotence checks

Implementation:
- update_on_test_completion(): Called per question evaluation, updates STREAK only
- process_session_completion(): Called when session completes, updates XP/BATCH
"""

from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging
import sentry_sdk
from django.db.models import Sum
from datetime import timedelta

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION (can be overridden in settings.py)
# ============================================================

# Streak milestone thresholds (days) and their badge names
STREAK_MILESTONES = getattr(settings, 'STREAK_MILESTONES', [
    (7, 'Bronze'),
    (15, 'Silver'),
    (30, 'Gold'),
    (45, 'Platinum'),
    (100, 'Diamond'),
])

# Batch progression sequence
BATCH_SEQUENCE = getattr(settings, 'BATCH_SEQUENCE', [
    'Bronze',
    'Silver',
    'Gold',
    'Platinum',
])

# Stars per batch (fixed at 5 as per requirements)
STARS_PER_BATCH = getattr(settings, 'STARS_PER_BATCH', 5)

# XP thresholds for each star (cumulative)
# Each star requires reaching these average XP points
STAR_XP_THRESHOLDS = getattr(settings, 'STAR_XP_THRESHOLDS', [
    100,   # Star 1: avg 100 XP
    200,   # Star 2: avg 200 XP
    300,   # Star 3: avg 300 XP
    400,   # Star 4: avg 400 XP
    500,  # Star 5: avg 500 XP (completes batch)
])


# ============================================================
# CORE PROGRESS UPDATE FUNCTIONS
# ============================================================

def update_on_test_completion(user, evaluator_result):
    """
    Update user's streak after a test evaluation is created.
    
    NOTE: This function ONLY handles STREAK updates per evaluation.
    XP/Batch updates are now handled at the SESSION level by process_session_completion().
    
    This function is called from agent_flow._evaluate_answer() immediately after
    creating an EvaluatorResult. It handles:
    1. Streak tracking (one test per day, reset on miss, milestone badges)
    
    Args:
        user: User instance (must be locked with select_for_update())
        evaluator_result: EvaluatorResult instance that was just created
        
    Returns:
        dict: Summary of changes made {
            'streak_updated': bool,
            'new_streak': int,
            'milestone_earned': str or None,
            'xp_updated': bool,  # Always False now (handled at session level)
            'new_avg_xp': int,
            'stars_earned': int,  # Always 0 now (handled at session level)
            'batch_upgraded': str or None,  # Always None now (handled at session level)
        }
        
    Raises:
        Exception: On database errors (should be caught by caller)
    """
    
    # Idempotence check: skip if already processed
    if evaluator_result.progress_processed:
        logger.info(f"Evaluation {evaluator_result.id} already processed for progress, skipping")
        return {
            'streak_updated': False,
            'new_streak': user.streak_current,
            'milestone_earned': None,
            'xp_updated': False,
            'new_avg_xp': user.total_xp_sum,
            'stars_earned': 0,
            'batch_upgraded': None,
        }
    
    try:
        with transaction.atomic():
            # Lock the user row for update to prevent race conditions
            from .models import User
            user = User.objects.select_for_update().get(pk=user.pk)
            
            # Get test completion date (use message creation time, convert to date in UTC)
            test_datetime = evaluator_result.message.created_at
            test_date = test_datetime.date()
            
            logger.info(f"Processing progress for user {user.id}, test date: {test_date}")
            
            # ============================================================
            # STREAK SYSTEM UPDATE
            # ============================================================
            
            streak_updated = False
            milestone_earned = None
            
            if user.streak_last_test_date is None:
                # First test ever
                user.streak_current = 1
                user.streak_last_test_date = test_date
                streak_updated = True
                logger.info(f"First test - streak initialized to 1")
                
            elif test_date == user.streak_last_test_date:
                # Same day - don't increment streak, but still process XP
                logger.info(f"Same day test (no streak increment)")
                pass
                
            elif test_date == user.streak_last_test_date + timezone.timedelta(days=1):
                # Next consecutive day - increment streak
                user.streak_current += 1
                user.streak_last_test_date = test_date
                streak_updated = True
                logger.info(f"Consecutive day - streak incremented to {user.streak_current}")
                
            else:
                # Missed days - reset streak to 1
                old_streak = user.streak_current
                user.streak_current = 1
                user.streak_last_test_date = test_date
                streak_updated = True
                logger.info(f"Streak reset from {old_streak} to 1 (missed days)")
            
            # Check for milestone achievement
            if streak_updated:
                for threshold, badge_name in STREAK_MILESTONES:
                    if user.streak_current == threshold:
                        # Earned new milestone
                        milestone_str = f"{badge_name} ({threshold})"
                        
                        # Ensure streak_earned_batches is a list
                        if not isinstance(user.streak_earned_batches, list):
                            user.streak_earned_batches = []
                        
                        # Add milestone if not already earned
                        if milestone_str not in user.streak_earned_batches:
                            user.streak_earned_batches.append(milestone_str)
                            milestone_earned = milestone_str
                            logger.info(f"Milestone earned: {milestone_str}")
                        break
            
            # ============================================================
            # BATCH SYSTEM UPDATE (XP-based)
            # ============================================================
            # NOTE: XP/Batch updates are now deferred to process_session_completion()
            # which is called when the entire session/batch is completed.
            # This ensures we calculate avg XP per session and sum those averages.
            
            # Mark evaluation as processed (for streak idempotence)
            evaluator_result.progress_processed = True
            evaluator_result.save(update_fields=['progress_processed'])
            
            # Save user changes
            user.save()
            
            logger.info(f"Progress update complete for user {user.id}")
            
            return {
                'streak_updated': streak_updated,
                'new_streak': user.streak_current,
                'milestone_earned': milestone_earned,
                'xp_updated': False,  # XP now updated at session level
                'new_avg_xp': user.total_xp_sum,  # Current value (unchanged here)
                'stars_earned': 0,  # Stars now awarded at session level
                'batch_upgraded': None,  # Batch now upgraded at session level
            }
            
    except Exception as e:
        logger.error(f"Error updating progress for user {user.id}: {e}", exc_info=True)
        sentry_sdk.capture_exception(e, extras={
            'component': 'progress',
            'function': 'update_on_test_completion',
            'user_id': str(user.id),
            'evaluator_result_id': str(evaluator_result.id),
        })
        raise


def process_session_completion(session):
    """
    Process XP and batch updates when a tutoring session/batch completes.
    
    This implements the new XP calculation model:
    - Calculate average XP per session (avg of all EvaluatorResults in that session)
    - Add that session average to the running sum (stored in user.total_xp_sum)
    - Update user.xp_points = total_xp_sum (sum of all session averages)
    - Update stars and batch based on new xp_points value
    
    Args:
        session: ChatSession instance that just completed
        
    Returns:
        dict: Summary of changes {
            'session_avg_xp': float,
            'session_question_count': int,
            'new_total_xp': int,  # Sum of session averages
            'sessions_completed': int,
            'stars_earned': int,
            'batch_upgraded': str or None,
        }
        
    Raises:
        Exception: On database errors (should be caught by caller)
    """
    
    from .models import EvaluatorResult, User, TutoringQuestionBatch, SessionInsight
    
    try:
        with transaction.atomic():
            # Lock the user row for update
            user = User.objects.select_for_update().get(pk=session.user.pk)

            # Try to get the question batch for this session (if exists)
            batch = TutoringQuestionBatch.objects.filter(session=session).first()

            # Get all EvaluatorResults for this session
            evaluator_results = EvaluatorResult.objects.filter(
                message__session=session
            ).values_list('xp', flat=True)

            evaluator_results_list = list(evaluator_results)

            if not evaluator_results_list:
                logger.warning(f"No EvaluatorResults found for session {session.id}, skipping XP update")
                return {
                    'session_avg_xp': 0,
                    'session_question_count': 0,
                    'new_total_xp': user.total_xp_sum,
                    'sessions_completed': SessionInsight.objects.filter(user=user, status='completed').count(),
                    'stars_earned': 0,
                    'batch_upgraded': None,
                }

            # Calculate session average XP (float)
            session_total_xp = sum(evaluator_results_list)
            session_question_count = len(evaluator_results_list)
            session_avg_xp = session_total_xp / session_question_count

            logger.info(f"Session {session.id}: {session_question_count} questions, total={session_total_xp}, avg={session_avg_xp:.2f}")
            
            # OLD SEMANTICS (before this change):
            # - total_xp_sum = cumulative sum of all individual question XP
            # - total_tests_taken = count of all questions evaluated
            # - xp_points = total_xp_sum / total_tests_taken (global average)
            
            # NEW SEMANTICS (Option A implementation):
            # - total_xp_sum = sum of per-session average XP values
            # - total_tests_taken = count of sessions completed
            # - xp_points = total_xp_sum (sum of session averages, displayed directly)
            
            # Use batch fields to avoid double-processing and make updates idempotent
            old_total_xp = user.total_xp_sum
            stars_earned = 0
            batch_upgraded = None

            # If we have a batch record, use its xp_processed/session_xp_avg fields
            if batch:
                if not batch.xp_processed:
                    # Add the session avg (store int in batch for compatibility)
                    batch.session_xp_avg = int(round(session_avg_xp))
                    batch.xp_processed = True
                    batch.save(update_fields=['session_xp_avg', 'xp_processed'])

                    # Add the session avg to the running sum
                    user.total_xp_sum += batch.session_xp_avg
                    logger.info(f"User {user.id} total_xp_sum updated: {old_total_xp} + {batch.session_xp_avg} = {user.total_xp_sum}")
                else:
                    # Already processed - no-op
                    logger.info(f"Session {session.id} already processed for XP (batch.session_xp_avg={batch.session_xp_avg})")
            else:
                # No batch record: still process using evaluator results and mark via session (non-persistent)
                # This allows processing regardless of batch existence/completion
                session_xp_int = int(round(session_avg_xp))
                user.total_xp_sum += session_xp_int

                logger.info(f"User {user.id} total_xp_sum updated (no batch record): {old_total_xp} + {session_xp_int} = {user.total_xp_sum}")
            
            # NOTE: We DO NOT recompute from SessionInsight here because:
            # 1. SessionInsight is generated asynchronously (often after this function runs)
            # 2. Recomputing would overwrite the XP we just added above
            # 3. The batch.xp_processed flag already ensures idempotence
            # 4. total_xp_sum is the source of truth, SessionInsight.xp_points is derived from it

            # Calculate ACTUAL total XP by summing all completed SessionInsights for star calculation
            # This gives us the real cumulative XP earned across all sessions
            insight_qs = SessionInsight.objects.filter(user=user, status='completed')
            agg = insight_qs.aggregate(total=Sum('xp_points'))
            actual_total_xp = agg.get('total') or 0
            
            # If no completed insights yet, use the current session's total XP
            if actual_total_xp == 0:
                actual_total_xp = session_total_xp

            # Update stars and batch based on ACTUAL total XP (not session averages)
            result = update_on_xp(user, actual_total_xp)
            stars_earned = result['stars_earned']
            batch_upgraded = result['batch_upgraded']

            # Save user changes
            user.save()
            
            logger.info(f"Session completion processed for user {user.id}: stars={stars_earned}, batch={batch_upgraded}")
            
            # Compute sessions completed for return
            sessions_completed = SessionInsight.objects.filter(user=user, status='completed').count()

            return {
                'session_avg_xp': session_avg_xp,
                'session_question_count': session_question_count,
                'new_total_xp': user.total_xp_sum,
                'sessions_completed': sessions_completed,
                'stars_earned': stars_earned,
                'batch_upgraded': batch_upgraded,
            }
            
    except Exception as e:
        logger.error(f"Error processing session completion for session {session.id}: {e}", exc_info=True)
        sentry_sdk.capture_exception(e, extras={
            'component': 'progress',
            'function': 'process_session_completion',
            'session_id': str(session.id),
        })
        raise


def update_on_xp(user, total_xp):
    """
    Update stars and batch progression based on total XP earned.
    
    This function calculates how many stars should be earned based on the
    user's actual total XP across all completed sessions, and handles batch 
    upgrades when all stars in a batch are completed.
    
    Args:
        user: User instance (already locked with select_for_update())
        total_xp: Current total XP value (sum of all SessionInsight.xp_points)
        
    Returns:
        dict: {
            'stars_earned': int,  # Number of NEW stars earned in this update
            'batch_upgraded': str or None,  # New batch name if upgraded, else None
        }
    """
    
    old_star_count = user.current_star
    old_batch = user.batch_current
    
    # Calculate how many stars should be earned based on total XP
    new_star_count = 0
    for threshold in STAR_XP_THRESHOLDS:
        if total_xp >= threshold:
            new_star_count += 1
        else:
            break
    
    # Cap stars at stars_per_batch (5)
    new_star_count = min(new_star_count, user.stars_per_batch)
    
    stars_earned = max(0, new_star_count - old_star_count)
    
    if stars_earned > 0:
        logger.info(f"Stars earned: {old_star_count} -> {new_star_count}")
        user.current_star = new_star_count
    
    # Check for batch upgrade (all stars completed)
    batch_upgraded = None
    if user.current_star >= user.stars_per_batch:
        # Find current batch index
        try:
            current_batch_idx = BATCH_SEQUENCE.index(user.batch_current)
        except ValueError:
            # Current batch not in sequence, default to first batch
            current_batch_idx = 0
            user.batch_current = BATCH_SEQUENCE[0]
        
        # Check if there's a next batch
        if current_batch_idx < len(BATCH_SEQUENCE) - 1:
            # Upgrade to next batch
            new_batch = BATCH_SEQUENCE[current_batch_idx + 1]
            user.batch_current = new_batch
            batch_upgraded = new_batch
            
            # Reset stars to 0 for new batch
            # (User will immediately earn stars based on their avg XP in the new batch)
            user.current_star = 0
            
            # Recalculate stars for new batch
            new_star_count_in_batch = 0
            for threshold in STAR_XP_THRESHOLDS:
                if total_xp >= threshold:
                    new_star_count_in_batch += 1
                else:
                    break
            user.current_star = min(new_star_count_in_batch, user.stars_per_batch)
            
            logger.info(f"Batch upgraded: {old_batch} -> {new_batch}, stars reset to {user.current_star}")
        else:
            # Already at max batch
            logger.info(f"Already at max batch ({user.batch_current}), capping stars at {user.stars_per_batch}")
            user.current_star = user.stars_per_batch
    
    return {
        'stars_earned': stars_earned,
        'batch_upgraded': batch_upgraded,
    }


def get_progress_summary(user):
    """
    Get comprehensive progress summary for a user.
    
    Args:
        user: User instance
        
    Returns:
        dict: {
            'streak': {
                'current': int,
                'last_test_date': str (YYYY-MM-DD) or None,
                'earned_milestones': list of str,
                'next_milestone': int or None,
                'progress_to_next': float (0-100),
            },
            'batch': {
                'current_batch': str,
                'current_star': int,
                'xp_points': int (sum of per-session averages),
                'total_tests_taken': int (session count),
                'stars_per_batch': int,
                'xp_to_next_star': int or None,
                'next_star_threshold': int or None,
            }
        }
    """
    
    # ============================================================
    # STREAK SUMMARY
    # ============================================================
    
    # Find next milestone
    next_milestone = None
    for threshold, _ in STREAK_MILESTONES:
        if user.streak_current < threshold:
            next_milestone = threshold
            break
    
    # Calculate progress to next milestone
    if next_milestone:
        progress_to_next = (user.streak_current / next_milestone) * 100
    else:
        # At or beyond max milestone
        progress_to_next = 100.0
    
    # Ensure streak_earned_batches is a list
    earned_milestones = user.streak_earned_batches if isinstance(user.streak_earned_batches, list) else []
    
    streak_summary = {
        'current': user.streak_current,
        'last_test_date': user.streak_last_test_date.isoformat() if user.streak_last_test_date else None,
        'earned_milestones': earned_milestones,
        'next_milestone': next_milestone,
        'progress_to_next': round(progress_to_next, 1),
    }
    
    # ============================================================
    # BATCH SUMMARY
    # ============================================================
    
    # Find next star threshold
    next_star_threshold = None
    xp_to_next_star = None
    
    # Calculate ACTUAL total XP by summing all SessionInsight.xp_points (this is the real XP earned)
    from .models import SessionInsight
    from django.db.models import Sum
    
    sessions = SessionInsight.objects.filter(user=user, status='completed')
    sessions_completed = sessions.count()
    
    # Get the REAL total XP (sum of all session XP, not averages)
    total_xp_aggregate = sessions.aggregate(total=Sum('xp_points'))
    actual_total_xp = total_xp_aggregate.get('total') or 0
    
    if user.current_star < user.stars_per_batch:
        # Get threshold for next star
        next_star_idx = user.current_star  # 0-indexed
        if next_star_idx < len(STAR_XP_THRESHOLDS):
            next_star_threshold = STAR_XP_THRESHOLDS[next_star_idx]
            xp_to_next_star = max(0, next_star_threshold - actual_total_xp)

    batch_summary = {
        'current_batch': user.batch_current,
        'current_star': user.current_star,
        'xp_points': actual_total_xp,  # Use ACTUAL total XP from SessionInsights
        'total_tests_taken': sessions_completed,
        'stars_per_batch': user.stars_per_batch,
        'xp_to_next_star': xp_to_next_star,
        'next_star_threshold': next_star_threshold,
    }
    
    return {
        'streak': streak_summary,
        'batch': batch_summary,
    }


def normalize_streak_on_view(user):
    """
    Ensure streak_current reflects whether the user has missed yesterday when
    the user opens the app or refreshes the progress view.

    Behavior:
    - If user.streak_last_test_date is None -> keep streak_current as-is (usually 0)
    - If last_test_date is today or yesterday -> no change
    - If last_test_date is older than yesterday -> set streak_current to 0

    This function is intentionally separate from update_on_test_completion
    so that streak updates when a test is completed remain unchanged.
    """
    try:
        with transaction.atomic():
            from .models import User
            u = User.objects.select_for_update().get(pk=user.pk)

            if u.streak_last_test_date is None:
                # No tests recorded yet - keep current streak (expected 0)
                return False

            today = timezone.now().date()
            yesterday = today - timedelta(days=1)

            if u.streak_last_test_date == today or u.streak_last_test_date == yesterday:
                # streak is up-to-date
                return False

            # Missed one or more days -> show 0 until user takes a new test
            if u.streak_current != 0:
                u.streak_current = 0
                u.save(update_fields=['streak_current'])
                return True

            return False
    except Exception as e:
        logger.error(f"Error normalizing streak on view for user {user.id}: {e}")
        try:
            sentry_sdk.capture_exception(e, extras={
                'component': 'progress',
                'function': 'normalize_streak_on_view',
                'user_id': str(user.id),
            })
        except Exception:
            pass
        return False


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_milestone_name(streak_count):
    """
    Get the milestone badge name for a given streak count.
    
    Args:
        streak_count: Current streak count
        
    Returns:
        str: Milestone name (e.g., "Bronze (7)") or None if no milestone reached
    """
    for threshold, badge_name in reversed(STREAK_MILESTONES):
        if streak_count >= threshold:
            return f"{badge_name} ({threshold})"
    return None


def get_batch_index(batch_name):
    """
    Get the index of a batch in the sequence.
    
    Args:
        batch_name: Name of the batch
        
    Returns:
        int: Index in BATCH_SEQUENCE, or 0 if not found
    """
    try:
        return BATCH_SEQUENCE.index(batch_name)
    except ValueError:
        return 0
