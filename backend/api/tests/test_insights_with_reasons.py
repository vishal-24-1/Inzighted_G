"""
Tests for BoostMe insights generation with reasons.
Verifies that insights include reason arrays explaining why each zone was identified.
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from api.gemini_client import GeminiLLMClient
from api.models import SessionInsight, ChatSession, Document

User = get_user_model()


class InsightsWithReasonsTestCase(TestCase):
    """Test insight generation includes reasons for each zone"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        self.document = Document.objects.create(
            user=self.user,
            filename='test_doc.pdf',
            file_size=1024,
            status='completed'
        )
        self.session = ChatSession.objects.create(
            user=self.user,
            document=self.document,
            title='Test Session'
        )
        self.client_instance = GeminiLLMClient()

    def test_generate_insights_with_valid_reasons(self):
        """Test that LLM response with reasons is correctly parsed and validated"""
        # Mock LLM response with all required fields including reasons
        mock_response = json.dumps({
            "focus_zone": ["Weak area 1", "Weak area 2"],
            "focus_zone_reasons": ["Low score in Q2 and Q5", "Concept confusion observed"],
            "steady_zone": ["Strong area 1", "Strong area 2"],
            "steady_zone_reasons": ["Correct answers in Q1, Q3", "Consistent performance"],
            "edge_zone": ["Growth area 1", "Growth area 2"],
            "edge_zone_reasons": ["Nearly correct in Q4", "Right approach, minor errors"]
        })

        # Patch the generate_response method
        with patch.object(self.client_instance, 'generate_response', return_value=mock_response):
            qa_records = [
                {
                    'question': 'Test Q1',
                    'expected_answer': 'Answer 1',
                    'answer': 'Student answer 1',
                    'explanation': 'Good answer',
                    'score': 0.9,
                    'xp': 10,
                    'correct': True
                },
                {
                    'question': 'Test Q2',
                    'expected_answer': 'Answer 2',
                    'answer': 'Student answer 2',
                    'explanation': 'Needs improvement',
                    'score': 0.3,
                    'xp': 3,
                    'correct': False
                }
            ]

            insights = self.client_instance.generate_boostme_insights(qa_records, language='english')

            # Verify all zones present
            self.assertIn('focus_zone', insights)
            self.assertIn('steady_zone', insights)
            self.assertIn('edge_zone', insights)

            # Verify all reason arrays present
            self.assertIn('focus_zone_reasons', insights)
            self.assertIn('steady_zone_reasons', insights)
            self.assertIn('edge_zone_reasons', insights)

            # Verify structure
            self.assertEqual(len(insights['focus_zone']), 2)
            self.assertEqual(len(insights['focus_zone_reasons']), 2)
            self.assertEqual(len(insights['steady_zone_reasons']), 2)
            self.assertEqual(len(insights['edge_zone_reasons']), 2)

    def test_generate_insights_missing_reasons_uses_fallback(self):
        """Test that missing reasons trigger fallback generation"""
        # Mock LLM response WITHOUT reasons
        mock_response = json.dumps({
            "focus_zone": ["Weak area 1", "Weak area 2"],
            "steady_zone": ["Strong area 1", "Strong area 2"],
            "edge_zone": ["Growth area 1", "Growth area 2"]
        })

        with patch.object(self.client_instance, 'generate_response', return_value=mock_response):
            qa_records = [{'question': 'Q1', 'answer': 'A1', 'score': 0.5, 'xp': 5, 'explanation': 'OK'}]

            insights = self.client_instance.generate_boostme_insights(qa_records)

            # Should have fallback reasons
            self.assertIn('focus_zone_reasons', insights)
            self.assertIn('steady_zone_reasons', insights)
            self.assertIn('edge_zone_reasons', insights)

            # Fallback reasons should be arrays of 2
            self.assertEqual(len(insights['focus_zone_reasons']), 2)
            self.assertIsInstance(insights['focus_zone_reasons'][0], str)

    def test_fallback_insights_include_reasons(self):
        """Test that fallback generator produces reasons"""
        qa_records = [
            {'question': 'Q1', 'answer': 'A1', 'score': 0.9, 'xp': 10, 'explanation': 'Excellent', 'correct': True},
            {'question': 'Q2', 'answer': 'A2', 'score': 0.2, 'xp': 2, 'explanation': 'Weak', 'correct': False}
        ]

        insights = self.client_instance._generate_fallback_boostme_insights(qa_records)

        # Verify reasons present
        self.assertIn('focus_zone_reasons', insights)
        self.assertIn('steady_zone_reasons', insights)
        self.assertIn('edge_zone_reasons', insights)

        # Verify structure
        self.assertEqual(len(insights['focus_zone_reasons']), 2)
        self.assertEqual(len(insights['steady_zone_reasons']), 2)
        self.assertEqual(len(insights['edge_zone_reasons']), 2)

        # Verify content is meaningful
        for reason in insights['focus_zone_reasons']:
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason), 5)  # Not just empty strings

    def test_empty_qa_records_fallback_has_reasons(self):
        """Test that even with no QA data, fallback provides reasons"""
        insights = self.client_instance._generate_fallback_boostme_insights([])

        # Should still have all reason fields
        self.assertIn('focus_zone_reasons', insights)
        self.assertIn('steady_zone_reasons', insights)
        self.assertIn('edge_zone_reasons', insights)

        self.assertEqual(len(insights['focus_zone_reasons']), 2)

    def test_session_insight_model_persists_reasons(self):
        """Test that SessionInsight model can save and retrieve reasons"""
        insight = SessionInsight.objects.create(
            session=self.session,
            user=self.user,
            document=self.document,
            focus_zone=["Weak 1", "Weak 2"],
            focus_zone_reasons=["Reason 1", "Reason 2"],
            steady_zone=["Strong 1", "Strong 2"],
            steady_zone_reasons=["Reason A", "Reason B"],
            edge_zone=["Edge 1", "Edge 2"],
            edge_zone_reasons=["Reason X", "Reason Y"],
            xp_points=50,
            accuracy=75.0,
            total_qa_pairs=4,
            status='completed'
        )

        # Retrieve from DB
        retrieved = SessionInsight.objects.get(id=insight.id)

        # Verify reasons persisted
        self.assertEqual(retrieved.focus_zone_reasons, ["Reason 1", "Reason 2"])
        self.assertEqual(retrieved.steady_zone_reasons, ["Reason A", "Reason B"])
        self.assertEqual(retrieved.edge_zone_reasons, ["Reason X", "Reason Y"])

    def test_backward_compatibility_null_reasons(self):
        """Test that insights work when reasons are null (backward compatibility)"""
        insight = SessionInsight.objects.create(
            session=self.session,
            user=self.user,
            document=self.document,
            focus_zone=["Weak 1", "Weak 2"],
            steady_zone=["Strong 1", "Strong 2"],
            edge_zone=["Edge 1", "Edge 2"],
            xp_points=50,
            accuracy=75.0,
            total_qa_pairs=4,
            status='completed'
            # Note: NOT setting reason fields - should remain null
        )

        retrieved = SessionInsight.objects.get(id=insight.id)

        # Reasons should be null/None
        self.assertIsNone(retrieved.focus_zone_reasons)
        self.assertIsNone(retrieved.steady_zone_reasons)
        self.assertIsNone(retrieved.edge_zone_reasons)

        # Zones should still work
        self.assertEqual(len(retrieved.focus_zone), 2)
