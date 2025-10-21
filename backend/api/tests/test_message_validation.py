"""
Unit tests for message validation module
Tests emoji-only, gibberish, and irrelevance detection
"""

import pytest
from django.test import TestCase
from api.message_validation import (
    is_emoji_only,
    is_gibberish,
    is_irrelevant_answer,
    categorize_invalid_message,
    get_corrective_message
)


class TestEmojiDetection(TestCase):
    """Test emoji-only message detection"""
    
    def test_single_emoji(self):
        """Single emoji should be detected"""
        self.assertTrue(is_emoji_only("👍"))
        self.assertTrue(is_emoji_only("🤔"))
        self.assertTrue(is_emoji_only("😂"))
    
    def test_multiple_emojis(self):
        """Multiple emojis should be detected"""
        self.assertTrue(is_emoji_only("👍👍👍"))
        self.assertTrue(is_emoji_only("😂😂😂"))
        self.assertTrue(is_emoji_only("🔥🔥"))
    
    def test_emoji_with_text(self):
        """Emoji with text should NOT be detected as emoji-only"""
        self.assertFalse(is_emoji_only("ok 👍"))
        self.assertFalse(is_emoji_only("yes please"))
        self.assertFalse(is_emoji_only("I think 🤔"))
        self.assertFalse(is_emoji_only("The answer is 42"))
    
    def test_punctuation_only(self):
        """Punctuation only should be detected as emoji-only"""
        self.assertTrue(is_emoji_only("???"))
        self.assertTrue(is_emoji_only("!!!"))
        self.assertTrue(is_emoji_only("..."))
    
    def test_empty_message(self):
        """Empty message should return False"""
        self.assertFalse(is_emoji_only(""))
        self.assertFalse(is_emoji_only("   "))


class TestGibberishDetection(TestCase):
    """Test gibberish message detection"""
    
    def test_random_characters(self):
        """Random character sequences should be detected"""
        self.assertTrue(is_gibberish("asdkjasd"))
        self.assertTrue(is_gibberish("hfjhfhf"))
        self.assertTrue(is_gibberish("xyzxyzxyz"))
    
    def test_mixed_gibberish(self):
        """Mixed random chars with numbers/punctuation should be detected"""
        self.assertTrue(is_gibberish("asdkjasd 123???"))
        self.assertTrue(is_gibberish("fjfj!@#$"))
    
    def test_excessive_repetition(self):
        """Excessive character repetition should be detected"""
        self.assertTrue(is_gibberish("aaaaaaa"))
        self.assertTrue(is_gibberish("!!!!!!!!"))
        self.assertTrue(is_gibberish("xxxxxxx"))
    
    def test_valid_numeric_answers(self):
        """Numeric answers should NOT be detected as gibberish"""
        self.assertFalse(is_gibberish("42"))
        self.assertFalse(is_gibberish("3.14"))
        self.assertFalse(is_gibberish("100"))
        # With numeric expected answer
        self.assertFalse(is_gibberish("42", expected_answer="42"))
    
    def test_valid_short_answers(self):
        """Valid short answers should NOT be detected as gibberish"""
        self.assertFalse(is_gibberish("NaOH"))
        self.assertFalse(is_gibberish("photosynthesis"))
        self.assertFalse(is_gibberish("oxygen"))
    
    def test_valid_sentences(self):
        """Valid sentences should NOT be detected as gibberish"""
        self.assertFalse(is_gibberish("My answer is 42"))
        self.assertFalse(is_gibberish("The process is called photosynthesis"))
        self.assertFalse(is_gibberish("It uses light energy"))
    
    def test_empty_message(self):
        """Empty message should be treated as gibberish"""
        self.assertTrue(is_gibberish(""))
        self.assertTrue(is_gibberish("   "))


class TestIrrelevanceDetection(TestCase):
    """Test irrelevant answer detection"""
    
    def test_completely_irrelevant(self):
        """Completely off-topic answers should be detected"""
        is_irr, score = is_irrelevant_answer(
            "I like pizza",
            "Explain photosynthesis"
        )
        self.assertTrue(is_irr)
        self.assertLess(score, 0.3)
    
    def test_personal_irrelevant(self):
        """Personal statements unrelated to question should be detected"""
        is_irr, score = is_irrelevant_answer(
            "My dog is cute",
            "What is NaOH?"
        )
        self.assertTrue(is_irr)
        self.assertLess(score, 0.3)
    
    def test_relevant_answer(self):
        """Relevant answers should NOT be detected as irrelevant"""
        is_irr, score = is_irrelevant_answer(
            "Plants use sunlight to make food",
            "Explain photosynthesis"
        )
        self.assertFalse(is_irr)
        self.assertGreater(score, 0.3)
    
    def test_partial_keyword_match(self):
        """Answers with some keyword overlap should be relevant"""
        is_irr, score = is_irrelevant_answer(
            "It's a chemical base",
            "What is NaOH?"
        )
        self.assertFalse(is_irr)
        self.assertGreater(score, 0.0)
    
    def test_question_about_question(self):
        """Questions about questions should be relevant (handled by intent classifier)"""
        # This is more of an edge case - the keyword check may pass
        is_irr, score = is_irrelevant_answer(
            "What is photosynthesis?",
            "Explain photosynthesis"
        )
        self.assertFalse(is_irr)  # Should match keyword "photosynthesis"


class TestCategorization(TestCase):
    """Test overall message categorization"""
    
    def test_emoji_categorization(self):
        """Emoji-only messages should return 'emoji' category"""
        category = categorize_invalid_message("👍", "What is photosynthesis?")
        self.assertEqual(category, "emoji")
    
    def test_gibberish_categorization(self):
        """Gibberish messages should return 'gibberish' category"""
        category = categorize_invalid_message("asdkjasd", "What is photosynthesis?")
        self.assertEqual(category, "gibberish")
    
    def test_irrelevant_categorization(self):
        """Irrelevant messages should return 'irrelevant' category"""
        category = categorize_invalid_message(
            "I like pizza", 
            "What is photosynthesis?",
            "Plants use sunlight to make food"
        )
        self.assertEqual(category, "irrelevant")
    
    def test_valid_message(self):
        """Valid messages should return None"""
        category = categorize_invalid_message(
            "Plants use sunlight",
            "What is photosynthesis?"
        )
        self.assertIsNone(category)
    
    def test_priority_emoji_over_gibberish(self):
        """Emoji check should take priority over gibberish"""
        # A message that could be both emoji and gibberish
        category = categorize_invalid_message("😂😂😂", "What is photosynthesis?")
        self.assertEqual(category, "emoji")


class TestCorrectiveMessages(TestCase):
    """Test corrective message generation"""
    
    def test_emoji_corrective_english(self):
        """Emoji corrective message in English"""
        message = get_corrective_message("emoji", "What is photosynthesis?", "english")
        self.assertIn("emoji", message.lower())
        self.assertIn("words", message.lower())
        self.assertIn("What is photosynthesis?", message)
    
    def test_gibberish_corrective_english(self):
        """Gibberish corrective message in English"""
        message = get_corrective_message("gibberish", "What is NaOH?", "english")
        self.assertIn("understand", message.lower())
        self.assertIn("clearly", message.lower())
        self.assertIn("What is NaOH?", message)
    
    def test_irrelevant_corrective_english(self):
        """Irrelevant corrective message in English"""
        message = get_corrective_message("irrelevant", "Explain photosynthesis", "english")
        self.assertIn("unrelated", message.lower())
        self.assertIn("Explain photosynthesis", message)
    
    def test_emoji_corrective_tanglish(self):
        """Emoji corrective message in Tanglish"""
        message = get_corrective_message("emoji", "What is photosynthesis?", "tanglish")
        self.assertIn("emoji", message.lower())
        self.assertIn("words", message.lower())
        self.assertIn("What is photosynthesis?", message)
    
    def test_question_included_in_message(self):
        """All corrective messages should include the original question"""
        for category in ["emoji", "gibberish", "irrelevant"]:
            message = get_corrective_message(category, "Test question here", "english")
            self.assertIn("Test question here", message)


class TestEdgeCases(TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_very_short_valid_answer(self):
        """Very short but valid answers should be accepted"""
        # Single word with vowels
        self.assertFalse(is_gibberish("yes"))
        self.assertFalse(is_gibberish("no"))
        self.assertFalse(is_gibberish("true"))
        
        # Numeric
        self.assertFalse(is_gibberish("5"))
        self.assertFalse(is_gibberish("0"))
    
    def test_chemical_formulas(self):
        """Chemical formulas should be accepted"""
        self.assertFalse(is_gibberish("H2O"))
        self.assertFalse(is_gibberish("NaOH"))
        self.assertFalse(is_gibberish("CO2"))
    
    def test_mixed_language_answer(self):
        """Mixed language (Tanglish) answers should be accepted"""
        self.assertFalse(is_gibberish("Photosynthesis nadakum"))
        self.assertFalse(is_gibberish("Answer is sunlight energy"))
    
    def test_unicode_characters(self):
        """Answers with unicode/accented characters should be handled"""
        self.assertFalse(is_gibberish("café"))
        self.assertFalse(is_gibberish("naïve"))
    
    def test_none_inputs(self):
        """None or empty inputs should be handled gracefully"""
        # Emoji detection
        self.assertFalse(is_emoji_only(None))
        
        # Gibberish detection
        self.assertTrue(is_gibberish(None))
        
        # Irrelevance detection
        is_irr, score = is_irrelevant_answer(None, "Question?")
        self.assertTrue(is_irr)
        self.assertEqual(score, 0.0)
