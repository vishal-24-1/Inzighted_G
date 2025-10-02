import unittest
from unittest.mock import patch, MagicMock
import time
import requests
from api.gemini_client import GeminiLLMClient


class TestParallelEmbedding(unittest.TestCase):
    
    def setUp(self):
        self.client = GeminiLLMClient()
        self.client.api_key = "test_key"  # Mock API key
    
    @patch('api.gemini_client.settings')
    @patch('requests.Session')
    def test_parallel_embedding_success(self, mock_session_class, mock_settings):
        """Test successful parallel embedding with multiple texts"""
        # Mock settings
        mock_settings.EMBEDDING_API_KEY = "test_key"
        mock_settings.EMBEDDING_CONCURRENCY = 3
        mock_settings.EMBEDDING_MAX_RETRIES = 2
        mock_settings.EMBEDDING_RETRY_BACKOFF_BASE = 0.1
        mock_settings.EMBEDDING_RETRY_BACKOFF_MAX = 1.0
        
        # Mock successful response
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'embedding': {'values': [0.1, 0.2, 0.3]}
        }
        mock_session.post = MagicMock(return_value=mock_response)
        
        # Test with multiple texts
        texts = ["text1", "text2", "text3", "text4"]
        
        start_time = time.time()
        embeddings = self.client._get_embeddings_with_requests(texts)
        duration = time.time() - start_time
        
        # Verify results
        self.assertEqual(len(embeddings), 4)
        self.assertEqual(embeddings[0], [0.1, 0.2, 0.3])
        self.assertEqual(embeddings[3], [0.1, 0.2, 0.3])
        
        # Verify all texts were processed
        self.assertEqual(mock_session.post.call_count, 4)
    
    @patch('api.gemini_client.settings')
    @patch('requests.Session')
    def test_parallel_embedding_with_retries(self, mock_session_class, mock_settings):
        """Test parallel embedding with retry logic on transient failures"""
        # Mock settings
        mock_settings.EMBEDDING_API_KEY = "test_key"
        mock_settings.EMBEDDING_CONCURRENCY = 2
        mock_settings.EMBEDDING_MAX_RETRIES = 3
        mock_settings.EMBEDDING_RETRY_BACKOFF_BASE = 0.01  # Fast for testing
        mock_settings.EMBEDDING_RETRY_BACKOFF_MAX = 0.1
        
        # Mock session that fails first, then succeeds
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # First call fails with 503, second succeeds
        error_response = MagicMock()
        error_response.status_code = 503
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_response)
        
        success_response = MagicMock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {
            'embedding': {'values': [0.5, 0.6, 0.7]}
        }
        
        # Configure mock to fail once then succeed
        mock_session.post.side_effect = [error_response, success_response]
        
        # Test single text with retry
        texts = ["test text"]
        embeddings = self.client._get_embeddings_with_requests(texts)
        
        # Should succeed after retry
        self.assertEqual(len(embeddings), 1)
        self.assertEqual(embeddings[0], [0.5, 0.6, 0.7])
        
        # Should have made 2 calls (1 failed + 1 success)
        self.assertEqual(mock_session.post.call_count, 2)
    
    @patch('api.gemini_client.settings')
    @patch('requests.Session')
    def test_parallel_embedding_order_preservation(self, mock_session_class, mock_settings):
        """Test that embedding order matches input text order"""
        # Mock settings
        mock_settings.EMBEDDING_API_KEY = "test_key"
        mock_settings.EMBEDDING_CONCURRENCY = 3
        mock_settings.EMBEDDING_MAX_RETRIES = 1
        
        # Mock session with different embeddings for each text
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # Create unique responses for each text
        def mock_post(*args, **kwargs):
            # Extract text from request data to determine response
            data = kwargs.get('json', {})
            text = data.get('content', {}).get('parts', [{}])[0].get('text', '')
            
            response = MagicMock()
            response.raise_for_status.return_value = None
            
            # Return unique embedding based on text
            if 'first' in text:
                response.json.return_value = {'embedding': {'values': [1.0, 0.0, 0.0]}}
            elif 'second' in text:
                response.json.return_value = {'embedding': {'values': [0.0, 1.0, 0.0]}}
            elif 'third' in text:
                response.json.return_value = {'embedding': {'values': [0.0, 0.0, 1.0]}}
            else:
                response.json.return_value = {'embedding': {'values': [0.5, 0.5, 0.5]}}
            
            return response
        
        mock_session.post.side_effect = mock_post
        
        # Test with ordered texts
        texts = ["first text", "second text", "third text"]
        embeddings = self.client._get_embeddings_with_requests(texts)
        
        # Verify order is preserved
        self.assertEqual(len(embeddings), 3)
        self.assertEqual(embeddings[0], [1.0, 0.0, 0.0])  # first text
        self.assertEqual(embeddings[1], [0.0, 1.0, 0.0])  # second text  
        self.assertEqual(embeddings[2], [0.0, 0.0, 1.0])  # third text
    
    @patch('api.gemini_client.settings')
    @patch('requests.Session')
    def test_parallel_embedding_failure_handling(self, mock_session_class, mock_settings):
        """Test handling of persistent failures"""
        # Mock settings
        mock_settings.EMBEDDING_API_KEY = "test_key"
        mock_settings.EMBEDDING_CONCURRENCY = 2
        mock_settings.EMBEDDING_MAX_RETRIES = 2
        mock_settings.EMBEDDING_RETRY_BACKOFF_BASE = 0.01
        mock_settings.EMBEDDING_RETRY_BACKOFF_MAX = 0.1
        
        # Mock session that always fails
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=error_response)
        mock_session.post.return_value = error_response
        
        # Test should raise exception for persistent failure
        texts = ["failing text"]
        
        with self.assertRaises(ValueError) as context:
            self.client._get_embeddings_with_requests(texts)
        
        self.assertIn("Failed to get embeddings", str(context.exception))


if __name__ == '__main__':
    unittest.main()