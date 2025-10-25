"""
Tests for automatic session timeout functionality
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from api.models import User, ChatSession, Document
from api.views.tutoring_views import is_session_expired, end_session_helper


class SessionTimeoutTestCase(TestCase):
    """Test automatic session timeout logic"""
    
    def setUp(self):
        """Create test user and session"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
    def test_is_session_expired_returns_false_for_new_session(self):
        """Test that newly created sessions are not expired"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Test Session',
            is_active=True
        )
        
        self.assertFalse(is_session_expired(session))
    
    def test_is_session_expired_returns_true_for_old_session(self):
        """Test that sessions older than timeout are expired"""
        timeout_mins = getattr(settings, 'SESSION_TIMEOUT_MINS', 15)
        
        # Create session with created_at in the past
        session = ChatSession.objects.create(
            user=self.user,
            title='Old Session',
            is_active=True
        )
        
        # Manually set created_at to past timeout
        session.created_at = timezone.now() - timedelta(minutes=timeout_mins + 1)
        session.save()
        
        self.assertTrue(is_session_expired(session))
    
    def test_is_session_expired_boundary_condition(self):
        """Test session exactly at timeout boundary"""
        timeout_mins = getattr(settings, 'SESSION_TIMEOUT_MINS', 15)
        
        session = ChatSession.objects.create(
            user=self.user,
            title='Boundary Session',
            is_active=True
        )
        
        # Set to exactly timeout duration
        session.created_at = timezone.now() - timedelta(minutes=timeout_mins)
        session.save()
        
        # At exact boundary, should still be valid (not expired)
        self.assertFalse(is_session_expired(session))
    
    def test_end_session_helper_marks_session_inactive(self):
        """Test that end_session_helper marks session as inactive"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Active Session',
            is_active=True
        )
        
        result = end_session_helper(session)
        
        # Refresh from database
        session.refresh_from_db()
        
        self.assertFalse(session.is_active)
        self.assertFalse(result['already_ended'])
        self.assertIsNotNone(result['total_messages'])
    
    def test_end_session_helper_idempotent(self):
        """Test that calling end_session_helper twice is idempotent"""
        session = ChatSession.objects.create(
            user=self.user,
            title='Session',
            is_active=True
        )
        
        # End session first time
        result1 = end_session_helper(session)
        self.assertFalse(result1['already_ended'])
        
        # End session second time
        result2 = end_session_helper(session)
        self.assertTrue(result2['already_ended'])
        
        # Session should still be inactive
        session.refresh_from_db()
        self.assertFalse(session.is_active)
    
    def test_end_session_helper_with_messages(self):
        """Test end_session_helper counts messages correctly"""
        from api.models import ChatMessage
        
        session = ChatSession.objects.create(
            user=self.user,
            title='Session with Messages',
            is_active=True
        )
        
        # Add some messages
        ChatMessage.objects.create(
            session=session,
            user=self.user,
            content='Test message 1',
            is_user_message=True
        )
        ChatMessage.objects.create(
            session=session,
            user=self.user,
            content='Test response 1',
            is_user_message=False
        )
        
        result = end_session_helper(session)
        
        self.assertEqual(result['total_messages'], 2)
        self.assertFalse(session.is_active)
