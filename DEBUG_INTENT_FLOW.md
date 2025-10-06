# Debug Guide: Intent Classification & Answer Generation Flow

## What I Added

Added detailed logging throughout the intent classification and response generation flow to help diagnose why answers aren't appearing.

## Logging Points Added

### 1. Agent Flow (`backend/api/agent_flow.py`)

**handle_user_message():**
```
[AGENT] ========== HANDLING USER MESSAGE ==========
[AGENT] Session: {session_id}
[AGENT] User message: {first 100 chars}
[AGENT] Calling intent classifier...
[AGENT] ✅ Intent classified as: {DIRECT_ANSWER/MIXED/RETURN_QUESTION}
[AGENT] Branching to handler for intent: {intent}
[AGENT] → Calling _handle_{intent_type}
```

**_handle_return_question():**
```
[AGENT] === RETURN_QUESTION Flow ===
[AGENT] User asked: {first 80 chars}
[AGENT] Calling RAG to answer user's question...
[AGENT] RAG reply length: {X} chars
[AGENT] RAG reply preview: {first 150 chars}
[AGENT] ✅ Returning reply + next question
```

**_answer_user_question_with_rag():**
```
[RAG] Answering user question using RAG: {first 50 chars}
[RAG] Raw response length: {X} chars, preview: {first 100 chars}
[RAG] Response too long ({X} chars), summarizing in Tanglish...
[RAG] Tanglish summary: {first 100 chars}
[RAG] Detected prompting language in RAG output — forcing rewrite into direct answer
[RAG] Rewrote prompting output into direct answer: {first 120 chars}
[RAG] Returning final response to user
```

### 2. Views Layer (`backend/api/views.py`)

**TutoringSessionAnswerView:**
```
[VIEW] Agent result keys: {dict_keys}
[VIEW] reply present: {True/False}
[VIEW] reply length: {X}
[VIEW] next_question present: {True/False}
[VIEW] evaluation present: {True/False}
[VIEW] session_complete: {True/False}
[VIEW] ✅ Adding feedback to response
[VIEW] Feedback text length: {X}
[VIEW] ⚠️ No reply from agent, feedback not added
[VIEW] ✅ Adding next_question to response
[VIEW] ========== FINAL RESPONSE ==========
[VIEW] Response keys: {dict_keys}
[VIEW] Has feedback: {True/False}
[VIEW] Has next_question: {True/False}
[VIEW] Has evaluation: {True/False}
```

## How to Debug Your Issue

### Step 1: Restart Django Server
```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor\backend
# Stop current server (Ctrl+C)
python manage.py runserver
```

### Step 2: Test a Question
1. Start a tutoring session
2. Type a question: **"what is question scoring?"**
3. Watch the console where `runserver` is running

### Step 3: Read the Logs

You should see output like this:

```
[AGENT] ========== HANDLING USER MESSAGE ==========
[AGENT] Session: abc-123-...
[AGENT] User message: what is question scoring?
[AGENT] Calling intent classifier...
```

**Check Point 1: Intent Classification**
```
[AGENT] ✅ Intent classified as: RETURN_QUESTION
```

✅ **If you see `RETURN_QUESTION`** - Intent classification is working correctly!
❌ **If you see `DIRECT_ANSWER`** - Intent classifier is wrong! The question contains "what is" but was misclassified.

**Check Point 2: Handler Branch**
```
[AGENT] Branching to handler for intent: RETURN_QUESTION
[AGENT] → Calling _handle_return_question
```

✅ Should route to `_handle_return_question` for questions

**Check Point 3: RAG Call**
```
[AGENT] === RETURN_QUESTION Flow ===
[AGENT] User asked: what is question scoring?
[AGENT] Calling RAG to answer user's question...
[RAG] Answering user question using RAG: what is question scoring?
[RAG] Raw response length: 234 chars, preview: Question scoring refers to the evaluation...
```

✅ **If you see RAG output** - RAG is working and returning content
❌ **If RAG output is empty or error** - RAG failed to retrieve documents

**Check Point 4: Prompting Detection & Rewrite**
```
[RAG] Detected prompting language in RAG output — forcing rewrite into direct answer
[RAG] Rewrote prompting output into direct answer: Question scoring na evaluation...
```

✅ If original RAG output had prompting language (like "try to", "can you"), this should trigger

**Check Point 5: Return to Agent**
```
[AGENT] RAG reply length: 187 chars
[AGENT] RAG reply preview: Question scoring na evaluation process...
[AGENT] ✅ Returning reply + next question
```

✅ Agent should have non-empty reply ready to return

**Check Point 6: View Layer Processing**
```
[VIEW] Agent result keys: dict_keys(['reply', 'next_question', 'next_question_item', 'session_complete', 'evaluation'])
[VIEW] reply present: True
[VIEW] reply length: 187
[VIEW] next_question present: True
[VIEW] evaluation present: False
[VIEW] session_complete: False
```

✅ **If `reply present: True`** - Agent successfully returned a reply!
❌ **If `reply present: False`** - Agent handler didn't return reply (logic bug)

**Check Point 7: Response Building**
```
[VIEW] ✅ Adding feedback to response
[VIEW] Feedback text length: 187
[VIEW] ✅ Adding next_question to response
```

✅ View should add feedback to response_data

**Check Point 8: Final Response**
```
[VIEW] ========== FINAL RESPONSE ==========
[VIEW] Response keys: dict_keys(['session_id', 'response_time_ms', 'feedback', 'next_question', 'evaluation'])
[VIEW] Has feedback: True
[VIEW] Has next_question: True
[VIEW] Has evaluation: False
```

✅ **If `Has feedback: True`** - Response contains the answer!
❌ **If `Has feedback: False`** - Something went wrong between agent and view

## Common Issues & Solutions

### Issue 1: Intent Misclassified as DIRECT_ANSWER
**Symptom:** `[AGENT] ✅ Intent classified as: DIRECT_ANSWER` for a question

**Cause:** Gemini classifier or fallback heuristic failed

**Solution:** Check `backend/api/tanglish_prompts.py` fallback_intent_classifier - make sure question words like "what", "?" are detected

### Issue 2: RAG Returns Empty or Prompting Text
**Symptom:** `[RAG] Raw response length: 0` or prompting language detected

**Cause:** 
- No documents in Pinecone for user
- RAG returning generic prompts instead of answers

**Solution:** 
- Verify document is uploaded and processed
- Check Pinecone stats: user has vectors in their namespace
- Rewrite logic (already added) should convert prompts to answers

### Issue 3: Agent Returns reply=None
**Symptom:** `[VIEW] reply present: False`

**Cause:** Agent handler returned `{"reply": None, ...}`

**Solution:** Check which handler was called:
- `_handle_direct_answer` → Should return `reply: None` (this is correct!)
- `_handle_mixed` → Should return `reply: {RAG answer}` (must not be None)
- `_handle_return_question` → Should return `reply: {RAG answer}` (must not be None)

### Issue 4: Frontend Not Showing Feedback
**Symptom:** API returns feedback but UI doesn't show it

**Cause:** Frontend not appending feedback to messages

**Solution:** Already fixed in `frontend/src/pages/TutoringChat.tsx` - restart frontend dev server

## Quick Test Cases

### Test 1: Pure Question (RETURN_QUESTION)
**Input:** "what is question scoring?"
**Expected Intent:** RETURN_QUESTION
**Expected Output:** Explanation appears + next question

### Test 2: Direct Answer (DIRECT_ANSWER)
**Input:** "correct"
**Expected Intent:** DIRECT_ANSWER
**Expected Output:** NO explanation, just next question (evaluation shown separately)

### Test 3: Mixed (MIXED)
**Input:** "correct, but what is electric field?"
**Expected Intent:** MIXED
**Expected Output:** Explanation about electric field + next question

## Next Steps

1. **Run the test** - Type "what is question scoring?" in your tutoring session
2. **Copy the console output** - All the `[AGENT]`, `[RAG]`, and `[VIEW]` logs
3. **Send me the logs** - I'll analyze exactly where the flow breaks
4. **Check network tab** - Look at the API response in browser DevTools to confirm if `feedback` is present

The logs will tell us exactly which checkpoint is failing!
