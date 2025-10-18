"""
Language-specific prompt fragments.
This module centralizes required-output-format and gamification wrappers per language.
"""

"""
Key/value language fragments

This module exposes two dictionaries:

- REQUIRED_OUTPUT_FORMATS: mapping language_code -> required-output-format string
- GAMIFICATION_WRAPPERS: mapping language_code -> gamification wrapper string

These are simple key/value pairs as requested.
"""

# Note: keys should be lowercase language codes used across the app
REQUIRED_OUTPUT_FORMATS = {
    'english': '''REQUIRED OUTPUT FORMAT:
Return a JSON array like:
[
  {{
    "question_id": "q_abc123",
    "archetype": "Concept Unfold",
    "question_text": "In an RLC circuit at resonance, how do the current and voltage relate in phase? Explain simply.",
    "difficulty": "easy",
    "expected_answer": "At resonance, current and voltage are in phase."
  }},
  ...
]
''',

    'tanglish': '''REQUIRED OUTPUT FORMAT:
Return a JSON array like:
[
  {{
    "question_id": "q_abc123",
    "archetype": "Concept Unfold",
    "question_text": "RLC circuit la resonance nadakkum bodhu current-um voltage-um epadi phase la irukkum? Simple-a sollu.",
    "difficulty": "easy",
    "expected_answer": "Resonance la current and voltage in phase."
  }},
  ...
]
'''
}


GAMIFICATION_WRAPPERS = {
    'english': '''GAMIFICATION WRAPPERS (English) to optionally prepend:
- "Quick Round: Try this quickly."
- "Challenge: This one is tougher."
- "Explain: Put it in your own words."
- "Think: What would you try?"
''',

    'tanglish': '''GAMIFICATION WRAPPERS (Tanglish) to optionally prepend:
- "Quick Round: Konjam fast-a sollu."
- "Challenge: Ithu konjam kashtam."
- "Explain: Idhai unga mazhiya sollu."
- "Think: Ithu edhaana problem?"
'''
}
