"""
Tanglish Agent System Prompts
Exact prompts from specification for Intent Classifier, Question Generator, and Answer Evaluator
"""

from .language_prompts import REQUIRED_OUTPUT_FORMATS as LANG_REQUIRED_OUTPUT_FORMATS, GAMIFICATION_WRAPPERS as LANG_GAMIFICATION_WRAPPERS

# § 2 — Intent Classifier System Prompt (use Gemini 2.0 Flash)
def get_intent_classifier_system_prompt(language: str = "tanglish") -> str:
    """Get intent classifier system prompt with dynamic language."""
    # Improve prompt clarity and precedence: prefer RETURN_QUESTION for clear questions
    # even when they are polite or prefaced (e.g. "let me know what is X?", "please tell me how...").
    return f"""You are a short intent classifier. Input: USER_MESSAGE. Return ONLY one token: DIRECT_ANSWER, MIXED, or RETURN_QUESTION.

Rules (priority order):
1) If USER_MESSAGE clearly asks a question (contains question words such as what/why/how/when/where/who/which or ends with '?'), classify as RETURN_QUESTION unless the message also contains an explicit answer phrase (see rule 2).
   - Polite prefacing phrases such as "let me know", "please tell me", "can you tell me", "i want to know", "please explain" should NOT by themselves make the message MIXED. These are still RETURN_QUESTION when a question is being asked.
2) If USER_MESSAGE is providing an explicit answer to the tutoring question (examples: "the answer is 42", "it's 3", "yes", "no", a numeric or multi-word explanation that asserts a solution), classify as DIRECT_ANSWER.
3) If USER_MESSAGE contains BOTH an explicit answer (an assertion, a clear solution, or numeric answer) AND a separate question component in the same message, classify as MIXED.

Examples (input -> expected token):
- "Let me know what is air conditioning?" -> RETURN_QUESTION
- "What is air conditioning?" -> RETURN_QUESTION
- "Yes, it's 42" -> DIRECT_ANSWER
- "The answer is 3. Also, can you show how to derive it?" -> MIXED

- Handle {language} or English. Do not explain. Return ONLY the token."""

# Intent Classifier Fallback Rules (deterministic)
def fallback_intent_classifier(user_message: str) -> str:
    """
    Fallback deterministic rule when Gemini API fails.
    Checks for presence of question markers or clarification words.
    """
    msg_lower = user_message.lower()
    
    print(f"[FALLBACK] Classifying: '{user_message}'")
    
    # Question indicators - expanded list
    question_markers = [
        '?', 'why', 'how', 'what', 'when', 'where', 'who', 'which', 'whom',
        'is', 'are', 'can', 'could', 'would', 'should', 'do', 'does', 'did',
        'means', 'mean', 'meaning'  # Added for "what is X means?" patterns
    ]
    tanglish_question_words = [
        'enna', 'sari', 'purinjudha', 'epadi', 'eppadi', 'ethuku', 'yaar',
        'na', 'nu'  # Common Tanglish question markers
    ]
    
    # Check if message starts with question words (strong indicator)
    first_word = msg_lower.split()[0] if msg_lower.split() else ''
    starts_with_question = first_word in ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'is', 'are', 'can', 'could', 'do', 'does']
    
    # Check for any question markers
    has_question = any(marker in msg_lower for marker in question_markers + tanglish_question_words)
    
    print(f"[FALLBACK] starts_with_question: {starts_with_question}, has_question: {has_question}")
    
    # Strong question indicators
    if starts_with_question or '?' in user_message:
        words = msg_lower.split()
        if len(words) > 15:  # Very long - might contain both answer and question
            print(f"[FALLBACK] → MIXED (long message with question)")
            return "MIXED"
        else:
            print(f"[FALLBACK] → RETURN_QUESTION (clear question)")
            return "RETURN_QUESTION"
    
    # Weak question indicators
    if has_question:
        # Check if message also contains non-question content (potential answer)
        words = msg_lower.split()
        if len(words) > 12:  # Longer messages might contain both answer and question
            print(f"[FALLBACK] → MIXED (answer + question)")
            return "MIXED"
        else:
            print(f"[FALLBACK] → RETURN_QUESTION (question detected)")
            return "RETURN_QUESTION"
    else:
        # No question markers - likely a direct answer
        if len(user_message.strip()) > 2:  # Reasonable answer length
            print(f"[FALLBACK] → DIRECT_ANSWER (no question markers)")
            return "DIRECT_ANSWER"
        else:
            print(f"[FALLBACK] → RETURN_QUESTION (too short, unclear)")
            return "RETURN_QUESTION"  # Too short, might need clarification


# § 3 — Question Generator System Prompt
def get_question_generator_system_prompt(language: str = "tanglish") -> str:
    """Get question generator system prompt with dynamic language."""
    language_instruction = "Output SHOULD be in {language}."
    if language.lower() == "tanglish":
        language_instruction = "Output SHOULD be either English or Tanglish (Tamil words transliterated into Latin letters). DO NOT use Tamil script (தமிழ்) or pure Tamil words in native script. If you include Tamil words, always transliterate them into Latin letters (Tanglish)."
    
    return f"""You are a university-level question generator for learners. Use ONLY the provided CONTEXT.
{language_instruction} Keep language simple and human-like."""

# Question Generator Detailed Instructions
def get_question_generator_instructions(language: str = "tanglish") -> str:
    """Get question generator instructions with dynamic language."""
    language_phrasing = f"Use {language} phrasing"
    if language.lower() == "tanglish":
        language_phrasing = "Use Tanglish phrasing (Tamil words MUST be transliterated into Latin letters) or English. DO NOT output Tamil in native Tamil script"
    # Archetypes and guidance (language-agnostic block)
    archetypes_block = '''
ARCHETYPE GUIDANCE (how to craft each):
- Concept Unfold — ask for core idea explanation. Keep conceptual.
- Critical Reversal — flip an assumption. Ask to critique or find failure cases.
- Application Sprint — quick applied problem solving. Small numeric or step answer.
- Explainer Role — ask user to teach as if to a peer.
- Scenario Repair — present a broken scenario. Ask for fixes.
- Experimental Thinking — practical, experimental setup or observation. Ask "how would you test...".
- Debate Card — short pro/con argument prompt.
'''

    # Required output and gamification are provided by language_prompts dicts (per-language)
    key = (language or 'tanglish').lower()
    required_output = LANG_REQUIRED_OUTPUT_FORMATS.get(key, LANG_REQUIRED_OUTPUT_FORMATS.get('tanglish', ''))
    gamification = LANG_GAMIFICATION_WRAPPERS.get(key, LANG_GAMIFICATION_WRAPPERS.get('tanglish', ''))

    return f"""
RULES for generation (must be implemented):
1. Generate 10 rule-based questions per session per context.
2. Use only the provided CONTEXT for question content. Do not invent out-of-context facts.
3. Use the archetypes below. Each session of 10 should include a mix of archetypes.
4. When appropriate, phrase some questions in an indirect or "twisted" (Socratic) style to encourage inference and deeper thinking.
   - Examples: present a short scenario, a partial fact, or a disguised prompt that requires the learner to infer the target concept.
   - Do this for at most ~30-40% of the questions (i.e., 3-4 questions out of 10) and only when the CONTEXT supports it.
   - IMPORTANT: Even for indirect questions, ensure the `expected_answer` field clearly maps to the intended correct response so automatic evaluation remains reliable.
5. Include a mix of question types. For each question object, add an optional `question_type` field with one of: `descriptive`, `true_false`, `problem`.
        - Aim for a balanced mix over 10 questions (suggested: 5-6 descriptive, 2-3 true_false, 2-3 problem-solving) when the CONTEXT allows.
        - For `true_false` use `expected_answer` = `True` or `False` (boolean or string acceptable).
        - For `problem` questions, `expected_answer` should contain the final numeric/short answer and (optionally) a brief solution outline.
        - If a question_type is omitted, treat it as `descriptive` by default.
6. Format outputs as JSON objects, one per question. Return the full array.
7. For each question record: question_id, archetype, question_text, difficulty, expected_answer
8. Difficulty must be one of: easy, medium, hard.
9. question_id is auto generated (use format: q_<random_string>).
10. {language_phrasing}. Keep sentences short (<20 words).
11. Save which archetype was used for the question.
12. Where contextually appropriate, rewrite the question in the voice of a popular Tamil Nadu personality (e.g., Rajinikanth, Vijay, or Ajith), using their natural tone, famous dialogue style, or familiar movie references. Only apply this when it enhances engagement — keep the question neutral if forced usage feels unnatural. Ensure academic accuracy remains intact.
{archetypes_block}

{required_output}

{gamification}
"""

def build_question_generation_prompt(context: str, total_questions: int = 10, language: str = "tanglish") -> str:
    """Build the complete question generation prompt with context and language"""
    system_prompt = get_question_generator_system_prompt(language)
    instructions = get_question_generator_instructions(language)
    
    return f"""{system_prompt}

{instructions}

EDUCATIONAL CONTEXT:
{context}

Generate exactly {total_questions} unique questions as a JSON array:"""


# § 4 — Answer Evaluator (Gemini Judge) System Prompt
def get_answer_evaluator_system_prompt(language: str = "tanglish") -> str:
    """Get answer evaluator system prompt with dynamic language."""
    return f"""You are an answer evaluator for university learners. Use CONTEXT to judge correctness.
Return JSON with keys: correct, score, explanation ({language}), confidence, followup_action, return_question_answer."""

# Answer Evaluator Detailed Instructions
def get_answer_evaluator_instructions(language: str = "tanglish") -> str:
    """Get answer evaluator instructions with dynamic language."""
    return f"""
EVALUATOR RULES:
1. Compare student_answer against expected_answer.
2. Score in [0.0, 1.0]. Use partial credit when partial correctness exists. Score must reflect key-concept coverage.
3. Give XP points (1-100) based on how correct the answer is: 
   - score >= 0.9: 80-100 XP
   - score >= 0.75: 60-79 XP
   - score >= 0.5: 40-59 XP
   - score >= 0.25: 20-39 XP
   - score < 0.25: 1-19 XP
4. correct is true if score >= 0.75 unless rubric says otherwise.
5. explanation (<30 words, in {language}): Summarize the student’s understanding of the question. If correct, state it clearly; if not, highlight the misunderstanding or missing concept based on their answer.
6. confidence float in [0.0, 1.0].
7. followup_action one of: none, give_hint, ask_clarification, show_solution.
8. return_question_answer is a concise {language} hint or short correction the agent may send to the student.

EXAMPLE OUTPUT:
{{
  "XP": 45,
  "correct": false,
  "score": 0.35,
  "explanation": "Partial correct. Nega idea correct but missing R value condition.",
  "followup_action": "give_hint",
  "return_question_answer": "Temperature change pannumbodhu resistance maariyum. Context la pathivu pannirukku.",
  "confidence": 0.7
}}
"""

def build_evaluation_prompt(context: str, expected_answer: str, student_answer: str, language: str = "tanglish") -> str:
    """Build the complete answer evaluation prompt with language"""
    system_prompt = get_answer_evaluator_system_prompt(language)
    instructions = get_answer_evaluator_instructions(language)
    
    return f"""{system_prompt}

{instructions}

CONTEXT:
{context}

EXPECTED ANSWER:
{expected_answer}

STUDENT ANSWER:
{student_answer}

Evaluate now and return JSON:"""




# Tanglish Style Guidelines (for reference)
def get_tanglish_style_rules(language: str = "tanglish") -> str:
    """Get style rules with dynamic language."""
    language_instructions = f"Use {language} for learner-facing content."
    if language.lower() == "tanglish":
        language_instructions = """Use Tanglish for learner-facing content (Tamil words must be transliterated into Latin letters). DO NOT use Tamil script (தமிழ்) anywhere in learner-facing outputs.
- Natural Tamil words in Latin script allowed: enna, sari, purinjudha, kashtam."""
    
    return f"""
0 — Global rules & style
- Tone: warm, human, slightly academic.
- {language_instructions}
- Technical words remain in English. Add short clarifications when helpful.
- Avoid diacritics and complex grammar.
- Keep responses concise and context-grounded.
- Enable language toggle between different languages when requested.
"""


# Common gamification wrappers that some generators may prepend (kept for reference)
GAMIFICATION_WRAPPERS = [
    "Quick Round:",
    "Challenge:",
    "Explain:",
    "Think:",
    "Debate:"
]


def strip_gamification_prefix(text: str) -> str:
    """Remove common gamification prefixes such as 'Explain:', 'Debate:', etc.

    This is a defensive client-side sanitizer. It strips these prefixes if they
    appear at the start of the LLM output, preserving the rest of the text.
    """
    if not text:
        return text

    s = text.lstrip()  # remove leading whitespace
    for prefix in GAMIFICATION_WRAPPERS:
        if s.startswith(prefix):
            # remove the prefix and any following whitespace or punctuation
            stripped = s[len(prefix):].lstrip(' \t\n:-')
            return stripped

    # Also handle cases where wrapper is in the first line followed by newline
    first_line_end = s.find('\n')
    if first_line_end != -1:
        first_line = s[:first_line_end]
        for prefix in GAMIFICATION_WRAPPERS:
            if first_line.startswith(prefix):
                stripped_first = first_line[len(prefix):].lstrip(' \t\n:-')
                return stripped_first + s[first_line_end:]

    return text
