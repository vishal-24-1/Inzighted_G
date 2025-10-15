# Dynamic Language Implementation

## Overview
This document describes the implementation of dynamic language support across the HelloTutor application. The system now supports unlimited languages based on the user's `preferred_language` field, moving away from hardcoded "Tanglish" references.

## Architecture

### Language Flow
```
User.preferred_language 
  → ChatSession.language 
  → TutorAgent.language 
  → Gemini Client Methods 
  → Prompt Functions 
  → AI Responses
```

## Modified Files

### 1. `api/tanglish_prompts.py`
**Purpose**: Centralized prompt templates for all LLM operations

**Changes**:
- Converted all prompt constants to functions accepting `language` parameter
- Made Tanglish-specific rules conditional (only included when `language == "tanglish"`)
- Added dynamic language insertion in prompts using f-strings

**Functions Updated**:
- `get_intent_classifier_system_prompt(language="tanglish")` - Intent classification
- `get_question_generator_system_prompt(language)` - Question generation system prompt
- `get_question_generator_instructions(language)` - Question generation instructions
- `get_answer_evaluator_system_prompt(language)` - Answer evaluation system prompt
- `get_answer_evaluator_instructions(language)` - Evaluation instructions with dynamic language
- `get_tanglish_style_rules(language)` - Tanglish-specific style rules (conditional)
- `build_question_generation_prompt(context, total_questions, language)` - Complete question prompt builder
- `build_evaluation_prompt(context, expected_answer, student_answer, language)` - Complete evaluation prompt builder

**Example**:
```python
def get_intent_classifier_system_prompt(language: str = "tanglish") -> str:
    """Returns intent classifier prompt with dynamic language."""
    return f"""You are an intent classifier for a {language}-speaking tutoring chatbot.
Your job is to classify the student's response into one of three categories:
...
"""
```

### 2. `api/gemini_client.py`
**Purpose**: Interface with Gemini API for all LLM operations

**Methods Updated**:
1. **`classify_intent(user_message, language="tanglish")`**
   - Accepts language parameter
   - Passes language to `get_intent_classifier_system_prompt()`

2. **`generate_questions_structured(context, total_questions=10, language="tanglish")`**
   - Accepts language parameter
   - Uses `build_question_generation_prompt()` with language
   - Logs language being used

3. **`evaluate_answer(context, expected_answer, student_answer, language="tanglish")`**
   - Accepts language parameter
   - Uses `build_evaluation_prompt()` with language
   - Logs evaluation language

4. **`generate_boostme_insights(qa_records, language="tanglish")`**
   - Accepts language parameter
   - Dynamically inserts language in system prompt
   - Passes language to fallback method

5. **`_generate_fallback_boostme_insights(qa_records, language="tanglish")`**
   - Accepts language parameter for future enhancement
   - Currently uses hardcoded Tanglish fallbacks (can be made dynamic later)

**Example**:
```python
def generate_questions_structured(self, context: str, total_questions: int = 10, language: str = "tanglish") -> list:
    """Generate structured questions using Gemini with dynamic language."""
    logger.info(f"Generating {total_questions} questions in {language}...")
    
    prompt = build_question_generation_prompt(
        context=context, 
        total_questions=total_questions,
        language=language
    )
    # ... rest of implementation
```

### 3. `api/agent_flow.py`
**Purpose**: Core tutoring state machine orchestrating the question flow

**Changes**:
1. **Added language property in `__init__`**:
   ```python
   def __init__(self, session: ChatSession):
       self.session = session
       self.user = session.user
       self.user_id = str(self.user.id)
       self.tenant_tag = get_tenant_tag(self.user_id)
       # Get language preference from user, fallback to session language, then 'tanglish'
       self.language = getattr(self.user, 'preferred_language', None) or self.session.language or 'tanglish'
   ```

2. **Updated all Gemini client method calls**:
   - `generate_questions_structured()` - Passes `language=self.language`
   - `classify_intent()` - Passes `language=self.language`
   - `evaluate_answer()` - Passes `language=self.language`
   - `generate_boostme_insights()` - Passes `language=self.language`

**Example**:
```python
# Generate questions with user's language preference
questions_data = gemini_client.generate_questions_structured(
    context, 
    total_questions=10, 
    language=self.language
)

# Classify intent with user's language
classifier_token = gemini_client.classify_intent(user_message, language=self.language)
```

### 4. `api/views/tutoring_views.py`
**Purpose**: API endpoint for starting tutoring sessions

**Changes**:
- Modified session creation to prioritize `user.preferred_language`
- Falls back to request data, then 'tanglish'

**Before**:
```python
language = request.data.get('language', 'tanglish')
```

**After**:
```python
language = getattr(request.user, 'preferred_language', None) or request.data.get('language', 'tanglish')
```

### 5. `api/views/chat_views.py`
**Purpose**: General chat session management

**Changes**:
- Updated `_get_or_create_session()` to use user's preferred language when creating new sessions

**Before**:
```python
return ChatSession.objects.create(user=user)
```

**After**:
```python
language = getattr(user, 'preferred_language', 'tanglish')
return ChatSession.objects.create(user=user, language=language)
```

## Usage

### Adding New Languages

To add support for a new language (e.g., "hindi"):

1. **Update User Model** (if not already done):
   ```python
   class User(AbstractUser):
       LANGUAGE_CHOICES = [
           ('english', 'English'),
           ('tanglish', 'Tanglish'),
           ('hindi', 'Hindi'),  # Add new language
       ]
       preferred_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='tanglish')
   ```

2. **Set User's Preference**:
   ```python
   user.preferred_language = 'hindi'
   user.save()
   ```

3. **The System Automatically**:
   - Uses the language in all prompts
   - Generates questions in that language
   - Evaluates answers in that language
   - Creates insights in that language

No code changes needed! The prompts will dynamically adjust:
```
"You are generating questions in hindi..."
"Evaluate the answer in hindi..."
"Language: hindi. Keep each point concise..."
```

### Language-Specific Rules

If a language needs special handling (like Tanglish's transliteration rules), add conditional logic in the prompt functions:

```python
def get_question_generator_instructions(language: str) -> str:
    base_instructions = f"""Generate questions in {language}..."""
    
    if language == "tanglish":
        base_instructions += "\n" + get_tanglish_style_rules(language)
    elif language == "hindi":
        base_instructions += "\n" + get_hindi_style_rules(language)
    
    return base_instructions
```

## Testing

### Test Dynamic Language Flow

1. **Set User Language**:
   ```python
   user = User.objects.get(username='test_user')
   user.preferred_language = 'english'
   user.save()
   ```

2. **Start Session**:
   ```bash
   POST /api/tutoring/start/
   {
     "document_id": "123"
   }
   ```

3. **Verify**:
   - Questions generated in English
   - Intent classification considers English responses
   - Evaluations in English
   - Insights in English

### Test Different Languages

```python
# Test with Tanglish
user.preferred_language = 'tanglish'
# Start session → Questions in Tanglish with transliteration rules

# Test with English
user.preferred_language = 'english'
# Start session → Questions in pure English without Tanglish rules

# Test with custom language
user.preferred_language = 'spanish'
# Start session → Questions attempt Spanish (quality depends on LLM capability)
```

## Benefits

1. **Scalability**: Support unlimited languages without code changes
2. **User-Centric**: Respects user's language preference automatically
3. **Maintainability**: Single source of truth for language preference
4. **Flexibility**: Easy to add language-specific rules when needed
5. **Backward Compatibility**: Defaults to 'tanglish' for existing users

## Default Behavior

If language is not set at any level:
- User.preferred_language → None
- Request data → None
- Session.language → 'tanglish' (default)
- Agent.language → 'tanglish'

## Notes

- All default parameters are set to `"tanglish"` for backward compatibility
- Language preference flows: User → Session → Agent → Prompts
- Fallback insights in `_generate_fallback_boostme_insights` still use hardcoded Tanglish (can be enhanced later)
- LLM quality may vary for languages it wasn't trained extensively on

## Future Enhancements

1. **Validate Language**: Add language validation at the User model level
2. **Translation Layer**: Add automatic translation for unsupported languages
3. **Language-Specific Prompts**: Create separate prompt templates for major languages
4. **Fallback Insights**: Make fallback insights language-aware
5. **Language Detection**: Auto-detect user's language from responses
