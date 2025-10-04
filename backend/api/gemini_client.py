from django.conf import settings
import logging
import requests
import json
import time
import random
import concurrent.futures
import threading
from .llm_key_manager import LLMKeyManager
import sentry_sdk

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
        # Key manager supports multiple comma-separated keys in settings.LLM_API_KEY
        self.key_manager = LLMKeyManager(settings.LLM_API_KEY if getattr(settings, 'LLM_API_KEY', None) else None)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client with API key from settings"""
        try:
            if not self.key_manager or self.key_manager.total_keys() == 0:
                logger.error("LLM_API_KEY not found in settings or no keys configured")
                sentry_sdk.capture_message(
                    "LLM_API_KEY not configured",
                    level="error",
                    extras={"component": "gemini_client"}
                )
                return

            # Set initial api_key
            self.api_key = self.key_manager.get_key()
            logger.info("Successfully initialized Gemini client with gemini-2.0-flash-exp (key rotation enabled)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            sentry_sdk.capture_exception(e)
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
        if not self.key_manager or self.key_manager.total_keys() == 0:
            return "Error: Gemini client not initialized. Please check your LLM_API_KEY."
        
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
            headers = {'Content-Type': 'application/json'}

            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.7,
                    "topP": 0.8,
                    "topK": 40,
                },
            }

            # We'll attempt across available keys until one succeeds or all fail
            tried_keys = []
            total_available = self.key_manager.total_keys()

            for key_attempt in range(total_available):
                current_key = self.key_manager.get_key()
                if not current_key:
                    break

                tried_keys.append(current_key)
                params = {'key': current_key}

                # Try a small retry loop per key for transient errors
                for attempt in range(2):
                    try:
                        response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                        response.raise_for_status()

                        result = response.json()
                        text = self._extract_text_from_response(result)
                        if text:
                            # success
                            return text.strip()

                        logger.error(f"Gemini response could not be parsed into text. Raw response: {json.dumps(result, indent=2)}")
                        return "Error: Received empty or filtered response from the AI model."

                    except requests.exceptions.HTTPError as e:
                        status = getattr(e.response, 'status_code', None)
                        body = getattr(e.response, 'text', '')

                        # Capture HTTP errors in Sentry with context
                        sentry_sdk.capture_exception(e, extras={
                            "component": "gemini_client",
                            "method": "generate_response",
                            "status_code": status,
                            "response_body": body[:500],  # First 500 chars
                            "key_attempt": key_attempt,
                            "attempt": attempt
                        })

                        # If key is invalid or quota, blacklist this key and try next
                        if status in (401, 403, 429):
                            logger.warning(f"Key error (status {status}) for key {current_key[:8]}..., marking failed. Response: {body}")
                            # blacklist the key for some time
                            self.key_manager.mark_key_failed(current_key, cooldown_seconds=60)
                            break  # break out of retry loop for this key and try next key

                        # transient server errors - maybe retry
                        if status in (502, 503) and attempt == 0:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"Gemini API {status} error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/2)")
                            time.sleep(wait_time)
                            continue

                        logger.error(f"HTTP error calling Gemini API: {status} - {body}")
                        return f"Error: API request failed with status {status}"

                    except requests.exceptions.RequestException as e:
                        # Capture request exceptions
                        sentry_sdk.capture_exception(e, extras={
                            "component": "gemini_client",
                            "method": "generate_response",
                            "key_attempt": key_attempt,
                            "attempt": attempt
                        })
                        
                        if attempt == 0:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            logger.warning(f"Request error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/2): {e}")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Request error calling Gemini API: {e}")
                            # mark key as possibly bad and try next
                            self.key_manager.mark_key_failed(current_key, cooldown_seconds=30)
                            break

            # If we get here, all keys failed
            logger.error(f"All LLM API keys failed or exhausted. Tried keys: {[k[:8] + '...' for k in tried_keys]}")
            sentry_sdk.capture_message(
                "All LLM API keys failed or exhausted",
                level="error",
                extras={
                    "component": "gemini_client",
                    "method": "generate_response",
                    "tried_keys_count": len(tried_keys)
                }
            )
            return "Error: All configured LLM API keys failed or are exhausted."
                
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "generate_response"
            })
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
        try:
            if not settings.EMBEDDING_API_KEY:
                logger.error("EMBEDDING_API_KEY not found in settings")
                sentry_sdk.capture_message(
                    "EMBEDDING_API_KEY not configured",
                    level="error",
                    extras={"component": "gemini_client", "method": "get_embeddings"}
                )
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
        except Exception as e:
            logger.error(f"Error in get_embeddings: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "get_embeddings",
                "text_count": len(texts) if texts else 0
            })
            raise
    
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
            error_msg = f"Failed to get embeddings for {len(failed_indices)} texts at indices: {failed_indices}"
            logger.error(error_msg)
            sentry_sdk.capture_message(
                error_msg,
                level="error",
                extras={
                    "component": "gemini_client",
                    "method": "_get_embeddings_with_requests",
                    "failed_count": len(failed_indices),
                    "total_count": len(texts)
                }
            )
            raise ValueError(error_msg)
        
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
                # Try across available keys
                params_key = None
                for _ in range(self.key_manager.total_keys()):
                    candidate_key = self.key_manager.get_key()
                    if not candidate_key:
                        break
                    params = {'key': candidate_key}
                    try:
                        response = requests.post(url, headers=headers, json=data, params=params, timeout=10)
                        response.raise_for_status()

                        result = response.json()
                        token_count = result.get('totalTokens', 0)
                        token_lists.append(list(range(token_count)))
                        break

                    except requests.exceptions.HTTPError as e:
                        status = getattr(e.response, 'status_code', None)
                        if status in (401, 403, 429):
                            # mark key failed and try next
                            self.key_manager.mark_key_failed(candidate_key, cooldown_seconds=30)
                            continue
                        else:
                            raise
                    except requests.exceptions.RequestException:
                        # try next key
                        self.key_manager.mark_key_failed(candidate_key, cooldown_seconds=10)
                        continue

                else:
                    # No key succeeded for this text - fall back to tiktoken or whitespace
                    logger.error("Gemini tokenization: no LLM keys succeeded for tokenization request, falling back")
                    if HAS_TIKTOKEN:
                        enc = tiktoken.get_encoding("cl100k_base")
                        token_lists.append(enc.encode(text))
                    else:
                        token_lists.append(text.split())
                
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