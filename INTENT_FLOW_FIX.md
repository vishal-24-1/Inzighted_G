# Intent Classification Flow - Fix Applied

## Issue Reported

When users asked questions (like "what is chunker?", "what is pinecone?", "tanglish means?"), the system was:
- ❌ Classifying intent correctly as `RETURN_QUESTION`
- ❌ But then just **re-asking the same question** without answering the user's question
- ❌ Not moving to the next question in the queue

## Required Behavior (As Per Spec)

**Intent Classification Flow:**

1. **DIRECT_ANSWER** (user gives an answer)
   - Evaluate the answer with XP and score
   - Move to next question

2. **MIXED** (user gives answer + asks a question)
   - Answer user's follow-up question using RAG
   - Evaluate the answer part
   - Move to next question

3. **RETURN_QUESTION** (user asks a question / needs clarification)
   - Answer user's question using RAG
   - **Move to next question** (don't re-ask same question)

## Fix Applied

### File: `backend/api/agent_flow.py`

#### 1. Updated `_handle_return_question()` method

**Before:**
```python
def _handle_return_question(...):
    # Answer the user's question
    clarification_reply = self._generate_simple_clarification(user_message)
    
    # Resume with current question (don't advance)  ❌ WRONG
    return {
        "reply": clarification_reply,
        "next_question": question_item.question_text,  # Re-ask same question
        "next_question_item": question_item,
        "session_complete": False,
        "evaluation": None
    }
```

**After:**
```python
def _handle_return_question(...):
    """
    Handle RETURN_QUESTION flow
    User asked a question - answer it then move to next question
    """
    # Answer the user's question using RAG
    clarification_reply = self._answer_user_question_with_rag(user_message)
    
    # Move to next question (as per requirement) ✅ FIXED
    has_more = self.advance_to_next_question()
    
    if has_more:
        next_q_text, next_q_item = self.get_next_question()
        return {
            "reply": clarification_reply,
            "next_question": next_q_text,  # Next question, not same
            "next_question_item": next_q_item,
            "session_complete": False,
            "evaluation": None
        }
    else:
        self._generate_session_insights()
        return {
            "reply": clarification_reply + "\n\nGreat job! You've completed all questions. 🎉",
            "next_question": None,
            "session_complete": True,
            "evaluation": None
        }
```

#### 2. Renamed helper method for clarity

**Before:** `_generate_simple_clarification()`  
**After:** `_answer_user_question_with_rag()`

This method:
- Uses RAG (`query_rag()`) to answer user's question using document context
- Summarizes long responses in Tanglish (sentences <20 words)
- Returns concise, helpful answer

#### 3. Updated `_handle_mixed()` to use renamed method

Both `MIXED` and `RETURN_QUESTION` now use the same RAG-based question answering.

## Testing the Fix

### Test Case 1: User asks "what is chunker?"

**Request:**
```json
POST /api/tutoring/{session_id}/answer/
{
  "text": "what is chunker?"
}
```

**Expected Response:**
```json
{
  "feedback": {
    "text": "Chunker is a process that splits large text into smaller pieces for better processing. Inga document-a small chunks-a divide pannuradhu.\n\nNow, let's continue with the question."
  },
  "next_question": {
    "text": "Next question about your document topic..."
  }
}
```

✅ User's question is answered  
✅ Moves to next question  
❌ No evaluation (since user didn't provide an answer)

### Test Case 2: User provides answer

**Request:**
```json
POST /api/tutoring/{session_id}/answer/
{
  "text": "Pinecone database-la document vectors store pannuradhu"
}
```

**Expected Response:**
```json
{
  "evaluation": {
    "score": 0.85,
    "xp": 75,
    "correct": true,
    "explanation": "Correct! Pinecone la vectors store pannurom. Good understanding."
  },
  "next_question": {
    "text": "Next question..."
  }
}
```

✅ Answer is evaluated  
✅ XP awarded  
✅ Moves to next question

### Test Case 3: User provides answer + asks question (MIXED)

**Request:**
```json
POST /api/tutoring/{session_id}/answer/
{
  "text": "TWA Android app-a wrap pannadhu. But what is assetlinks.json?"
}
```

**Expected Response:**
```json
{
  "feedback": {
    "text": "assetlinks.json file Android app-ku website-oda connection verify pannum. TWA ku romba important.\n\nNow, let's continue with the question."
  },
  "evaluation": {
    "score": 0.90,
    "xp": 85,
    "correct": true,
    "explanation": "Perfect! TWA Android app wrap pannuradhu correct."
  },
  "next_question": {
    "text": "Next question..."
  }
}
```

✅ Follow-up question answered  
✅ Answer part evaluated  
✅ Moves to next question

## Flow Summary

```
User Input
    ↓
[Gemini Intent Classifier]
    ↓
┌─────────────┬──────────────┬─────────────────┐
│ DIRECT_     │   MIXED      │ RETURN_         │
│ ANSWER      │              │ QUESTION        │
└─────────────┴──────────────┴─────────────────┘
    ↓               ↓                ↓
Evaluate        Answer Q         Answer Q
Answer          +                using RAG
using Gemini    Evaluate            ↓
    ↓           Answer          Move to Next
Move to Next       ↓            Question
Question       Move to Next
               Question
```

## Files Changed

- ✅ `backend/api/agent_flow.py` - Updated `_handle_return_question()` and `_handle_mixed()`
- ✅ Method renamed: `_generate_simple_clarification()` → `_answer_user_question_with_rag()`

## Backward Compatibility

✅ No API changes - same endpoints work  
✅ Same response format  
✅ Old behavior upgraded automatically  
✅ Existing frontend code continues to work

## Verification

Restart the server and test:

```powershell
# The server should already be running, just test the endpoints
# Start a tutoring session
# Submit "what is chunker?" and verify you get an answer + next question
```

Check logs for:
- `Intent classified as: RETURN_QUESTION`
- `Answering user question using RAG: what is chunker?...`
- `Advanced to question X/10`

---

**Status**: ✅ Fixed and ready for testing  
**Date**: October 6, 2025
