from django.conf import settings
import logging
import requests
import json
import time
import random
import concurrent.futures
import threading

logger = logging.getLogger(__name__)

# Try to import tiktoken for fallback tokenization
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    logger.warning("tiktoken not available - install with: pip install tiktoken")

class GeminiLLMClient:
    """
    Client for Google's Gemini API using direct HTTP requests
    """
    
    def __init__(self):
        self.api_key = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client with API key from settings"""
        try:
            if not settings.LLM_API_KEY:
                logger.error("LLM_API_KEY not found in settings")
                return
                
            self.api_key = settings.LLM_API_KEY
            logger.info("Successfully initialized Gemini client with gemini-2.0-flash-exp")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.api_key = None
    
    def generate_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate response using Gemini 2.0 Flash model via direct HTTP API
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text or error message
        """
        if not self.api_key:
            return "Error: Gemini client not initialized. Please check your LLM_API_KEY."
        
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7,
                    "topP": 0.8,
                    "topK": 40
                }
            }
            
            params = {
                'key': self.api_key
            }
            
            # Make the request with retry logic
            for attempt in range(3):
                try:
                    response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # Extract text from response
                    text = self._extract_text_from_response(result)
                    if text:
                        return text.strip()
                    
                    # Log the raw response for debugging
                    logger.error(f"Gemini response could not be parsed into text. Raw response: {json.dumps(result, indent=2)}")
                    return "Error: Received empty or filtered response from the AI model."
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 503 and attempt < 2:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Gemini API 503 error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/3)")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"HTTP error calling Gemini API: {e.response.status_code} - {e.response.text}")
                        return f"Error: API request failed with status {e.response.status_code}"
                except requests.exceptions.RequestException as e:
                    if attempt < 2:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Request error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/3): {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Request error calling Gemini API: {e}")
                        return f"Error: Request failed - {str(e)}"
            
            return "Error: Failed to get response after 3 retries"
                
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            return f"Error: Failed to generate response - {str(e)}"

    def _extract_text_from_response(self, response_json) -> str | None:
        """Extract text from Gemini API JSON response.
        
        Args:
            response_json: Parsed JSON response from Gemini API
            
        Returns:
            Extracted text or None if not found
        """
        try:
            # Standard Gemini API response structure
            if 'candidates' in response_json:
                for candidate in response_json['candidates']:
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'text' in part and part['text']:
                                return part['text']
            
            # Alternative response structures
            if 'output' in response_json and isinstance(response_json['output'], str):
                return response_json['output']
                
            if 'text' in response_json and response_json['text']:
                return response_json['text']
                
        except Exception as e:
            logger.error(f"Error extracting text from response: {e}")
            
        return None
    
    def is_available(self) -> bool:
        """Check if the client is properly initialized"""
        return self.api_key is not None
    
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using Gemini Embedding API
        Note: This method is kept for compatibility but uses the EMBEDDING_API_KEY
        """
        if not settings.EMBEDDING_API_KEY:
            logger.error("EMBEDDING_API_KEY not found in settings")
            raise ValueError("EMBEDDING_API_KEY not configured")
        
        logger.info(f"Generating embeddings for {len(texts)} text chunks...")
        
        # Use direct HTTP requests for embeddings
        embeddings = self._get_embeddings_with_requests(texts)
        logger.info(f"✅ Embeddings generated using HTTP requests")
        
        # Validate embedding dimensions
        if embeddings and len(embeddings) > 0:
            actual_dim = len(embeddings[0])
            logger.info(f"✅ Embedding validation: {len(embeddings)} vectors of dimension {actual_dim}")
        
        return embeddings
    
    def _get_embeddings_with_requests(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using parallel HTTP requests with retry logic.
        Maintains order and handles failures gracefully.
        """
        if not texts:
            return []
        
        # Get concurrency settings
        max_workers = getattr(settings, 'EMBEDDING_CONCURRENCY', 5)
        max_retries = getattr(settings, 'EMBEDDING_MAX_RETRIES', 3)
        backoff_base = getattr(settings, 'EMBEDDING_RETRY_BACKOFF_BASE', 1.0)
        backoff_max = getattr(settings, 'EMBEDDING_RETRY_BACKOFF_MAX', 10.0)
        
        logger.info(f"Starting parallel embedding for {len(texts)} texts with {max_workers} workers")
        start_time = time.time()
        
        def embed_single_text(idx_text_pair):
            """Worker function to embed a single text with retry logic"""
            idx, text = idx_text_pair
            session = requests.Session()
            
            try:
                for attempt in range(1, max_retries + 1):
                    try:
                        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
                        headers = {'Content-Type': 'application/json'}
                        data = {
                            "model": "models/gemini-embedding-001",
                            "content": {
                                "parts": [{"text": text}]
                            }
                        }
                        params = {'key': settings.EMBEDDING_API_KEY}
                        
                        response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                        response.raise_for_status()
                        
                        result = response.json()
                        embedding = result['embedding']['values']
                        
                        logger.debug(f"Embedding {idx}: success on attempt {attempt}")
                        return (idx, embedding, attempt)
                        
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code in [429, 503, 502] and attempt < max_retries:
                            # Calculate backoff with jitter
                            backoff = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                            jitter = random.uniform(0, 0.1 * backoff)
                            sleep_time = backoff + jitter
                            
                            logger.warning(f"Embedding {idx}: HTTP {e.response.status_code} on attempt {attempt}, retrying in {sleep_time:.2f}s")
                            time.sleep(sleep_time)
                            continue
                        else:
                            logger.error(f"Embedding {idx}: HTTP error {e.response.status_code} on attempt {attempt}")
                            raise
                    
                    except requests.exceptions.RequestException as e:
                        if attempt < max_retries:
                            backoff = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
                            jitter = random.uniform(0, 0.1 * backoff)
                            sleep_time = backoff + jitter
                            
                            logger.warning(f"Embedding {idx}: Request error on attempt {attempt}, retrying in {sleep_time:.2f}s: {e}")
                            time.sleep(sleep_time)
                            continue
                        else:
                            logger.error(f"Embedding {idx}: Request failed after {attempt} attempts: {e}")
                            raise
                
                # If we get here, all retries failed
                raise ValueError(f"Failed to get embedding for text {idx} after {max_retries} attempts")
                
            finally:
                session.close()
        
        # Execute embeddings in parallel
        embeddings = [None] * len(texts)
        failed_indices = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_idx = {
                executor.submit(embed_single_text, (idx, text)): idx 
                for idx, text in enumerate(texts)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_idx):
                try:
                    idx, embedding, attempts = future.result()
                    embeddings[idx] = embedding
                    logger.debug(f"Collected embedding {idx} (took {attempts} attempts)")
                    
                except Exception as e:
                    idx = future_to_idx[future]
                    failed_indices.append(idx)
                    logger.error(f"Failed to get embedding for text {idx}: {e}")
        
        # Check for failures
        if failed_indices:
            raise ValueError(f"Failed to get embeddings for {len(failed_indices)} texts at indices: {failed_indices}")
        
        # Validate all embeddings were collected
        if None in embeddings:
            missing_indices = [i for i, emb in enumerate(embeddings) if emb is None]
            raise ValueError(f"Missing embeddings at indices: {missing_indices}")
        
        total_time = time.time() - start_time
        avg_time_per_text = total_time / len(texts) if texts else 0
        logger.info(f"✅ Parallel embedding complete: {len(texts)} texts in {total_time:.2f}s (avg {avg_time_per_text:.3f}s per text)")
        
        return embeddings

    def tokenize_texts(self, texts: list[str]) -> list[list[int]]:
        """
        Tokenize texts using Gemini tokenizer with tiktoken fallback.
        
        Args:
            texts: List of text strings to tokenize
            
        Returns:
            List of token ID lists for each text
        """
        use_gemini = getattr(settings, 'RAG_USE_GEMINI_TOKENIZER', True)
        
        if use_gemini and self.api_key:
            try:
                return self._tokenize_with_gemini(texts)
            except Exception as e:
                logger.warning(f"Gemini tokenization failed, falling back to tiktoken: {e}")
        
        # Fallback to tiktoken
        return self._tokenize_with_tiktoken(texts)
    
    def _tokenize_with_gemini(self, texts: list[str]) -> list[list[int]]:
        """
        Attempt to tokenize using Gemini API.
        Note: This is a placeholder implementation as Gemini may not expose 
        a direct tokenization endpoint. We'll use a count-tokens approach.
        """
        token_lists = []
        
        for text in texts:
            try:
                # Use the countTokens endpoint if available
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:countTokens"
                headers = {'Content-Type': 'application/json'}
                data = {
                    "contents": [{
                        "parts": [{"text": text}]
                    }]
                }
                params = {'key': self.api_key}
                
                response = requests.post(url, headers=headers, json=data, params=params, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                # Extract token count and create a dummy token list
                token_count = result.get('totalTokens', 0)
                
                # Since we don't get actual token IDs, create a dummy list
                # This is sufficient for chunking which only needs token counts
                token_lists.append(list(range(token_count)))
                
            except Exception as e:
                logger.error(f"Gemini tokenization failed for text: {e}")
                # Fall back to tiktoken for this specific text
                if HAS_TIKTOKEN:
                    enc = tiktoken.get_encoding("cl100k_base")
                    token_lists.append(enc.encode(text))
                else:
                    # Last resort: approximate with whitespace
                    token_lists.append(text.split())
        
        logger.info(f"✅ Gemini tokenization successful for {len(texts)} texts")
        return token_lists
    
    def _tokenize_with_tiktoken(self, texts: list[str]) -> list[list[int]]:
        """
        Tokenize using tiktoken as fallback.
        """
        if not HAS_TIKTOKEN:
            logger.warning("tiktoken not available, using whitespace approximation")
            return [text.split() for text in texts]
        
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            token_lists = [enc.encode(text) for text in texts]
            logger.info(f"✅ tiktoken tokenization successful for {len(texts)} texts")
            return token_lists
        except Exception as e:
            logger.error(f"tiktoken tokenization failed: {e}")
            # Final fallback: whitespace split
            return [text.split() for text in texts]

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a single text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        token_list = self.tokenize_texts([text])[0]
        return len(token_list)

# Module-level instance
gemini_client = GeminiLLMClient()