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
    
    # ============================================================
    # NEW METHODS FOR TANGLISH AGENT FLOW
    # ============================================================
    
    def classify_intent(self, user_message: str) -> str:
        """
        Classify user intent using Gemini with exact system prompt from spec.
        Returns one token: DIRECT_ANSWER, MIXED, or RETURN_QUESTION.
        Falls back to deterministic rule on API failure.
        
        Args:
            user_message: The user's message to classify
            
        Returns:
            Intent token string
        """
        from .tanglish_prompts import INTENT_CLASSIFIER_SYSTEM_PROMPT, fallback_intent_classifier
        
        try:
            # Build prompt
            prompt = f"{INTENT_CLASSIFIER_SYSTEM_PROMPT}\n\nUSER_MESSAGE: {user_message}\n\nClassify:"
            
            print(f"[CLASSIFIER] Prompt: {prompt[:200]}...")
            
            # Call Gemini with short response
            response = self.generate_response(prompt, max_tokens=10)
            
            print(f"[CLASSIFIER] Gemini raw response: '{response}'")
            
            if not response or response.startswith("Error:"):
                print(f"[CLASSIFIER] Gemini failed, using fallback")
                return fallback_intent_classifier(user_message)
            
            # Parse first token
            token = response.strip().split()[0].upper()
            
            print(f"[CLASSIFIER] Parsed token: '{token}'")
            
            # Validate token
            valid_tokens = ['DIRECT_ANSWER', 'MIXED', 'RETURN_QUESTION']
            if token in valid_tokens:
                print(f"[CLASSIFIER] ✅ Valid token: {token}")
                return token
            else:
                print(f"[CLASSIFIER] ⚠️ Invalid token '{token}', using fallback")
                return fallback_intent_classifier(user_message)
                
        except Exception as e:
            logger.error(f"Error in classify_intent: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "classify_intent"
            })
            return fallback_intent_classifier(user_message)
    
    def generate_questions_structured(self, context: str, total_questions: int = 10) -> list:
        """
        Generate structured questions using exact system prompt from spec.
        Returns list of question dictionaries with archetype, difficulty, etc.
        
        Args:
            context: Document context to generate questions from
            total_questions: Number of questions to generate
            
        Returns:
            List of question dicts matching spec format
        """
        from .tanglish_prompts import build_question_generation_prompt
        import json
        
        try:
            # Build prompt with context
            prompt = build_question_generation_prompt(context, total_questions)
            
            # Call Gemini
            logger.info(f"Generating {total_questions} structured questions...")
            response = self.generate_response(prompt, max_tokens=3000)
            
            if response.startswith("Error:"):
                raise ValueError(f"LLM error: {response}")
            
            # Parse JSON response
            try:
                # Clean response
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                questions = json.loads(cleaned)
                
                if not isinstance(questions, list):
                    raise ValueError("Response is not a JSON array")
                
                # Validate structure
                required_keys = ['question_id', 'archetype', 'question_text', 'difficulty', 'expected_answer']
                valid_questions = []
                
                for q in questions:
                    if isinstance(q, dict) and all(k in q for k in required_keys):
                        valid_questions.append(q)
                
                if len(valid_questions) < total_questions // 2:
                    raise ValueError(f"Only got {len(valid_questions)} valid questions")
                
                logger.info(f"Successfully generated {len(valid_questions)} structured questions")
                return valid_questions[:total_questions]
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse question JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                
                # Fallback: return minimal structure
                return [{
                    "question_id": f"q_fallback_{i}",
                    "archetype": "Concept Unfold",
                    "question_text": f"Question {i+1} generation failed. Please try again.",
                    "difficulty": "medium",
                    "expected_answer": "N/A"
                } for i in range(min(3, total_questions))]
                
        except Exception as e:
            logger.error(f"Error in generate_questions_structured: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "generate_questions_structured"
            })
            return []
    
    def evaluate_answer(self, context: str, expected_answer: str, student_answer: str) -> dict:
        """
        Evaluate student answer using Gemini Judge with exact system prompt from spec.
        Returns evaluation dict with score, XP, explanation, etc.
        
        Args:
            context: Question context
            expected_answer: Expected answer
            student_answer: Student's answer
            
        Returns:
            Evaluation dict matching spec format
        """
        from .tanglish_prompts import build_evaluation_prompt
        import json
        
        try:
            # Build evaluation prompt
            prompt = build_evaluation_prompt(context, expected_answer, student_answer)
            
            # Call Gemini
            logger.info("Evaluating student answer...")
            response = self.generate_response(prompt, max_tokens=500)
            
            if response.startswith("Error:"):
                raise ValueError(f"LLM error: {response}")
            
            # Parse JSON response
            try:
                # Clean response
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                evaluation = json.loads(cleaned)
                
                # Validate required keys
                required_keys = ['score', 'correct', 'explanation', 'confidence', 'followup_action']
                if not all(k in evaluation for k in required_keys):
                    raise ValueError("Missing required keys in evaluation")
                
                # Ensure XP is present and valid
                if 'XP' not in evaluation or not isinstance(evaluation['XP'], (int, float)):
                    # Calculate XP from score
                    score = float(evaluation['score'])
                    if score >= 0.9:
                        evaluation['XP'] = int(80 + (score - 0.9) * 200)
                    elif score >= 0.75:
                        evaluation['XP'] = int(60 + (score - 0.75) * 133)
                    elif score >= 0.5:
                        evaluation['XP'] = int(40 + (score - 0.5) * 80)
                    elif score >= 0.25:
                        evaluation['XP'] = int(20 + (score - 0.25) * 80)
                    else:
                        evaluation['XP'] = max(1, int(score * 80))
                
                # Ensure return_question_answer exists
                if 'return_question_answer' not in evaluation:
                    evaluation['return_question_answer'] = ""
                
                logger.info(f"Answer evaluated: score={evaluation['score']}, XP={evaluation['XP']}")
                return evaluation
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse evaluation JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                
                # Fallback: return safe default evaluation
                return {
                    "XP": 20,
                    "correct": False,
                    "score": 0.5,
                    "explanation": "Unable to fully evaluate. Partial credit given.",
                    "confidence": 0.3,
                    "followup_action": "none",
                    "return_question_answer": ""
                }
                
        except Exception as e:
            logger.error(f"Error in evaluate_answer: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "evaluate_answer"
            })
            return {
                "XP": 10,
                "correct": False,
                "score": 0.0,
                "explanation": "Evaluation failed. Try again.",
                "confidence": 0.0,
                "followup_action": "none",
                "return_question_answer": ""
            }
    
    def generate_insights(self, qa_records: list) -> dict:
        """
        Generate SWOT insights from tutoring session QA records.
        DEPRECATED: Use generate_boostme_insights() instead.
        Kept for backward compatibility.
        
        Args:
            qa_records: List of QA dicts with question, answer, score, xp
            
        Returns:
            Insights dict with strength, weakness, opportunity, threat
        """
        from .tanglish_prompts import build_insights_prompt
        import json
        
        try:
            # Build insights prompt
            prompt = build_insights_prompt(qa_records, [])
            
            # Call Gemini
            logger.info("Generating session insights...")
            response = self.generate_response(prompt, max_tokens=800)
            
            if response.startswith("Error:"):
                raise ValueError(f"LLM error: {response}")
            
            # Parse JSON response
            try:
                # Clean response
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                insights = json.loads(cleaned)
                
                # Validate required keys
                required_keys = ['strength', 'weakness', 'opportunity', 'threat']
                if not all(k in insights for k in required_keys):
                    raise ValueError("Missing required keys in insights")
                
                logger.info("Session insights generated successfully")
                return insights
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse insights JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                
                # Fallback: return generic insights
                return {
                    "strength": "Participated in tutoring session.",
                    "weakness": "Analysis unavailable.",
                    "opportunity": "Continue practicing regularly.",
                    "threat": "N/A"
                }
                
        except Exception as e:
            logger.error(f"Error in generate_insights: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "generate_insights"
            })
            return {
                "strength": "Session completed.",
                "weakness": "Unable to analyze.",
                "opportunity": "Try again.",
                "threat": "N/A"
            }
    
    def generate_boostme_insights(self, qa_records: list) -> dict:
        """
        Generate BoostMe insights (3 zones) from tutoring session QA records.
        Returns focus_zone, steady_zone, edge_zone as arrays of 2 Tanglish points each.
        
        Args:
            qa_records: List of QA dicts with question, answer, score, xp
            
        Returns:
            Dict with focus_zone, steady_zone, edge_zone (each is array of 2 strings)
        """
        import json
        
        # System prompt for BoostMe insights
        system_prompt = """You are an insights-generator for InzightEd-G for Tamil learners. Output JSON only (no commentary).
Language: Tanglish (Tamil in Latin letters). Keep each point concise (<= 15 words).
Produce three zones based on the student's performance. Each zone must be an array of exactly two short points (strings).

{
  "focus_zone": ["point1", "point2"],
  "steady_zone": ["point1", "point2"],
  "edge_zone": ["point1", "point2"]
}

ZONE DEFINITIONS & LOGIC

1. focus_zone → Core Weakness / Low Understanding  
   - Identify clear misunderstanding, wrong reasoning, or concept confusion.  
   - Highlight the root cause (concept gap, recall issue, or misread question).  
   - Mention what needs to improve, not just that it’s “wrong.”  
   - Avoid generic words like “mistake,” “confused,” or “wrong.”  
   - Output should point to *specific learning gap*.  

   Examples:  
   - "formula usage la thappu iruku, basics revise pannunga"  
   - "concept clarity illa, logic steps skip panniruka"  
   - "meaning miss panniruka, careful-a padikka venum"  
   - "application method wrong side la poiduchu"  

2. steady_zone → Strong / Confident Understanding  
   - Identify areas where the student showed consistent accuracy or strong reasoning.  
   - Highlight what they’re doing well — correct logic, structured solving, or recall clarity.  
   - Encourage retention of these skills.  
   - Avoid generic praise; focus on *specific strengths*.  

   Examples:  
   - "concept grip super, approach clear-a iruku"  
   - "logic perfect-a apply panniruka"  
   - "accuracy high, recall nalla aagiduchu"  
   - "pattern understanding romba solid"  

3. edge_zone → Growth Potential / Near-Mastery  
   - Identify areas where the student was almost correct or partially right.  
   - Logic or approach is right, but minor slip or clarity issue exists.  
   - Show how a small fix leads to full mastery.  
   - Tone should be positive and motivating.  

   Examples:  
   - "idea sari, last step la slip aagiduchu"  
   - "logic strong, wording improve panna mudiyum"  
   - "approach correct, calculation clarity venum"  
   - "almost correct, thoda polish panna super aagum"  

Each point should be in Tanglish and <= 15 words."""
        
        try:
            # Build context from QA records
            qa_summary = "\n".join([
                f"Q: {qa.get('question', 'N/A')[:100]}\n"
                f"A: {qa.get('answer', 'N/A')[:100]}\n"
                f"Score: {qa.get('score', 0)}, XP: {qa.get('xp', 0)}\n"
                for qa in qa_records[:10]  # Limit to first 10 QAs
            ])
            
            prompt = f"""{system_prompt}

Student's Question-Answer Performance:
{qa_summary}

Generate BoostMe insights in JSON:"""
            
            # Call Gemini
            logger.info("Generating BoostMe insights...")
            response = self.generate_response(prompt, max_tokens=600)
            
            if response.startswith("Error:"):
                raise ValueError(f"LLM error: {response}")
            
            # Parse JSON response
            try:
                # Clean response
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                insights = json.loads(cleaned)
                
                # Validate structure
                required_keys = ['focus_zone', 'steady_zone', 'edge_zone']
                if not all(k in insights for k in required_keys):
                    raise ValueError("Missing required zone keys")
                
                # Validate each zone is an array with 2 items
                for zone_key in required_keys:
                    if not isinstance(insights[zone_key], list) or len(insights[zone_key]) != 2:
                        raise ValueError(f"{zone_key} must be array of 2 strings")
                
                logger.info("BoostMe insights generated successfully")
                return insights
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse BoostMe insights JSON: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                
                # Fallback: return generic Tanglish insights
                return self._generate_fallback_boostme_insights(qa_records)
                
        except Exception as e:
            logger.error(f"Error in generate_boostme_insights: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "gemini_client",
                "method": "generate_boostme_insights"
            })
            return self._generate_fallback_boostme_insights(qa_records)
    
    def _generate_fallback_boostme_insights(self, qa_records: list) -> dict:
        """
        Generate deterministic fallback BoostMe insights based on QA performance.
        
        Args:
            qa_records: List of QA dicts with question, answer, score, xp
            
        Returns:
            Dict with focus_zone, steady_zone, edge_zone arrays
        """
        if not qa_records:
            return {
                "focus_zone": ["Session data unavailable", "Try answering more questions"],
                "steady_zone": ["Session participation good", "Keep learning regularly"],
                "edge_zone": ["Practice consistency venum", "More topics explore pannunga"]
            }
        
        # Calculate simple statistics
        total = len(qa_records)
        scores = [qa.get('score', 0) for qa in qa_records]
        avg_score = sum(scores) / total if total > 0 else 0
        high_scores = sum(1 for s in scores if s >= 0.75)
        low_scores = sum(1 for s in scores if s < 0.5)
        
        # Generate insights based on performance
        if avg_score >= 0.75:
            steady_zone = [
                f"Concept understanding romba nalla iruku",
                f"{high_scores}/{total} questions correct ah answer panninga"
            ]
        else:
            steady_zone = [
                "Session la participate panninga",
                "努力 continuous ah maintain pannunga"
            ]
        
        if low_scores > total // 2:
            focus_zone = [
                f"Basics practice venum - {low_scores} questions weak",
                "Core concepts marupadiyum revise pannunga"
            ]
        else:
            focus_zone = [
                "Some topics la confusion iruku",
                "Difficult questions ku extra attention venum"
            ]
        
        edge_zone = [
            "Apply concepts to new scenarios try pannunga",
            "Practice speed improve panna vendiyathu"
        ]
        
        return {
            "focus_zone": focus_zone,
            "steady_zone": steady_zone,
            "edge_zone": edge_zone
        }

# Module-level instance
gemini_client = GeminiLLMClient()