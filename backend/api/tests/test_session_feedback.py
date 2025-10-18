"""
Test suite for the Post-Session Feedback feature
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from api.models import ChatSession, SessionFeedback, Document
import uuid

User = get_user_model()


class SessionFeedbackAPITestCase(TestCase):
    """Test cases for SessionFeedback API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            name='Test User'
        )
        
        # Create test session
        self.session = ChatSession.objects.create(
            user=self.user,
            title='Test Tutoring Session',
            language='tanglish'
        )
        
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_submit_feedback_success(self):
        """Test successful feedback submission"""
        url = f'/api/sessions/{self.session.id}/feedback/'
        data = {
            'rating': 9,
            'liked': 'The questions were engaging',
            'improve': 'Add more hints',
            'skipped': False
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['feedback']['rating'], 9)
        self.assertEqual(response.data['feedback']['liked'], 'The questions were engaging')
        self.assertEqual(response.data['feedback']['improve'], 'Add more hints')
        self.assertFalse(response.data['feedback']['skipped'])

    def test_submit_feedback_without_improve_fails(self):
        """Test that feedback without 'improve' field fails when not skipped"""
        url = f'/api/sessions/{self.session.id}/feedback/'
        data = {
            'rating': 8,
            'liked': 'Good experience',
            'skipped': False
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_skip_feedback_success(self):
        """Test skipping feedback successfully"""
        url = f'/api/sessions/{self.session.id}/feedback/'
        data = {
            'skipped': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['feedback']['skipped'])

    def test_duplicate_feedback_fails(self):
        """Test that duplicate feedback for same session fails"""
        url = f'/api/sessions/{self.session.id}/feedback/'
        data = {
            'rating': 8,
            'improve': 'Test improvement',
            'skipped': False
        }
        
        # First submission
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second submission should fail
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already submitted', response2.data['error'].lower())

    def test_feedback_requires_authentication(self):
        """Test that feedback endpoint requires authentication"""
        self.client.force_authenticate(user=None)
        
        url = f'/api/sessions/{self.session.id}/feedback/'
        data = {
            'rating': 8,
            'improve': 'Test',
            'skipped': False
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_feedback_session_not_found(self):
        """Test feedback for non-existent session returns 404"""
        fake_session_id = uuid.uuid4()
        url = f'/api/sessions/{fake_session_id}/feedback/'
        data = {
            'rating': 8,
            'improve': 'Test',
            'skipped': False
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_existing_feedback(self):
        """Test retrieving existing feedback"""
        # Create feedback
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            rating=9,
            liked='Great!',
            improve='More examples',
            skipped=False
        )
        
        url = f'/api/sessions/{self.session.id}/feedback/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rating'], 9)
        self.assertEqual(response.data['liked'], 'Great!')

    def test_get_nonexistent_feedback(self):
        """Test retrieving feedback that doesn't exist returns 404"""
        url = f'/api/sessions/{self.session.id}/feedback/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('No feedback', response.data['message'])


class SessionFeedbackModelTestCase(TestCase):
    """Test cases for SessionFeedback model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='model@example.com',
            username='modeluser',
            password='testpass123',
            name='Model Test User'
        )
        
        self.session = ChatSession.objects.create(
            user=self.user,
            title='Model Test Session',
            language='tanglish'
        )

    def test_create_feedback(self):
        """Test creating a SessionFeedback instance"""
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            rating=8,
            liked='Good questions',
            improve='Better explanations',
            skipped=False
        )
        
        self.assertEqual(feedback.rating, 8)
        self.assertEqual(feedback.liked, 'Good questions')
        self.assertEqual(feedback.improve, 'Better explanations')
        self.assertFalse(feedback.skipped)
        self.assertEqual(feedback.session, self.session)
        self.assertEqual(feedback.user, self.user)

    def test_skipped_feedback(self):
        """Test creating skipped feedback"""
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            skipped=True
        )
        
        self.assertTrue(feedback.skipped)
        self.assertIsNone(feedback.rating)
        self.assertEqual(feedback.liked, '')
        self.assertEqual(feedback.improve, '')

    def test_feedback_str_representation(self):
        """Test string representation of feedback"""
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            rating=9,
            improve='Test',
            skipped=False
        )
        
        str_repr = str(feedback)
        self.assertIn('Rating: 9', str_repr)
        self.assertIn(self.session.get_title(), str_repr)

    def test_skipped_feedback_str_representation(self):
        """Test string representation of skipped feedback"""
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            skipped=True
        )
        
        str_repr = str(feedback)
        self.assertIn('Skipped', str_repr)

    def test_onetoone_relationship(self):
        """Test OneToOne relationship between Session and Feedback"""
        feedback = SessionFeedback.objects.create(
            session=self.session,
            user=self.user,
            rating=7,
            improve='Test',
            skipped=False
        )
        
        # Access feedback through session
        self.assertEqual(self.session.feedback, feedback)
        
        # Verify OneToOne constraint (trying to create another should fail)
        with self.assertRaises(Exception):
            SessionFeedback.objects.create(
                session=self.session,
                user=self.user,
                rating=8,
                improve='Another test',
                skipped=False
            )
