#!/usr/bin/env python3
"""
Comprehensive RAG Flow Test Script
Tests the complete pipeline from document ingestion to query response
"""

import os
import sys
import django
import tempfile
import uuid
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.rag_ingestion import ingest_document, initialize_pinecone
from api.rag_query import query_rag
from api.auth import get_tenant_tag
from api.gemini_client import gemini_client

def create_test_document():
    """Create a test document with sample content"""
    test_content = """
    Machine Learning and Artificial Intelligence
    
    Machine learning is a subset of artificial intelligence that focuses on the development of algorithms 
    that can learn and make decisions from data. It has revolutionized many industries including healthcare, 
    finance, and technology.
    
    Key Concepts in Machine Learning:
    
    1. Supervised Learning: Uses labeled data to train models
    2. Unsupervised Learning: Finds patterns in unlabeled data
    3. Reinforcement Learning: Learns through interaction with environment
    
    Deep Learning is a specialized form of machine learning that uses neural networks with multiple layers.
    It has been particularly successful in image recognition, natural language processing, and speech recognition.
    
    Applications of AI:
    - Healthcare: Medical diagnosis, drug discovery
    - Finance: Fraud detection, algorithmic trading
    - Transportation: Autonomous vehicles, route optimization
    - Technology: Recommendation systems, virtual assistants
    
    The future of AI holds great promise for solving complex problems and improving human life.
    """
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        return f.name

def test_embedding_api():
    """Test if embedding API is working"""
    print("🧪 Testing Embedding API...")
    try:
        test_texts = ["Hello world", "Machine learning is fascinating"]
        embeddings = gemini_client.get_embeddings(test_texts)
        print(f"✅ Embedding API works! Got {len(embeddings)} embeddings of dimension {len(embeddings[0])}")
        return True
    except Exception as e:
        print(f"❌ Embedding API failed: {e}")
        return False

def test_pinecone_connection():
    """Test Pinecone connection and index creation"""
    print("🧪 Testing Pinecone Connection...")
    try:
        index = initialize_pinecone()
        print(f"✅ Pinecone connected! Index: {index}")
        return True
    except Exception as e:
        print(f"❌ Pinecone connection failed: {e}")
        return False

def test_tenant_isolation():
    """Test tenant tag generation"""
    print("🧪 Testing Tenant Isolation...")
    try:
        user1_id = "user123"
        user2_id = "user456"
        
        tag1 = get_tenant_tag(user1_id)
        tag2 = get_tenant_tag(user2_id)
        
        # Same user should get same tag
        tag1_again = get_tenant_tag(user1_id)
        
        print(f"User1 tag: {tag1[:16]}...")
        print(f"User2 tag: {tag2[:16]}...")
        
        assert tag1 == tag1_again, "Same user should get same tag"
        assert tag1 != tag2, "Different users should get different tags"
        
        print("✅ Tenant isolation working correctly!")
        return True
    except Exception as e:
        print(f"❌ Tenant isolation failed: {e}")
        return False

def test_document_ingestion():
    """Test document ingestion pipeline"""
    print("🧪 Testing Document Ingestion...")
    try:
        # Create test document
        test_file = create_test_document()
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        print(f"Created test document: {test_file}")
        print(f"Test user ID: {test_user_id}")
        
        # Ingest document
        ingest_document(test_file, test_user_id)
        
        # Cleanup
        os.unlink(test_file)
        
        print("✅ Document ingestion completed!")
        return test_user_id
    except Exception as e:
        print(f"❌ Document ingestion failed: {e}")
        if 'test_file' in locals() and os.path.exists(test_file):
            os.unlink(test_file)
        return None

def test_query_pipeline(user_id):
    """Test query pipeline"""
    print("🧪 Testing Query Pipeline...")
    try:
        test_queries = [
            "What is machine learning?",
            "Tell me about deep learning",
            "What are the applications of AI in healthcare?",
            "How does supervised learning work?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Query {i}: {query} ---")
            response = query_rag(user_id, query)
            print(f"Response: {response[:200]}...")
            
            if "Error:" in response:
                print(f"⚠️  Query {i} returned an error")
            else:
                print(f"✅ Query {i} successful")
        
        print("\n✅ Query pipeline testing completed!")
        return True
    except Exception as e:
        print(f"❌ Query pipeline failed: {e}")
        return False

def test_cross_tenant_isolation():
    """Test that users can't access each other's documents"""
    print("🧪 Testing Cross-Tenant Isolation...")
    try:
        # Create two users and documents
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}" 
        
        # Create user1's document
        user1_content = "User 1's secret information about quantum computing and advanced algorithms."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(user1_content)
            user1_file = f.name
        
        # Create user2's document  
        user2_content = "User 2's confidential data about blockchain technology and cryptocurrency."
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(user2_content)
            user2_file = f.name
        
        # Ingest both documents
        print(f"Ingesting document for user1: {user1_id}")
        ingest_document(user1_file, user1_id)
        
        print(f"Ingesting document for user2: {user2_id}")
        ingest_document(user2_file, user2_id)
        
        # Test queries
        query = "Tell me about quantum computing"
        
        print(f"\nUser1 querying about quantum computing...")
        user1_response = query_rag(user1_id, query)
        
        print(f"User2 querying about quantum computing...")
        user2_response = query_rag(user2_id, query)
        
        # User1 should get relevant results, User2 should not
        user1_has_quantum = "quantum" in user1_response.lower()
        user2_has_quantum = "quantum" in user2_response.lower()
        
        print(f"User1 response contains 'quantum': {user1_has_quantum}")
        print(f"User2 response contains 'quantum': {user2_has_quantum}")
        
        # Cleanup
        os.unlink(user1_file)
        os.unlink(user2_file)
        
        if user1_has_quantum and not user2_has_quantum:
            print("✅ Cross-tenant isolation working correctly!")
            return True
        else:
            print("⚠️  Cross-tenant isolation needs investigation")
            return False
            
    except Exception as e:
        print(f"❌ Cross-tenant isolation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting RAG Flow Comprehensive Test\n")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Embedding API
    test_results['embedding'] = test_embedding_api()
    print()
    
    # Test 2: Pinecone Connection
    test_results['pinecone'] = test_pinecone_connection()
    print()
    
    # Test 3: Tenant Isolation
    test_results['tenant'] = test_tenant_isolation()
    print()
    
    # Test 4: Document Ingestion
    test_user_id = test_document_ingestion()
    test_results['ingestion'] = test_user_id is not None
    print()
    
    # Test 5: Query Pipeline (only if ingestion worked)
    if test_user_id:
        test_results['query'] = test_query_pipeline(test_user_id)
    else:
        test_results['query'] = False
        print("❌ Skipping query test due to ingestion failure")
    print()
    
    # Test 6: Cross-tenant isolation
    test_results['isolation'] = test_cross_tenant_isolation()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper():.<20} {status}")
    
    print("-" * 60)
    print(f"TOTAL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! RAG system is working correctly!")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)