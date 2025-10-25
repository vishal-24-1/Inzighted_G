#!/usr/bin/env python
"""
Test script for Tanglish Agent Implementation
Run this after migrations to verify the implementation
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.models import User, Document, ChatSession, QuestionItem, EvaluatorResult
from api.gemini_client import gemini_client
from api.tanglish_prompts import fallback_intent_classifier


def test_intent_classifier_fallback():
    """Test the fallback intent classifier with sample messages"""
    print("\n=== Testing Intent Classifier Fallback ===")
    
    test_cases = [
        ("Resonance la current and voltage in phase irukkum.", "DIRECT_ANSWER"),
        ("I think it's 5V, but why does it change?", "MIXED"),
        ("What is resonance?", "RETURN_QUESTION"),
        ("Enna sollureenga?", "RETURN_QUESTION"),
        ("The answer is capacitive reactance equals inductive reactance at resonance frequency.", "DIRECT_ANSWER"),
    ]
    
    for message, expected in test_cases:
        result = fallback_intent_classifier(message)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{message[:50]}...' -> {result} (expected: {expected})")


def test_gemini_methods():
    """Test Gemini client new methods"""
    print("\n=== Testing Gemini Client Methods ===")
    
    # Test classify_intent
    print("\n1. Testing classify_intent()...")
    test_message = "The current is in phase with voltage at resonance."
    test_question = "What happens to the phase relationship at resonance?"
    try:
        result = gemini_client.classify_intent(test_message, current_question=test_question)
        print(f"   ✅ Intent classification result: {result}")
        if result.get("valid"):
            print(f"      Token: {result.get('token')}")
        else:
            print(f"      Invalid message: {result.get('message')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test generate_questions_structured
    print("\n2. Testing generate_questions_structured()...")
    test_context = "Resonance in RLC circuits occurs when inductive and capacitive reactances are equal."
    try:
        questions = gemini_client.generate_questions_structured(test_context, total_questions=3)
        if questions:
            print(f"   ✅ Generated {len(questions)} questions")
            for q in questions[:2]:
                print(f"      - {q.get('archetype')}: {q.get('question_text', '')[:60]}...")
        else:
            print(f"   ⚠️  No questions generated")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test evaluate_answer
    print("\n3. Testing evaluate_answer()...")
    context = "Question about resonance"
    expected = "Current and voltage are in phase at resonance"
    student = "At resonance, current and voltage have same phase"
    try:
        evaluation = gemini_client.evaluate_answer(context, expected, student)
        print(f"   ✅ Evaluation: score={evaluation.get('score')}, XP={evaluation.get('XP')}")
        print(f"      Explanation: {evaluation.get('explanation', '')[:60]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_models():
    """Test that new models are available"""
    print("\n=== Testing Database Models ===")
    
    try:
        # Check QuestionItem model
        from api.models import QuestionItem
        print("✅ QuestionItem model available")
        
        # Check EvaluatorResult model
        from api.models import EvaluatorResult
        print("✅ EvaluatorResult model available")
        
        # Check ChatSession has language field
        from api.models import ChatSession
        fields = [f.name for f in ChatSession._meta.get_fields()]
        if 'language' in fields:
            print("✅ ChatSession.language field available")
        else:
            print("❌ ChatSession.language field missing")
        
        # Check ChatMessage has classifier_token field
        from api.models import ChatMessage
        fields = [f.name for f in ChatMessage._meta.get_fields()]
        if 'classifier_token' in fields:
            print("✅ ChatMessage.classifier_token field available")
        else:
            print("❌ ChatMessage.classifier_token field missing")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_urls():
    """Test that new URL endpoints are registered"""
    print("\n=== Testing URL Configuration ===")
    
    from django.urls import reverse
    
    endpoints = [
        'agent_session_start',
        'agent_respond',
        'agent_status',
        'agent_language_toggle',
    ]
    
    for endpoint in endpoints:
        try:
            if endpoint in ['agent_respond', 'agent_status', 'agent_language_toggle']:
                # These need a session_id parameter
                url = reverse(f'api:{endpoint}', kwargs={'session_id': '00000000-0000-0000-0000-000000000000'})
            else:
                url = reverse(f'api:{endpoint}')
            print(f"✅ {endpoint}: {url}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")


def main():
    """Run all tests"""
    print("=" * 70)
    print("Tanglish Agent Implementation - Test Suite")
    print("=" * 70)
    
    # Check if Gemini is available
    if gemini_client.is_available():
        print("\n✅ Gemini client initialized successfully")
    else:
        print("\n⚠️  Gemini client not available - check LLM_API_KEY")
    
    # Run tests
    test_models()
    test_urls()
    test_intent_classifier_fallback()
    
    if gemini_client.is_available():
        test_gemini_methods()
    else:
        print("\n⚠️  Skipping Gemini method tests (API key not configured)")
    
    print("\n" + "=" * 70)
    print("Test suite complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. If any tests failed, check migrations: python manage.py migrate")
    print("2. Verify .env has LLM_API_KEY and EMBEDDING_API_KEY")
    print("3. Test the API endpoints using the examples in TANGLISH_AGENT_IMPLEMENTATION.md")
    print("=" * 70)


if __name__ == '__main__':
    main()
