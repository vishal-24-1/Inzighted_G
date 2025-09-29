# Prefer the new official Google GenAI client when available (package: google-genai)
# Keep legacy google.generativeai support for LLM generation as a fallback.
from django.conf import settings
import logging
import requests
import json
import time
import random

logger = logging.getLogger(__name__)

# Try to import the new google-genai client (provides `from google import genai`)
try:
    from google import genai as genai_client
except Exception:
    genai_client = None

# Try to import the legacy google.generativeai (some code paths still use it)
try:
    import google.generativeai as genai
except Exception:
    genai = None

class GeminiLLMClient:
    """
    Client for Google's Gemini/Generative AI API
    """
    
    def __init__(self):
        self.model = None
        self.embed_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini client with API key from settings"""
        try:
            if not settings.LLM_API_KEY:
                logger.error("LLM_API_KEY not found in settings")
                return
                
            # Configure the API key for legacy client
            genai.configure(api_key=settings.LLM_API_KEY)
            
            # Initialize the model with Gemini 2.5 Flash
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Initialize the new genai client for embeddings
            if settings.EMBEDDING_API_KEY:
                self.embed_client = genai_client.Client(api_key=settings.EMBEDDING_API_KEY)
                logger.info("Successfully initialized Gemini client with gemini-2.5-flash and embedding client")
            else:
                logger.warning("EMBEDDING_API_KEY not found, falling back to requests-based embedding")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.model = None
            self.embed_client = None
    
    def generate_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate response using Gemini model
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text or error message
        """
        if not self.model:
            return "Error: Gemini client not initialized. Please check your LLM_API_KEY."
        
        try:
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract text from response
            if response.text:
                return response.text.strip()
            else:
                logger.error("Empty response from Gemini")
                return "Error: Received empty response from the AI model."
                
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            return f"Error: Failed to generate response - {str(e)}"
    
    def is_available(self) -> bool:
        """Check if the client is properly initialized"""
        return self.model is not None
    
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using Gemini Embedding API
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not settings.EMBEDDING_API_KEY:
            logger.error("EMBEDDING_API_KEY not found in settings")
            raise ValueError("EMBEDDING_API_KEY not configured")
        
        print(f"Generating embeddings for {len(texts)} text chunks...")
        
        # Use the new genai.Client() if available, fallback to requests
        if self.embed_client:
            try:
                embeddings = self._get_embeddings_with_client(texts)
                print("✅ Embeddings generated using genai.Client")
            except Exception as e:
                print(f"⚠️ genai.Client failed, falling back to HTTP requests: {e}")
                embeddings = self._get_embeddings_with_requests(texts)
                print("✅ Embeddings generated using HTTP fallback")
        else:
            embeddings = self._get_embeddings_with_requests(texts)
            print("✅ Embeddings generated using HTTP requests (no client available)")
        
        # Validate embedding dimensions
        if embeddings and len(embeddings) > 0:
                actual_dim = len(embeddings[0])
                # Allow optional configuration via settings.EMBEDDING_DIM
                configured = getattr(settings, 'EMBEDDING_DIM', None)
                if configured:
                    try:
                        expected_dim = int(configured)
                    except Exception:
                        expected_dim = None
                    if expected_dim and actual_dim != expected_dim:
                        # Don't hard-fail by default; log a warning and proceed with actual_dim
                        logger.warning(
                            "Embedding dimension mismatch vs configured EMBEDDING_DIM: expected %s, got %s. Proceeding with actual dimension.",
                            expected_dim,
                            actual_dim,
                        )
                    else:
                        logger.info("Embedding validation passed: %s vectors of dimension %s", len(embeddings), actual_dim)
                else:
                    # No configured expectation: accept detected dimension and log it
                    logger.info("Embedding dimension detected: %s (no EMBEDDING_DIM configured)", actual_dim)
                print(f"✅ Embedding validation: {len(embeddings)} vectors of dimension {actual_dim}")
        
        return embeddings
    
    def _get_embeddings_with_client(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings using the official genai.Client()"""
        embeddings = []
        
        for text in texts:
            success = False
            for attempt in range(3):  # 3 retries
                try:
                    result = self.embed_client.models.embed_content(
                        model="gemini-embedding-001",
                        contents=text
                    )
                    
                    # Extract embedding values from the result
                    if hasattr(result, 'embeddings') and len(result.embeddings) > 0:
                        embedding = result.embeddings[0].values
                        embeddings.append(embedding)
                        success = True
                        break
                    else:
                        raise ValueError("Empty embedding response")
                        
                except Exception as e:
                    if "503" in str(e) and attempt < 2:  # Retry on 503-like errors
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Gemini embedding error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/3): {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Error calling Gemini embedding with client: {e}")
                        # Fallback to requests method
                        return self._get_embeddings_with_requests(texts)
            
            if not success:
                logger.warning("Failed with client method, falling back to requests")
                return self._get_embeddings_with_requests(texts)
        
        return embeddings
    
    def _get_embeddings_with_requests(self, texts: list[str]) -> list[list[float]]:
        """Fallback method using direct HTTP requests"""
        embeddings = []
        
        for text in texts:
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
                headers = {
                    'Content-Type': 'application/json',
                }
                
                data = {
                    "model": "models/gemini-embedding-001",
                    "content": {
                        "parts": [{"text": text}]
                    }
                }
                
                params = {
                    'key': settings.EMBEDDING_API_KEY
                }
                
                # Retry logic with exponential backoff
                success = False
                for attempt in range(3):  # 3 retries
                    try:
                        response = requests.post(url, headers=headers, json=data, params=params)
                        response.raise_for_status()
                        
                        result = response.json()
                        embedding = result['embedding']['values']
                        embeddings.append(embedding)
                        success = True
                        break
                        
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 503 and attempt < 2:  # Retry on 503
                            wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff with jitter
                            logger.warning(f"Gemini API 503 error, retrying in {wait_time:.1f}s (attempt {attempt + 1}/3)")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise  # Re-raise if not 503 or final attempt
                
                if not success:
                    raise ValueError("Failed to get embedding after 3 retries")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP error calling Gemini Embedding API: {e}")
                raise ValueError(f"Failed to get embeddings: {e}")
            except KeyError as e:
                logger.error(f"Unexpected response format from Gemini Embedding API: {e}")
                raise ValueError(f"Invalid API response format: {e}")
            except Exception as e:
                logger.error(f"Error calling Gemini Embedding API: {e}")
                raise ValueError(f"Embedding API error: {e}")
        
        return embeddings

# Module-level instance
gemini_client = GeminiLLMClient()