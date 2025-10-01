from django.conf import settings
import logging
import requests
import json
import time
import random

logger = logging.getLogger(__name__)

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