# Tanglish Agent Implementation

## Overview

This implementation adds a new Tanglish tutoring agent flow to the existing HelloTutor platform **without affecting existing functionality**. The agent follows the exact specification provided:

- Intent classification (DIRECT_ANSWER, MIXED, RETURN_QUESTION)
- Structured question generation with archetypes
- Answer evaluation with XP and Tanglish feedback
- SWOT insights generation after session completion

## Architecture

### New Components

1. **Models** (`api/models.py` - extended):
   - `QuestionItem` - Individual questions with archetype, difficulty, XP metadata
   - `EvaluatorResult` - Answer evaluation results with score, XP, Tanglish feedback
   - Extended `ChatSession` with `language` field (tanglish/english)
   - Extended `ChatMessage` with `classifier_token` field

2. **Prompts** (`api/tanglish_prompts.py` - new):
   - Exact system prompts from specification
   - Intent classifier with fallback rules
   - Question generator instructions
   - Answer evaluator instructions
   - Insights generator instructions

3. **Gemini Client** (`api/gemini_client.py` - extended):
   - `classify_intent()` - Returns DIRECT_ANSWER/MIXED/RETURN_QUESTION
   - `generate_questions_structured()` - Returns list of question dicts with archetypes
   - `evaluate_answer()` - Returns evaluation dict with score, XP, Tanglish feedback
   - `generate_insights()` - Returns SWOT analysis dict

4. **Agent Flow** (`api/agent_flow.py` - new):
   - `TutorAgent` class - Core state machine
   - Implements exact flow from spec § 1
   - Handles all three intent branches
   - Manages question queue and evaluation
   - Generates insights on session completion

5. **API Views** (`api/views/agent_views.py` - new):
   - `POST /api/agent/session/start/` - Start new Tanglish session
   - `POST /api/agent/session/<id>/respond/` - Submit answer/question
   - `GET /api/agent/session/<id>/status/` - Get session progress
   - `POST /api/agent/session/<id>/language/` - Toggle language

## Database Migrations

After pulling this code, run migrations:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

## Configuration

Add to your `.env` file:

```env
GEMINI_MODEL=gemini-2.0-flash-exp
```

(Already configured in existing LLM_API_KEY and EMBEDDING_API_KEY)

## API Usage

### 1. Start Agent Session

```http
POST /api/agent/session/start/
Authorization: Bearer <token>
Content-Type: application/json

{
  "document_id": "uuid-of-uploaded-document",
  "language": "tanglish"
}
```

Response:
```json
{
  "session_id": "uuid",
  "first_question": {
    "text": "RLC circuit la resonance nadakkum bodhu current-um voltage-um epadi phase la irukkum? Simple-a sollu.",
    "question_id": "q_abc123",
    "archetype": "Concept Unfold",
    "difficulty": "easy",
    "message_id": "uuid"
  },
  "language": "tanglish"
}
```

### 2. Submit Answer/Question

```http
POST /api/agent/session/<session_id>/respond/
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Resonance la current and voltage in phase irukkum."
}
```

Response:
```json
{
  "session_id": "uuid",
  "session_complete": false,
  "reply": {
    "text": "Correct! Well done.",
    "message_id": "uuid"
  },
  "next_question": {
    "text": "Next question text...",
    "question_id": "q_def456",
    "archetype": "Application Sprint",
    "difficulty": "medium",
    "message_id": "uuid"
  },
  "evaluation": {
    "score": 0.95,
    "xp": 85,
    "correct": true,
    "explanation": "Perfect understanding! Current-um voltage-um same phase la irukkum resonance bodhu.",
    "confidence": 0.9,
    "followup_action": "none"
  },
  "response_time_ms": 1250
}
```

### 3. Check Session Status

```http
GET /api/agent/session/<session_id>/status/
Authorization: Bearer <token>
```

Response:
```json
{
  "session_id": "uuid",
  "language": "tanglish",
  "total_questions": 10,
  "current_question_index": 3,
  "questions_answered": 3,
  "total_xp": 245,
  "is_complete": false,
  "is_active": true
}
```

### 4. Toggle Language

```http
POST /api/agent/session/<session_id>/language/
Authorization: Bearer <token>
Content-Type: application/json

{
  "language": "english"
}
```

## Specification Compliance

### § 1 — High-level Flow ✅

- [x] Agent pulls next question from queue
- [x] Delivers question in Tanglish style
- [x] Waits for user reply
- [x] Classifies intent using Gemini
- [x] Branches on DIRECT_ANSWER / MIXED / RETURN_QUESTION
- [x] Runs evaluator for answers
- [x] Stores QA pairs and evaluations
- [x] Advances question queue
- [x] Generates insights after completion

### § 2 — Intent Classifier ✅

- [x] Exact system prompt from spec
- [x] Returns single token: DIRECT_ANSWER / MIXED / RETURN_QUESTION
- [x] Handles Tanglish and English
- [x] Fallback deterministic rule on API failure
- [x] Logs failures to Sentry

### § 3 — Question Generator ✅

- [x] Exact system prompt from spec
- [x] Generates 10 questions per session
- [x] Uses only provided context
- [x] Returns JSON with all required fields
- [x] Includes 7 archetypes
- [x] Tanglish phrasing with short sentences
- [x] Difficulty levels (easy/medium/hard)

### § 4 — Answer Evaluator ✅

- [x] Exact system prompt from spec
- [x] Returns JSON with all required keys
- [x] Score in [0.0, 1.0] with partial credit
- [x] XP calculation (1-100 based on score)
- [x] Tanglish explanation (<30 words)
- [x] Confidence float
- [x] Follow-up actions
- [x] return_question_answer hint

### § 5 — Insights Generator ✅

- [x] Generates SWOT analysis
- [x] Uses stored QA pairs and evaluations
- [x] Tanglish style output
- [x] Triggered after session completion

### § 0 — Tanglish Style ✅

- [x] Warm, human, slightly academic tone
- [x] Short sentences (<20 words)
- [x] Natural Tamil words in Latin script
- [x] Technical words in English
- [x] Language toggle support

## Backward Compatibility

This implementation:

- **Does NOT modify** existing tutoring session endpoints
- **Does NOT change** existing `TutoringSessionStartView`, `TutoringSessionAnswerView`
- **Only adds** new fields to existing models (all nullable/optional)
- **Uses separate** URL namespace (`/api/agent/...`)
- **Reuses** existing infrastructure (Gemini client, Pinecone, S3)

### Existing Functionality Preserved

- Document upload and ingestion still works
- RAG query/chat still works
- Old tutoring flow still works
- Insights generation still works
- All existing API endpoints unchanged

## Testing

### Manual Testing

1. Upload a document via existing endpoint
2. Wait for processing to complete
3. Start agent session with document ID
4. Submit answers and questions
5. Check session status
6. Complete all questions
7. Verify insights generation

### Unit Tests (TODO)

Create tests in `backend/api/tests/test_agent_flow.py`:

- Intent classifier fallback rules
- Question JSON parsing with malformed responses
- Evaluator XP calculation
- Agent branching logic for each intent type
- Session completion and insights trigger

## Monitoring

All operations log to Sentry with context:

- Intent classification failures
- Question generation errors
- Answer evaluation errors
- Insights generation failures

## Future Enhancements

1. **Question Scoring Formula** - Implement compute_question_score() for resequencing
2. **Language Translation** - Add actual Tanglish ↔ English translation
3. **Gamification Wrappers** - Prepend motivational phrases to questions
4. **Advanced Clarification** - Use RAG for RETURN_QUESTION responses
5. **Analytics Dashboard** - Track XP, archetype performance, session completion rates

## Files Modified

- `backend/api/models.py` - Added QuestionItem, EvaluatorResult; extended ChatSession, ChatMessage
- `backend/api/gemini_client.py` - Added 4 new methods
- `backend/api/urls.py` - Added 4 new endpoints
- `.env.example` - Added GEMINI_MODEL

## Files Created

- `backend/api/tanglish_prompts.py` - All system prompts and helpers
- `backend/api/agent_flow.py` - TutorAgent state machine
- `backend/api/views/agent_views.py` - API views
- `backend/api/views/__init__.py` - Package exports
- `TANGLISH_AGENT_IMPLEMENTATION.md` - This file

## Deployment Checklist

- [ ] Run migrations
- [ ] Set GEMINI_MODEL in production .env
- [ ] Test with sample document
- [ ] Monitor Sentry for first 24 hours
- [ ] Verify XP calculation
- [ ] Check insights generation

## Support

For issues or questions, check:

1. Sentry logs for error details
2. Django logs for flow execution
3. Database for QuestionItem and EvaluatorResult records
4. This README for API usage examples
