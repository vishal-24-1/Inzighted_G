# Intent Classification Fix - UPDATED

## Problem Identified ✅

The intent classifier was **incorrectly classifying questions as DIRECT_ANSWER**:

**Example:**
```
User: "what is context chunking means?"
Classified as: DIRECT_ANSWER ❌ (WRONG!)
Should be: RETURN_QUESTION ✅
```

**Console output showed:**
```
[AGENT] User message: what is context chunking means?...
[AGENT] ✅ Intent classified as: DIRECT_ANSWER  ← WRONG!
[AGENT] → Calling _handle_direct_answer
[VIEW] reply present: False                    ← No RAG called!
[VIEW] ⚠️ No reply from agent
[VIEW] Has feedback: False                     ← No explanation shown!
```

This caused the system to:
1. Call `_handle_direct_answer()` instead of `_handle_return_question()`
2. Skip RAG (no explanation generated)
3. Return `reply: None` (no feedback shown to user)

## Root Causes

1. **Gemini classifier prompt was too vague** - didn't explicitly mention question word detection
2. **Fallback classifier was too simplistic** - missing common question patterns like "means", "is", "are"

## Fixes Applied

### 1. Improved Gemini System Prompt

**Before (vague):**
```python
INTENT_CLASSIFIER_SYSTEM_PROMPT = """You are a short intent classifier. Input: USER_MESSAGE. Return one token: DIRECT_ANSWER, MIXED, or RETURN_QUESTION. 
Handle Tanglish or English. Do not explain."""
```

**After (explicit rules):**
```python
INTENT_CLASSIFIER_SYSTEM_PROMPT = """You are a short intent classifier. Input: USER_MESSAGE. Return ONLY one token: DIRECT_ANSWER, MIXED, or RETURN_QUESTION.

Rules:
- If USER_MESSAGE contains question words (what, why, how, when, where, who, which) or ends with '?', classify as RETURN_QUESTION or MIXED
- If USER_MESSAGE is answering the tutoring question directly (like "correct", "yes", "no", a number, or explanation), classify as DIRECT_ANSWER
- If USER_MESSAGE contains BOTH an answer AND a question, classify as MIXED
- Handle Tanglish or English. Do not explain. Return ONLY the token."""
```

### 2. Enhanced Fallback Classifier

**Added features:**
- ✅ Check if message **starts with** question word (strong indicator)
- ✅ Expanded question markers: `'means', 'mean', 'meaning', 'is', 'are', 'can', 'could', 'do', 'does'`
- ✅ Added Tanglish markers: `'na', 'nu'`
- ✅ Prioritize `?` and question-word-at-start patterns
- ✅ Debug print statements to trace classification logic

**Logic flow:**
```python
if starts_with_question_word OR contains '?':
    → RETURN_QUESTION (or MIXED if very long)
elif has_question_markers:
    → RETURN_QUESTION (or MIXED if long)
else:
    → DIRECT_ANSWER
```

### 3. Added Debug Output

**In `gemini_client.py` - `classify_intent()`:**
```python
print(f"[CLASSIFIER] Prompt: {prompt[:200]}...")
print(f"[CLASSIFIER] Gemini raw response: '{response}'")
print(f"[CLASSIFIER] Parsed token: '{token}'")
print(f"[CLASSIFIER] ✅ Valid token: {token}")
```

**In `tanglish_prompts.py` - `fallback_intent_classifier()`:**
```python
print(f"[FALLBACK] Classifying: '{user_message}'")
print(f"[FALLBACK] starts_with_question: {starts_with_question}, has_question: {has_question}")
print(f"[FALLBACK] → RETURN_QUESTION (clear question)")
```

## Testing

**Restart Django server:**
```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor\backend
python manage.py runserver
```

**Test cases:**

### Test 1: Simple Question
```
Input: "what is context chunking means?"
Expected: RETURN_QUESTION
Should show: RAG explanation + next question
```

### Test 2: Question with "?"
```
Input: "what is question scoring?"
Expected: RETURN_QUESTION
Should show: RAG explanation + next question
```

### Test 3: Direct Answer
```
Input: "correct"
Expected: DIRECT_ANSWER
Should show: NO explanation, just next question
```

### Test 4: Mixed
```
Input: "correct, but what is electric field?"
Expected: MIXED
Should show: RAG explanation + next question
```

## Expected Console Output

Now when you test "what is context chunking means?", you should see:

```
============================================================
[AGENT] HANDLING USER MESSAGE
[AGENT] User message: what is context chunking means?...
============================================================

[AGENT] Calling intent classifier...
[CLASSIFIER] Prompt: You are a short intent classifier...
[CLASSIFIER] Gemini raw response: 'RETURN_QUESTION'
[CLASSIFIER] Parsed token: 'RETURN_QUESTION'
[CLASSIFIER] ✅ Valid token: RETURN_QUESTION
[AGENT] ✅ Intent classified as: RETURN_QUESTION

[AGENT] → Calling _handle_return_question

[AGENT] === RETURN_QUESTION Flow ===
[AGENT] Calling RAG to answer user's question...
[AGENT] RAG reply length: 234 chars
[AGENT] ✅ Returning reply + next question

[VIEW] reply present: True                    ← Should be True now!
[VIEW] ✅ Adding feedback to response
[VIEW] Has feedback: True                     ← Should be True now!
```

## Files Modified

1. **`backend/api/gemini_client.py`**
   - Added debug prints in `classify_intent()`
   - Shows Gemini's raw response and parsed token

2. **`backend/api/tanglish_prompts.py`**
   - Updated `INTENT_CLASSIFIER_SYSTEM_PROMPT` with explicit rules
   - Enhanced `fallback_intent_classifier()` with better question detection
   - Added debug prints to trace fallback logic

## Verification Checklist

After restart, verify:
- [ ] "what is X?" → classified as RETURN_QUESTION
- [ ] "what is X means?" → classified as RETURN_QUESTION
- [ ] "correct" → classified as DIRECT_ANSWER
- [ ] Questions show RAG explanation immediately
- [ ] Direct answers show NO explanation (only evaluation)

If Gemini still returns wrong classification, the enhanced fallback will catch it!

## Issue
When users asked clarifying questions (like "what is chunker?"), the system:
- ✅ Correctly classified the intent as `RETURN_QUESTION`
- ❌ But only returned a generic response
- ❌ And just re-asked the same question without actually answering

## Root Cause
The `_generate_simple_clarification()` method in `agent_flow.py` was returning hardcoded generic messages instead of using RAG to actually answer the user's question.

## Solution Implemented

### 1. Enhanced `_generate_simple_clarification()` Method

**Before:**
```python
def _generate_simple_clarification(self, user_message: str) -> str:
    if '?' in user_message:
        return "Good question! Let me help: focus on the key concepts..."
    else:
        return "I see. Let's continue..."
```

**After:**
```python
def _generate_simple_clarification(self, user_message: str) -> str:
    # Use RAG to answer the user's question from document context
    rag_response = query_rag(self.user_id, user_message)
    
    # If response is too long, summarize in Tanglish
    if len(rag_response) > 200:
        summary_prompt = "Summarize this in Tanglish (short sentences <20 words)..."
        rag_response = gemini_client.generate_response(summary_prompt, max_tokens=150)
    
    # Add encouragement to continue
    return f"{rag_response}\n\nNow, let's continue with the question."
```

### 2. Improved MIXED Flow Handler

Also updated `_handle_mixed()` to better handle messages that contain both an answer and a question.

## How It Works Now

### Flow for RETURN_QUESTION Intent

```
User asks: "what is chunker?"
    ↓
Intent Classifier → RETURN_QUESTION
    ↓
_handle_return_question()
    ↓
_generate_simple_clarification() → Uses RAG to answer from document
    ↓
Returns: {
    "reply": "Chunker is a process that breaks documents into smaller pieces 
              for better processing. Now, let's continue with the question.",
    "next_question": <same question re-asked>,
    "evaluation": null  (no evaluation for clarification questions)
}
```

### Flow for MIXED Intent

```
User says: "The answer is X, but what does Y mean?"
    ↓
Intent Classifier → MIXED
    ↓
_handle_mixed()
    ↓
1. Uses RAG to answer the follow-up question ("what does Y mean?")
2. Evaluates the answer portion ("The answer is X")
3. Advances to next question
    ↓
Returns: {
    "reply": <RAG-powered answer to "what does Y mean?">,
    "next_question": <next question in queue>,
    "evaluation": {score, xp, explanation...}
}
```

### Flow for DIRECT_ANSWER Intent

```
User says: "The answer is X"
    ↓
Intent Classifier → DIRECT_ANSWER
    ↓
_handle_direct_answer()
    ↓
1. Evaluates the answer
2. Provides Tanglish feedback if needed
3. Advances to next question
    ↓
Returns: {
    "reply": <optional feedback from evaluator>,
    "next_question": <next question in queue>,
    "evaluation": {score, xp, explanation...}
}
```

## Testing

### Test Case 1: User Asks Clarifying Question

**User Input:** "what is chunker?"

**Expected Behavior:**
1. ✅ Intent classified as `RETURN_QUESTION`
2. ✅ System uses RAG to retrieve information about "chunker" from the document
3. ✅ Response is summarized in Tanglish if too long
4. ✅ Same question is re-asked after clarification
5. ✅ No evaluation is performed (since user didn't answer)

**Log Output:**
```
Intent classified as: RETURN_QUESTION
Handling RETURN_QUESTION flow
Answering user question using RAG: what is chunker?...
```

### Test Case 2: User Provides Answer and Asks Question

**User Input:** "Chunker breaks documents into pieces, but what is hallucination rate?"

**Expected Behavior:**
1. ✅ Intent classified as `MIXED`
2. ✅ System evaluates "Chunker breaks documents into pieces" as answer
3. ✅ System uses RAG to answer "what is hallucination rate?"
4. ✅ Both evaluation and clarification are returned
5. ✅ Advances to next question

### Test Case 3: User Provides Direct Answer

**User Input:** "Chunker worker is used to process document chunks"

**Expected Behavior:**
1. ✅ Intent classified as `DIRECT_ANSWER`
2. ✅ System evaluates the answer
3. ✅ Returns score, XP, and Tanglish explanation
4. ✅ Advances to next question

## Files Modified

- `backend/api/agent_flow.py`
  - Enhanced `_generate_simple_clarification()` to use RAG
  - Improved `_handle_mixed()` flow
  - Added better error handling and logging

## Benefits

1. **Better User Experience**
   - Users get actual answers to their clarifying questions
   - Answers are based on their uploaded document content
   - Responses are in Tanglish style (short, clear sentences)

2. **Smarter Interactions**
   - System doesn't just repeat questions
   - Properly handles mixed intent (answer + question)
   - Uses document context for clarifications

3. **Maintains Flow**
   - After clarification, re-asks the original question
   - User can then provide their answer
   - Session continues smoothly

## Next Steps (Optional Enhancements)

1. **Question Extraction for MIXED**
   - Currently treats entire message as answer for evaluation
   - Could add logic to extract answer part vs question part
   - Would improve evaluation accuracy

2. **Context Awareness**
   - Could pass current question context to RAG for better clarifications
   - E.g., "what is chunker?" when asked during a question about document processing

3. **Caching**
   - Cache common clarification questions
   - Reduce RAG calls for repeated questions

---

**Status:** ✅ Implemented and ready for testing  
**Date:** October 6, 2025  
**Impact:** Fixes intent classification user experience without breaking existing functionality
