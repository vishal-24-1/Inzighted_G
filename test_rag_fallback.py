#!/usr/bin/env python3
"""
Quick test script to verify RAG fallback functionality
"""

import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

def test_rag_fallback():
    """Test that RAG fallback works when no context is found"""
    try:
        from api.rag_query import query_rag
        from api.auth import get_tenant_tag
        
        print("Testing RAG fallback functionality...")
        
        # Test with a made-up user ID that likely has no documents
        test_user_id = "test_user_12345"
        test_query = "What is the capital of France?"
        
        print(f"Testing query: '{test_query}'")
        print(f"Test user ID: {test_user_id}")
        print(f"Expected: Should fallback to general knowledge since no documents exist")
        print("-" * 60)
        
        # This should trigger the fallback since the test user has no documents
        result = query_rag(test_user_id, test_query, top_k=3)
        
        print("Result:")
        print(result)
        print("-" * 60)
        
        # Check if result contains expected fallback indicators
        if "General Knowledge" in result or "not from your documents" in result:
            print("✅ SUCCESS: Fallback functionality is working!")
            return True
        elif "Error:" in result:
            print("⚠️  WARNING: Got an error - this might be expected if services are not running")
            print("   Error:", result)
            return False
        else:
            print("❓ UNCLEAR: Got a response but not sure if it's fallback or regular RAG")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_rag_fallback()