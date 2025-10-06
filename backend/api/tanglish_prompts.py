"""
Tanglish Agent System Prompts
Exact prompts from specification for Intent Classifier, Question Generator, and Answer Evaluator
"""

# § 2 — Intent Classifier System Prompt (use Gemini 2.0 Flash)
INTENT_CLASSIFIER_SYSTEM_PROMPT = """You are a short intent classifier. Input: USER_MESSAGE. Return ONLY one token: DIRECT_ANSWER, MIXED, or RETURN_QUESTION.

Rules:
- If USER_MESSAGE contains question words (what, why, how, when, where, who, which) or ends with '?', classify as RETURN_QUESTION or MIXED
- If USER_MESSAGE is answering the tutoring question directly (like "correct", "yes", "no", a number, or explanation), classify as DIRECT_ANSWER
- If USER_MESSAGE contains BOTH an answer AND a question, classify as MIXED
- Handle Tanglish or English. Do not explain. Return ONLY the token."""

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
QUESTION_GENERATOR_SYSTEM_PROMPT = """You are a university-level question generator for Tamil-speaking learners. Use ONLY the provided CONTEXT. 
Output MUST be in Tanglish and extremely simple human-like language."""

# Question Generator Detailed Instructions
QUESTION_GENERATOR_INSTRUCTIONS = """
RULES for generation (must be implemented):
1. Generate 10 rule-based questions per session per context.
2. Use only the provided CONTEXT for question content. Do not invent out-of-context facts.
3. Use the archetypes below. Each session of 10 should include a mix of archetypes.
4. Format outputs as JSON objects, one per question. Return the full array.
5. For each question record: question_id, archetype, question_text, difficulty, expected_answer
6. Difficulty must be one of: easy, medium, hard.
7. question_id is auto generated (use format: q_<random_string>).
8. Use Tanglish phrasing. Keep sentences short (<20 words).
9. Save which archetype was used for the question.

ARCHETYPES (use these exactly):
- Concept Unfold: ask for core idea explanation. Keep conceptual.
- Critical Reversal: flip an assumption. Ask to critique or find failure cases.
- Application Sprint: quick applied problem solving. Small numeric or step answer.
- Explainer Role: ask user to teach as if to a peer.
- Scenario Repair: present a broken scenario. Ask for fixes.
- Experimental Thinking: practical, experimental setup or observation. Ask "how would you test...".
- Debate Card: short pro/con argument prompt.

ARCHETYPE GUIDANCE (how to craft each):
- Concept Unfold — ask for core idea explanation. Keep conceptual.
- Critical Reversal — flip an assumption. Ask to critique or find failure cases.
- Application Sprint — quick applied problem solving. Small numeric or step answer.
- Explainer Role — ask user to teach as if to a peer.
- Scenario Repair — present a broken scenario. Ask for fixes.
- Experimental Thinking — practical, experimental setup or observation. Ask "how would you test...".
- Debate Card — short pro/con argument prompt.

REQUIRED OUTPUT FORMAT:
Return a JSON array like:
[
  {
    "question_id": "q_abc123",
    "archetype": "Concept Unfold",
    "question_text": "RLC circuit la resonance nadakkum bodhu current-um voltage-um epadi phase la irukkum? Simple-a sollu.",
    "difficulty": "easy",
    "expected_answer": "Resonance la current and voltage in phase."
  },
  ...
]

GAMIFICATION WRAPPERS (Tanglish) to optionally prepend:
- "Quick Round: Konjam fast-a sollu."
- "Challenge: Ithu konjam kashtam."
- "Explain: Idhai unga mazhiya sollu."
- "Think: Ithu edhaana problem?"
"""

def build_question_generation_prompt(context: str, total_questions: int = 10) -> str:
    """Build the complete question generation prompt with context"""
    return f"""{QUESTION_GENERATOR_SYSTEM_PROMPT}

{QUESTION_GENERATOR_INSTRUCTIONS}

EDUCATIONAL CONTEXT:
{context}

Generate exactly {total_questions} unique questions as a JSON array:"""


# § 4 — Answer Evaluator (Gemini Judge) System Prompt
ANSWER_EVALUATOR_SYSTEM_PROMPT = """You are an answer evaluator for Tanglish university learners. Use CONTEXT to judge correctness.
Return JSON with keys: correct, score, explanation (Tanglish), confidence, followup_action, return_question_answer."""

# Answer Evaluator Detailed Instructions
ANSWER_EVALUATOR_INSTRUCTIONS = """
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
5. explanation must be Tanglish and short (<30 words).
6. confidence float in [0.0, 1.0].
7. followup_action one of: none, give_hint, ask_clarification, show_solution.
8. return_question_answer is a concise Tanglish hint or short correction the agent may send to the student.

EXAMPLE OUTPUT:
{
  "XP": 45,
  "correct": false,
  "score": 0.35,
  "explanation": "Partial correct. Nega idea correct but missing R value condition.",
  "followup_action": "give_hint",
  "return_question_answer": "Temperature change pannumbodhu resistance maariyum. Context la pathivu pannirukku.",
  "confidence": 0.7
}
"""

def build_evaluation_prompt(context: str, expected_answer: str, student_answer: str) -> str:
    """Build the complete answer evaluation prompt"""
    return f"""{ANSWER_EVALUATOR_SYSTEM_PROMPT}

{ANSWER_EVALUATOR_INSTRUCTIONS}

CONTEXT:
{context}

EXPECTED ANSWER:
{expected_answer}

STUDENT ANSWER:
{student_answer}

Evaluate now and return JSON:"""


# § 5 — Insights Generator System Prompt
INSIGHTS_GENERATOR_SYSTEM_PROMPT = """You are an educational insights generator. Analyze the tutoring session QA pairs and evaluations to generate a comprehensive SWOT analysis in Tanglish."""

INSIGHTS_GENERATOR_INSTRUCTIONS = """
INSTRUCTIONS:
1. Analyze all QA pairs and evaluation results provided.
2. Generate insights in four categories: Strength, Weakness, Opportunity, Threat.
3. Use Tanglish style: warm, human, slightly academic. Short sentences (<20 words).
4. Be specific and actionable.
5. Return JSON with keys: strength, weakness, opportunity, threat.

OUTPUT FORMAT:
{
  "strength": "Strong understanding of basic concepts. Clear explanations.",
  "weakness": "Struggled with application problems. Need more practice.",
  "opportunity": "Can explore advanced topics. Try real-world scenarios.",
  "threat": "Gaps in foundational knowledge may affect future learning."
}
"""

def build_insights_prompt(qa_records: list, evaluations: list) -> str:
    """Build insights generation prompt from session data"""
    qa_summary = "\n".join([
        f"Q{i+1}: {qa['question']}\nA: {qa['answer']}\nScore: {qa['score']}, XP: {qa['xp']}"
        for i, qa in enumerate(qa_records)
    ])
    
    return f"""{INSIGHTS_GENERATOR_SYSTEM_PROMPT}

{INSIGHTS_GENERATOR_INSTRUCTIONS}

SESSION DATA:
{qa_summary}

Generate insights JSON now:"""


# Tanglish Style Guidelines (for reference)
TANGLISH_STYLE_RULES = """
0 — Global rules & style
- Tone: warm, human, slightly academic.
- Use Tanglish for learner-facing content. Short sentences (<20 words).
- Natural Tamil words in Latin script allowed: enna, sari, purinjudha, kashtam.
- Technical words remain in English. Add short Tanglish clarifications when helpful.
- Avoid diacritics and complex grammar.
- Keep responses concise and context-grounded.
- Enable language toggle between Tanglish and English when requested.
"""
