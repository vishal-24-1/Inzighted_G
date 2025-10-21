"""
Message Validation Module
Detects invalid user inputs: emoji-only, gibberish, and irrelevant answers.
Integrated into TutorAgent flow to ensure quality answers before evaluation.
"""

import re
import unicodedata
import logging
from django.conf import settings
from typing import Optional, Tuple
import sentry_sdk

logger = logging.getLogger(__name__)

# Configuration with defaults (can be overridden via settings or env vars)
IRRELEVANCE_QUESTION_KEYWORDS_MIN = getattr(settings, 'MESSAGE_VALIDATION_IRRELEVANCE_QUESTION_KEYWORDS_MIN', 1)
GIBBERISH_MIN_ALPHA_RATIO = getattr(settings, 'MESSAGE_VALIDATION_GIBBERISH_MIN_ALPHA_RATIO', 0.5)
MIN_WORDS = getattr(settings, 'MESSAGE_VALIDATION_MIN_WORDS', 2)
DEBUG_LOGGING = getattr(settings, 'MESSAGE_VALIDATION_DEBUG_LOGGING', False)

# Import LLM client for optional short-answer validation
try:
    from .gemini_client import gemini_client
    HAS_LLM_CLIENT = True
except Exception:
    gemini_client = None
    HAS_LLM_CLIENT = False


def is_emoji_only(text: str) -> bool:
    """
    Check if message consists only of emojis/reactions (no meaningful words).
    
    Examples that return True:
    - "🤔"
    - "👍"
    - "😂😂😂"
    - "🔥🔥"
    
    Examples that return False:
    - "ok 👍"
    - "yes please"
    - "I think 🤔"
    
    Args:
        text: User message to check
        
    Returns:
        True if message is emoji-only
    """
    if not text or not text.strip():
        return False
    
    # Remove whitespace
    cleaned = text.strip()
    
    # Check if very short and no alphanumeric
    if len(cleaned) <= 5:
        # Count alphanumeric characters
        alphanumeric_count = sum(1 for c in cleaned if c.isalnum())
        if alphanumeric_count == 0:
            # Likely emoji or punctuation only
            if DEBUG_LOGGING:
                logger.debug(f"[VALIDATION] Detected emoji-only (short, no alnum): '{text}'")
            return True
    
    # Check if all characters are emoji or punctuation
    char_types = []
    for char in cleaned:
        if char.isspace():
            continue
        cat = unicodedata.category(char)
        # Emoji categories: So (Symbol, Other), Sk (Symbol, Modifier)
        # Punctuation: Po, Ps, Pe, Pd, Pc, Pi, Pf
        if cat.startswith('S') or cat.startswith('P'):
            char_types.append('emoji_punct')
        elif char.isalnum():
            char_types.append('alnum')
        else:
            char_types.append('other')
    
    # If no alphanumeric and some emoji/punct -> emoji-only
    if 'alnum' not in char_types and 'emoji_punct' in char_types:
        if DEBUG_LOGGING:
            logger.debug(f"[VALIDATION] Detected emoji-only (no alnum, has emoji/punct): '{text}'")
        return True
    
    return False


def is_gibberish(text: str, expected_answer: Optional[str] = None) -> bool:
    """
    Check if message is gibberish/nonsensical input.
    
    Heuristics:
    1. Very short with no coherent words (< MIN_WORDS)
    2. Low alphabetic character ratio (< GIBBERISH_MIN_ALPHA_RATIO)
    3. Excessive character repetition (e.g., "aaaaaaa", "??????")
    4. Random character sequences with no vowels
    
    Special handling:
    - If expected_answer is numeric/short, relax word count requirement
    - Single valid words/numbers are acceptable
    
    Examples that return True:
    - "asdkjasd 123???"
    - "hfjhfhf"
    - "???????????"
    - "xyzxyzxyz"
    
    Examples that return False:
    - "42" (valid numeric)
    - "NaOH" (valid chemical)
    - "photosynthesis" (valid word)
    - "My answer is X"
    
    Args:
        text: User message to check
        expected_answer: Expected answer (if numeric/short, relax checks)
        
    Returns:
        True if message appears to be gibberish
    """
    if not text or not text.strip():
        return True  # Empty is treated as gibberish
    
    cleaned = text.strip()
    
    # Exception: if expected answer is numeric or very short, allow numeric/short answers
    if expected_answer:
        exp_clean = expected_answer.strip()
        # Check if expected answer is numeric or chemical notation
        if len(exp_clean) < 10 or exp_clean.replace('.', '').replace('-', '').isdigit():
            # Allow numeric answers, chemical formulas, etc.
            if cleaned.replace('.', '').replace('-', '').replace(' ', '').isalnum():
                if DEBUG_LOGGING:
                    logger.debug(f"[VALIDATION] Allowed short/numeric answer: '{text}'")
                return False
    
    # Count words (split by whitespace)
    words = cleaned.split()
    word_count = len(words)
    
    # Heuristic 1: Too few words (but allow single valid words)
    if word_count < MIN_WORDS:
        # Check if single word is a valid dictionary-like word (has vowels, reasonable length)
        if word_count == 1:
            word = words[0].lower()
            # Allow if contains vowels and is alphanumeric
            if any(v in word for v in 'aeiou') and word.isalpha() and len(word) >= 3:
                return False
            # Allow pure numeric
            if word.replace('.', '').replace('-', '').isdigit():
                return False
        
        if DEBUG_LOGGING:
            logger.debug(f"[VALIDATION] Detected gibberish (too few words: {word_count}): '{text}'")
        return True
    
    # Heuristic 2: Low alphabetic ratio
    total_chars = len(cleaned.replace(' ', ''))
    alpha_chars = sum(1 for c in cleaned if c.isalpha())
    alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0
    
    if alpha_ratio < GIBBERISH_MIN_ALPHA_RATIO:
        if DEBUG_LOGGING:
            logger.debug(f"[VALIDATION] Detected gibberish (low alpha ratio: {alpha_ratio:.2f}): '{text}'")
        return True
    
    # Heuristic 3: Excessive repetition (same character repeated > 5 times)
    repetition_pattern = re.compile(r'(.)\1{5,}')
    if repetition_pattern.search(cleaned):
        if DEBUG_LOGGING:
            logger.debug(f"[VALIDATION] Detected gibberish (char repetition): '{text}'")
        return True
    
    # Heuristic 4: No vowels in multi-word response (likely keyboard mashing)
    if word_count >= 2:
        has_vowel = any(v in cleaned.lower() for v in 'aeiou')
        if not has_vowel:
            if DEBUG_LOGGING:
                logger.debug(f"[VALIDATION] Detected gibberish (no vowels): '{text}'")
            return True
    
    return False


def is_irrelevant_answer(user_message: str, question_text: str, expected_answer: Optional[str] = None) -> Tuple[bool, float]:
    """
    Check if user message is irrelevant/off-topic to the current question.
    
    Simplified approach (no embeddings):
    - Use intent classification to detect if user is asking a RETURN_QUESTION
    - If RETURN_QUESTION detected, it's handled by existing flow (not irrelevant)
    - For DIRECT_ANSWER or MIXED, check if message contains ANY keywords from the question
    - If no keyword overlap, likely irrelevant (e.g., "I like pizza" vs "Explain photosynthesis")
    
    Examples that return (True, low_score):
    - "I like pizza" when question is "Explain photosynthesis"
    - "My dog is cute" when question is "What is NaOH?"
    - "What's your name?" when question is about physics
    
    Examples that return (False, high_score):
    - "Plants use sunlight" when question is "Explain photosynthesis"
    - "It's a base" when question is "What is NaOH?"
    - Any answer containing keywords from the question
    
    Args:
        user_message: User's response
        question_text: Current tutoring question
        expected_answer: Expected answer (optional, not used in simplified approach)
        
    Returns:
        Tuple of (is_irrelevant: bool, relevance_score: float)
        relevance_score: 0.0 (completely irrelevant) to 1.0 (highly relevant)
    """
    if not user_message or not question_text:
        return True, 0.0
    
    # Normalize text
    msg_lower = user_message.lower().strip()
    q_lower = question_text.lower().strip()
    
    # Extract keywords from question (words longer than 3 chars, excluding common words)
    common_words = {'the', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when', 'where', 
                    'which', 'who', 'does', 'did', 'can', 'will', 'would', 'could', 'should',
                    'this', 'that', 'these', 'those', 'explain', 'describe', 'define', 'tell'}
    
    # Tokenize question
    q_words = re.findall(r'\w+', q_lower)
    q_keywords = [w for w in q_words if len(w) > 3 and w not in common_words]
    
    if DEBUG_LOGGING:
        logger.debug(f"[VALIDATION] Question keywords: {q_keywords}")
    
    # Check for keyword overlap (use word-boundary matching)
    matched_keywords = 0
    for keyword in q_keywords:
        if re.search(r"\b" + re.escape(keyword) + r"\b", msg_lower):
            matched_keywords += 1

    # Calculate simple relevance score based on keyword overlap
    if len(q_keywords) == 0:
        relevance_score = 0.5
    else:
        relevance_score = matched_keywords / len(q_keywords)

    # Threshold: if less than IRRELEVANCE_QUESTION_KEYWORDS_MIN keywords matched, likely irrelevant by keyword heuristic
    is_irrelevant = matched_keywords < IRRELEVANCE_QUESTION_KEYWORDS_MIN
    
    if DEBUG_LOGGING:
        logger.debug(f"[VALIDATION] Relevance check: matched={matched_keywords}/{len(q_keywords)}, "
                    f"score={relevance_score:.2f}, irrelevant={is_irrelevant}")
    
    # Additional heuristic: if message is very generic and doesn't match any keyword
    generic_phrases = ['i like', 'my favorite', 'i think', 'i believe', 'in my opinion',
                       'what is your', 'who are you', 'tell me about yourself']
    if any(phrase in msg_lower for phrase in generic_phrases) and matched_keywords == 0:
        if DEBUG_LOGGING:
            logger.debug(f"[VALIDATION] Detected generic irrelevant phrase")
        return True, 0.1

    # Additional: Detect product/platform meta-questions that are off-topic (support, pricing, profile, chatbot info)
    meta_phrases = [
        'price', 'pricing', 'cost', 'how much', 'subscription', 'plan', 'buy', 'purchase',
        'profile photo', 'change profile', 'edit profile', 'account settings',
        'how to contact', 'contact support', 'support', 'help center', 'refund',
        'what does this product do', 'what is this product', 'where to change', 'where can i',
        'chatbot', 'what is this platform', 'demo', 'download app'
    ]

    for p in meta_phrases:
        if p in msg_lower:
            if DEBUG_LOGGING:
                logger.debug(f"[VALIDATION] Detected meta/platform question phrase: '{p}'")
            # Consider meta-questions irrelevant with low relevance score
            return True, 0.0

    # If LLM is available, ask it to decide relevance when keyword heuristics are inconclusive
    if HAS_LLM_CLIENT and gemini_client and gemini_client.is_available():
        try:
            llm_prompt = (
                f"You are a relevance judge.\nQuestion: {question_text}\n"
                f"Expected answer: {expected_answer or ''}\nUser answer: {user_message}\n"
                "Task: Return a single number between 0 and 1 indicating how relevant the user answer is to the question "
                "(0 = completely irrelevant, 1 = fully relevant). Return only the number."
            )
            llm_resp = gemini_client.generate_response(llm_prompt, max_tokens=16, max_words=15)
            if DEBUG_LOGGING:
                logger.debug(f"[VALIDATION] Irrelevance LLM response: '{llm_resp}'")

            if llm_resp:
                # Extract first token that looks like a number
                match = re.search(r"([01](?:\.\d+)?)", llm_resp)
                if match:
                    score = float(match.group(1))
                    # If LLM says zero relevance, treat as irrelevant
                    if score <= 0.0:
                        return True, 0.0
                    # Otherwise, update score and determine irrelevance
                    relevance_score = max(relevance_score, score)
                    is_irrelevant = score < 0.1 or is_irrelevant
                else:
                    if DEBUG_LOGGING:
                        logger.debug("[VALIDATION] LLM response contained no numeric score; ignoring")

        except Exception as e:
            logger.error(f"[VALIDATION] Irrelevance LLM check failed: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "message_validation",
                "method": "irrelevance_llm_check",
                "user_message": user_message[:100]
            })

    return is_irrelevant, relevance_score


def is_admission_of_ignorance(user_message: str) -> bool:
    """
    Detect common phrases where the user admits they don't know the answer.
    Examples: "I don't know", "idk", "no idea", "theriyala", "I don't remember"
    Returns True if message is an admission of ignorance.
    """
    if not user_message or not user_message.strip():
        return False

    # Lowercase and normalize punctuation so trailing ellipses or extra punctuation don't block matches
    msg = user_message.lower().strip()
    # Replace non-word characters (except apostrophes) with space, collapse multiple spaces
    normalized = re.sub(r"[^\w\s']", ' ', msg)
    normalized = re.sub(r"\s+", ' ', normalized).strip()

    # Regex patterns to match admission of ignorance variants
    pattern = re.compile(r"\b(idk|dont know|don't know|no idea|theriyala|i dont remember|i don't remember|dont remember|not sure)\b")

    if pattern.search(normalized):
        return True

    return False


def enforce_max_words(text: str, max_words: int = 15) -> str:
    """
    Truncate the given text to at most max_words words. Preserve punctuation at end if present.
    Returns the truncated string.
    """
    if not text:
        return text
    words = text.strip().split()
    if len(words) <= max_words:
        return text.strip()
    truncated = ' '.join(words[:max_words]).strip()
    # Ensure the truncated text ends with a punctuation mark for readability
    if not re.search(r"[.!?]$", truncated):
        truncated = truncated + '...'
    return truncated


def categorize_invalid_message(
    user_message: str, 
    current_question_text: str, 
    expected_answer: Optional[str] = None
) -> Optional[str]:
    """
    Categorize if user message is invalid and return the category.
    
    Checks are performed in order:
    1. Emoji-only
    2. Gibberish
    3. Irrelevant (off-topic)
    
    Args:
        user_message: User's response
        current_question_text: Current tutoring question
        expected_answer: Expected answer (optional, used for context)
        
    Returns:
        One of: "emoji", "gibberish", "irrelevant", or None if message is valid
    """
    try:
        # Accept admission of ignorance (e.g., "I don't know") as valid and proceed
        if is_admission_of_ignorance(user_message):
            if DEBUG_LOGGING:
                logger.debug(f"[VALIDATION] Admission of ignorance accepted: '{user_message}'")
            return None

        # If LLM intent classifier is available, check if user is asking a RETURN_QUESTION or MIXED.
        # For both cases, accept the message as valid if it contains a genuine question component
        # (only reject if it's a meta/platform off-topic question).
        if HAS_LLM_CLIENT and gemini_client and gemini_client.is_available():
            try:
                intent_token = gemini_client.classify_intent(user_message)
                if DEBUG_LOGGING:
                    logger.debug(f"[VALIDATION] Intent classifier token: {intent_token}")
                
                # For RETURN_QUESTION and MIXED: only reject if meta/platform query detected
                if intent_token in ['RETURN_QUESTION', 'MIXED']:
                    # Check only for meta/platform phrases (not general irrelevance)
                    msg_lower = user_message.lower().strip()
                    meta_phrases = [
                        'price', 'pricing', 'cost', 'how much', 'subscription', 'plan', 'buy', 'purchase',
                        'profile photo', 'change profile', 'edit profile', 'account settings',
                        'how to contact', 'contact support', 'support', 'help center', 'refund',
                        'what does this product do', 'what is this product', 'where to change', 'where can i',
                        'chatbot', 'what is this platform', 'demo', 'download app'
                    ]
                    
                    is_meta_query = any(p in msg_lower for p in meta_phrases)
                    
                    if is_meta_query:
                        if DEBUG_LOGGING:
                            logger.debug(f"[VALIDATION] {intent_token} contains meta/platform query; flagging as irrelevant: '{user_message}'")
                        return 'irrelevant'
                    else:
                        if DEBUG_LOGGING:
                            logger.debug(f"[VALIDATION] {intent_token} intent accepted as valid: '{user_message}'")
                        return None
                        
            except Exception as e:
                # classifier failure should not block validation; fall back to heuristics
                if DEBUG_LOGGING:
                    logger.debug(f"[VALIDATION] Intent classifier failed: {e}")

        # New: Short-answer handling (1-3 words)
        # If a user responds with 1-3 words, mark as potentially insufficient and optionally ask LLM
        short_words = None
        if user_message and user_message.strip():
            short_words = [w for w in user_message.strip().split() if w]

        if short_words and 1 <= len(short_words) <= 3:
            # Mark as potentially insufficient. If LLM client available, ask it to judge sufficiency.
            if HAS_LLM_CLIENT and gemini_client and gemini_client.is_available():
                try:
                    # Build a concise prompt for the LLM
                    # The LLM is asked to reply with one token: sufficient, needs explanation, or invalid
                    prompt = (
                        f"Question: {current_question_text}\n"
                        f"User Answer: {user_message}\n"
                        "Task: Decide if the user's short answer is sufficient. "
                        "If it is sufficient respond with the single word: sufficient. "
                        "If the answer needs a brief explanation respond with the single phrase: needs explanation. "
                        "If the answer is invalid respond with the single word: invalid."
                    )
                    llm_resp = gemini_client.generate_response(prompt, max_tokens=16, max_words=15)
                    if DEBUG_LOGGING:
                        logger.debug(f"[VALIDATION] Short-answer LLM response: '{llm_resp}'")

                    token = (llm_resp or "").strip().split()[0].lower() if llm_resp else ""

                    if token == 'sufficient':
                        # Treat as valid and continue
                        if DEBUG_LOGGING:
                            logger.debug("[VALIDATION] Short answer judged sufficient by LLM")
                    elif token == 'needs':
                        # LLM may respond 'needs explanation' - treat as needs explanation
                        if DEBUG_LOGGING:
                            logger.debug("[VALIDATION] Short answer judged needing explanation by LLM")
                        return 'gibberish'  # re-use gibberish category to trigger re-ask flow (keeps downstream handling simple)
                    elif token == 'needs_explanation' or 'needs' in token:
                        return 'gibberish'
                    elif token == 'invalid':
                        return 'gibberish'
                    else:
                        # If LLM output is unexpected, fall through to existing heuristics
                        if DEBUG_LOGGING:
                            logger.debug(f"[VALIDATION] Unexpected LLM token: '{token}', falling back")

                except Exception as e:
                    # Log but don't block evaluation; fall back to heuristics
                    logger.error(f"[VALIDATION] Short-answer LLM check failed: {e}")
                    sentry_sdk.capture_exception(e, extras={
                        "component": "message_validation",
                        "method": "short_answer_llm_check",
                        "user_message": user_message[:100]
                    })
            else:
                # No LLM available: conservatively treat short answer as potentially insufficient
                if DEBUG_LOGGING:
                    logger.debug("[VALIDATION] No LLM available to validate short answer; marking as potentially insufficient")
                return 'gibberish'

        # Check 1: Emoji-only
        if is_emoji_only(user_message):
            logger.info(f"[VALIDATION] Detected emoji-only message: '{user_message[:50]}'")
            sentry_sdk.add_breadcrumb(
                category='validation',
                message='Emoji-only message detected',
                level='info'
            )
            return "emoji"
        
        # Check 2: Gibberish
        if is_gibberish(user_message, expected_answer):
            logger.info(f"[VALIDATION] Detected gibberish message: '{user_message[:50]}'")
            sentry_sdk.add_breadcrumb(
                category='validation',
                message='Gibberish message detected',
                level='info'
            )
            return "gibberish"
        
        # Check 3: Irrelevant
        is_irrelevant, relevance_score = is_irrelevant_answer(
            user_message, 
            current_question_text, 
            expected_answer
        )
        
        if is_irrelevant:
            logger.info(f"[VALIDATION] Detected irrelevant message (score={relevance_score:.2f}): '{user_message[:50]}'")
            sentry_sdk.add_breadcrumb(
                category='validation',
                message=f'Irrelevant message detected (score={relevance_score:.2f})',
                level='info'
            )
            return "irrelevant"
        
        # Message is valid
        return None
        
    except Exception as e:
        logger.error(f"[VALIDATION] Error in categorize_invalid_message: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "message_validation",
            "method": "categorize_invalid_message",
            "user_message": user_message[:100]
        })
        # On error, treat message as valid (fail open)
        return None


def get_corrective_message(category: str, question_text: str, language: str = "tanglish", user_message: Optional[str] = None) -> str:
    """
    Get corrective message for invalid input category.
    
    Args:
        category: One of "emoji", "gibberish", "irrelevant"
        question_text: Current question to re-ask
        language: Response language (tanglish or english)
        
    Returns:
        Corrective message with re-asked question
    """
    # Base corrective messages
    if language == "english":
        corrective_messages = {
            "emoji": "I noticed you reacted with an emoji. Could you please answer in words so I can understand your response better?",
            "gibberish": "I couldn't understand that response. Could you please answer more clearly based on the question?",
            "irrelevant": "That seems unrelated to the question. Could you try answering based on the original topic?"
        }
    else:  # tanglish
        corrective_messages = {
            "emoji": "I noticed you reacted with an emoji. Please words la answer pannunga so I can understand better.",
            "gibberish": "I couldn't understand that response. Please konjam clear ah answer pannunga based on the question.",
            "irrelevant": "I cannot answer that. Do you have any question relevant to the original question?"
        }

    # If category is 'irrelevant', and we have an LLM, try to generate a tailored corrective message
    if category == 'irrelevant' and HAS_LLM_CLIENT and gemini_client and gemini_client.is_available():
        try:
            # Build a short system-style prompt to produce a concise corrective message
            lang_label = 'English' if language == 'english' else 'Tanglish'
            lm_prompt = (
                f"You are a polite tutoring assistant that corrects off-topic student replies."
                f"\nLanguage: {lang_label}. Keep the message concise (<= 30 words)."
                "\nTask: The user sent an off-topic question or comment. Generate a single short reply that says you cannot answer that and asks the user to provide a question or answer relevant to the original tutoring question."
            )
            if user_message:
                lm_prompt += f"\nUser message: {user_message}"
            lm_prompt += f"\nRe-ask the original question at the end. Output only the reply text."

            lm_resp = gemini_client.generate_response(lm_prompt, max_tokens=80, max_words=15)
            if lm_resp and isinstance(lm_resp, str) and lm_resp.strip():
                # Use LLM-generated message but ensure we append the re-asked question (if not already present)
                reply = lm_resp.strip()
                # Enforce concise reply (<= 15 words) for the initial corrective sentence
                concise = enforce_max_words(reply, max_words=15)
                if question_text not in reply:
                    return concise + f"\n\nLet me repeat the question:\n{question_text}"
                # If LLM already included the question, still ensure first part is concise
                return concise

        except Exception as e:
            logger.error(f"[VALIDATION] Failed to generate tailored corrective message: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "message_validation",
                "method": "get_corrective_message_llm",
                "user_message": (user_message or '')[:100]
            })

    base_message = corrective_messages.get(category, corrective_messages["gibberish"])

    # Enforce concise base message
    concise_base = enforce_max_words(base_message, max_words=15)

    # Re-ask the question
    reask_prompt = f"\n\nLet me repeat the question:\n{question_text}"

    return concise_base + reask_prompt
