"""
Real-world test for RAG fallback to general knowledge LLM.
Run this after starting the Django server to test actual behavior.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.rag_query import query_rag
from api.gemini_client import gemini_client

def test_rag_fallback_real():
    """Test RAG with real queries to verify fallback works"""
    
    # Use a real user ID from your logs
    test_user_id = "b8593008-bb48-4c31-b62a-0331fbbbd50c"
    
    print("="*80)
    print("REAL-WORLD RAG FALLBACK TEST")
    print("="*80)
    
    test_cases = [
        {
            "name": "Embedding chunks (technical, likely not in docs)",
            "query": "what is embedding chunks how it will work?",
            "expect_fallback": True
        },
        {
            "name": "Quantum computing (completely unrelated)",
            "query": "explain quantum computing",
            "expect_fallback": True
        },
        {
            "name": "General ML question",
            "query": "what is machine learning?",
            "expect_fallback": True  # Unless user has ML docs
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {'Fallback to general LLM' if test['expect_fallback'] else 'Use RAG context'}")
        print(f"{'='*80}")
        
        try:
            response = query_rag(test_user_id, test['query'])
            
            print(f"\nResponse length: {len(response)} chars")
            print(f"\nResponse:\n{response}\n")
            
            # Check if fallback was used
            is_fallback = "(Note: This answer is based on general knowledge" in response
            is_error = "Error:" in response or "I could not find" in response
            
            if is_fallback:
                print("✅ Result: General knowledge fallback was used")
                if test['expect_fallback']:
                    print("✅ PASS: Behavior matches expectation")
                else:
                    print("⚠️  WARNING: Expected RAG context, but got fallback")
            elif is_error:
                print("❌ Result: Error occurred")
                print("⚠️  Check your API keys and configuration")
            else:
                print("✅ Result: Used RAG context from documents")
                if not test['expect_fallback']:
                    print("✅ PASS: Behavior matches expectation")
                else:
                    print("⚠️  WARNING: Expected fallback, but used RAG context")
                    print("   (User might have relevant content in their documents)")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print("The RAG system should:")
    print("1. ✅ Retrieve chunks from Pinecone for user's query")
    print("2. ✅ Check if LLM can answer from those chunks")
    print("3. ✅ If LLM says NO_ANSWER_IN_CONTEXT, fallback to general knowledge")
    print("4. ✅ Add '(Note: This answer is based on general knowledge...)' to fallback responses")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Check if LLM client is available
    if not gemini_client.is_available():
        print("❌ ERROR: Gemini client not available.")
        print("Check your LLM_API_KEY in .env file")
        sys.exit(1)
    
    print("✅ Gemini client is available")
    print("Starting real-world RAG fallback test...\n")
    
    test_rag_fallback_real()
