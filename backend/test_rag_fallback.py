#!/usr/bin/env python3
"""
Test script for RAG fallback functionality.
Tests that query_rag falls back to LLM general knowledge when no context is found.
"""
import os
import sys
import django
from unittest.mock import Mock, patch

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

def test_rag_with_context():
    """Test normal RAG operation with context found"""
    print("=== Test 1: RAG with context found ===")
    
    # Mock successful Pinecone retrieval
    mock_matches = [
        {
            'metadata': {
                'tenant_tag': 'test_tenant',
                'text': 'Python is a programming language.',
                'chunk_index': 1,
                'source_doc_id': 'test_doc'
            },
            'id': 'test_id_1'
        }
    ]
    
    with patch('api.rag_query.get_tenant_tag', return_value='test_tenant'), \
         patch('api.rag_query.get_embedding_client') as mock_embed, \
         patch('api.rag_query.initialize_pinecone') as mock_pinecone, \
         patch('api.rag_query.gemini_client') as mock_gemini:
        
        # Setup mocks
        mock_embed.return_value.get_embeddings.return_value = [[0.1, 0.2, 0.3]]
        mock_pinecone.return_value.query.return_value = {'matches': mock_matches}
        mock_gemini.is_available.return_value = True
        mock_gemini.generate_response.return_value = "Python is a high-level programming language. [test_doc:1]"
        
        from api.rag_query import query_rag
        result = query_rag("test_user", "What is Python?")
        
        print(f"Result: {result}")
        assert "Python is a high-level programming language" in result
        assert "[test_doc:1]" in result
        print("✅ Normal RAG operation works correctly")

def test_rag_fallback_to_llm():
    """Test RAG fallback to LLM when no context found"""
    print("\n=== Test 2: RAG fallback to LLM ===")
    
    with patch('api.rag_query.get_tenant_tag', return_value='test_tenant'), \
         patch('api.rag_query.get_embedding_client') as mock_embed, \
         patch('api.rag_query.initialize_pinecone') as mock_pinecone, \
         patch('api.rag_query.gemini_client') as mock_gemini:
        
        # Setup mocks - no matches found
        mock_embed.return_value.get_embeddings.return_value = [[0.1, 0.2, 0.3]]
        mock_pinecone.return_value.query.return_value = {'matches': []}  # No matches
        mock_gemini.is_available.return_value = True
        mock_gemini.generate_response.return_value = "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience."
        
        from api.rag_query import query_rag
        result = query_rag("test_user", "What is machine learning?")
        
        print(f"Result: {result}")
        assert "Machine learning is a subset of artificial intelligence" in result
        assert "Note: This answer is based on general knowledge" in result
        print("✅ LLM fallback works correctly")

def test_rag_fallback_llm_error():
    """Test RAG fallback when LLM also fails"""
    print("\n=== Test 3: RAG fallback with LLM error ===")
    
    with patch('api.rag_query.get_tenant_tag', return_value='test_tenant'), \
         patch('api.rag_query.get_embedding_client') as mock_embed, \
         patch('api.rag_query.initialize_pinecone') as mock_pinecone, \
         patch('api.rag_query.gemini_client') as mock_gemini:
        
        # Setup mocks - no matches and LLM error
        mock_embed.return_value.get_embeddings.return_value = [[0.1, 0.2, 0.3]]
        mock_pinecone.return_value.query.return_value = {'matches': []}
        mock_gemini.is_available.return_value = True
        mock_gemini.generate_response.return_value = "Error: API failed"
        
        from api.rag_query import query_rag
        result = query_rag("test_user", "What is quantum physics?")
        
        print(f"Result: {result}")
        assert "I could not find any relevant information in your documents" in result
        assert "having trouble accessing general knowledge" in result
        print("✅ LLM error fallback works correctly")

if __name__ == "__main__":
    try:
        test_rag_with_context()
        test_rag_fallback_to_llm()
        test_rag_fallback_llm_error()
        print("\n🎉 All tests passed! RAG fallback functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()