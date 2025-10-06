# Quick Fix: Print Statements for Debugging

## What I Changed

Replaced all `logger.info()` calls with `print()` statements so output shows in the console immediately (Django logging wasn't configured).

## Files Modified

1. **`backend/api/agent_flow.py`**
   - Changed `logger.info()` → `print()` in `handle_user_message()` and `_handle_return_question()`
   - Added visual separators with `===` lines

2. **`backend/api/views.py`**
   - Changed `logger.info()` → `print()` in `TutoringSessionAnswerView`
   - Added visual separators

## Now Restart and Test

**Step 1: Restart Django Server**
```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor\backend
# Stop current server (Ctrl+C)
python manage.py runserver
```

**Step 2: Test with a Question**
1. Go to your tutoring session
2. Type: **"what is question scoring?"**
3. Submit

**Step 3: Check the Console**

You should now see clear output like this in your terminal:

```
============================================================
[AGENT] HANDLING USER MESSAGE
[AGENT] Session: 985e0702-f12b-4297-8435-b02abc4c11ba
[AGENT] User message: what is question scoring?
============================================================

[AGENT] Calling intent classifier...
[AGENT] ✅ Intent classified as: RETURN_QUESTION

[AGENT] Branching to handler for intent: RETURN_QUESTION
[AGENT] → Calling _handle_return_question

[AGENT] === RETURN_QUESTION Flow ===
[AGENT] User asked: what is question scoring?...
[AGENT] Calling RAG to answer user's question...
[AGENT] RAG reply length: 234 chars
[AGENT] RAG reply preview: Question scoring refers to the evaluation process where...
[AGENT] ✅ Returning reply + next question

[VIEW] Agent result keys: ['reply', 'next_question', 'next_question_item', 'session_complete', 'evaluation']
[VIEW] reply present: True
[VIEW] reply length: 234
[VIEW] reply preview: Question scoring refers to...
[VIEW] next_question present: True
[VIEW] evaluation present: False
[VIEW] session_complete: False

[VIEW] ✅ Adding feedback to response
[VIEW] Feedback text length: 234
[VIEW] ✅ Adding next_question to response

[VIEW] ========== FINAL RESPONSE ==========
[VIEW] Response keys: ['session_id', 'response_time_ms', 'feedback', 'next_question', 'evaluation']
[VIEW] Has feedback: True
[VIEW] Has next_question: True
[VIEW] Has evaluation: False
=============================================

[06/Oct/2025 15:45:30] "POST /api/tutoring/985e0702-f12b-4297-8435-b02abc4c11ba/answer/ HTTP/1.1" 200 450
```

## What to Look For

**✅ If you see all the above logs:**
- Intent is being classified correctly
- RAG is returning an answer
- Reply is being added to response
- `Has feedback: True` in final response
- **The issue is in the frontend** (not updating UI) or **server needs restart**

**❌ If logs don't appear at all:**
- Code changes not loaded → **Restart server**

**❌ If `Intent classified as: DIRECT_ANSWER` (wrong!):**
- Gemini classifier or fallback is broken
- Need to check intent classification logic

**❌ If `RAG reply length: 0`:**
- RAG failed to retrieve documents
- No content in Pinecone for this user
- Need to check document ingestion

**❌ If `Has feedback: False`:**
- Reply not being added to response (view layer bug)
- Need to check response building logic

## After You See the Logs

Send me the complete console output and I'll diagnose the exact issue!
