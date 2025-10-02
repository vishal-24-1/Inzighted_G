#!/usr/bin/env python3
"""
Test script for the new batch-based question generation system
"""

import os
import sys
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.models import User, Document, ChatSession, TutoringQuestionBatch
from api.rag_query import generate_tutoring_question, generate_question_batch_for_session

def create_test_user_and_document():
    """Create a test user and document for testing"""
    try:
        # Create test user
        test_email = f"test_batch_{uuid.uuid4().hex[:8]}@example.com"
        user = User.objects.create_user(
            username=test_email,
            email=test_email,
            name="Test Batch User",
            password="testpassword123"
        )
        
        # Create test document (assuming you have some documents in the system)
        documents = Document.objects.filter(status='completed').first()
        if not documents:
            print("⚠️  No completed documents found in the system")
            print("   Please upload and process a document first using the main application")
            return None, None
        
        print(f"✅ Created test user: {user.email}")
        print(f"✅ Using existing document: {documents.filename}")
        return user, documents
        
    except Exception as e:
        print(f"❌ Error creating test user/document: {e}")
        return None, None

def test_batch_question_generation():
    """Test the new batch question generation system"""
    print("🚀 Testing Batch Question Generation System\n")
    print("=" * 60)
    
    # Create test user and get document
    user, document = create_test_user_and_document()
    if not user or not document:
        return False
    
    try:
        # Create a test session
        session = ChatSession.objects.create(
            user=user,
            title=f"Test Batch Session - {document.filename}",
            document=document
        )
        print(f"✅ Created test session: {session.id}")
        
        # Test batch generation
        print("\n📝 Testing batch generation...")
        question_batch = generate_question_batch_for_session(
            session_id=str(session.id),
            document_id=str(document.id),
            total_questions=5  # Generate 5 questions for testing
        )
        
        print(f"✅ Generated question batch with {question_batch.total_questions} questions")
        print(f"   Status: {question_batch.status}")
        print(f"   Source Document: {question_batch.source_doc_id}")
        
        # Display generated questions
        print("\n📋 Generated Questions:")
        for i, question in enumerate(question_batch.questions, 1):
            print(f"   {i}. {question}")
        
        # Test sequential question delivery
        print("\n🔄 Testing sequential question delivery...")
        for i in range(3):  # Test first 3 questions
            question = generate_tutoring_question(
                user_id=str(user.id),
                document_id=str(document.id),
                session_id=str(session.id)
            )
            
            # Refresh the batch to see updated status
            question_batch.refresh_from_db()
            print(f"   Question {i+1}: {question}")
            print(f"   Progress: {question_batch.current_question_index + 1}/{question_batch.total_questions}")
        
        print("\n✅ Batch question generation test completed successfully!")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        session.delete()
        user.delete()
        print("✅ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on failure
        try:
            if 'session' in locals():
                session.delete()
            if 'user' in locals():
                user.delete()
        except:
            pass
        
        return False

def test_fallback_to_legacy():
    """Test that the system falls back to legacy generation when no session_id is provided"""
    print("\n🔄 Testing fallback to legacy generation...")
    
    user, document = create_test_user_and_document()
    if not user or not document:
        return False
    
    try:
        # Test without session_id (should use legacy method)
        question = generate_tutoring_question(
            user_id=str(user.id),
            document_id=str(document.id)
            # No session_id provided - should fallback to legacy
        )
        
        print(f"✅ Legacy fallback question: {question}")
        
        # Cleanup
        user.delete()
        print("✅ Legacy fallback test completed")
        return True
        
    except Exception as e:
        print(f"❌ Legacy fallback test failed: {e}")
        try:
            user.delete()
        except:
            pass
        return False

def main():
    """Run all tests"""
    print("🧪 Starting Question Batch System Tests\n")
    
    test_results = {
        'batch_generation': test_batch_question_generation(),
        'legacy_fallback': test_fallback_to_legacy()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The batch question generation system is working correctly.")
    else:
        print("⚠️  SOME TESTS FAILED. Please check the error messages above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
