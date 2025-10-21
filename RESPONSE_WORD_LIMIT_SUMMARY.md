# Response Word Limit Summary

## Overview
All **corrective/validation** messages in the tutoring chat system are limited to **15 words** to ensure concise, clear feedback. Educational content (RAG answers to user questions) remains informative and detailed.

---

## 1. Message Validation (`backend/api/message_validation.py`)

### Functions with 15-Word Limit:

#### `is_irrelevant_answer()` - LLM Relevance Check
- **Location**: Line ~289
- **Purpose**: LLM-based relevance scoring when keyword heuristics are inconclusive
- **Implementation**: `gemini_client.generate_response(llm_prompt, max_tokens=16, max_words=15)`
- **Status**: ✅ **Enforced**

#### `categorize_invalid_message()` - Short Answer Validation
- **Location**: Line ~445
- **Purpose**: LLM judges if 1-3 word answers are sufficient
- **Implementation**: `gemini_client.generate_response(prompt, max_tokens=16, max_words=15)`
- **Status**: ✅ **Enforced**

#### `get_corrective_message()` - Tailored Corrective Messages
- **Location**: Line ~573
- **Purpose**: Generate dynamic corrective message for irrelevant answers
- **Implementation**: 
  - `gemini_client.generate_response(lm_prompt, max_tokens=80, max_words=15)`
  - `enforce_max_words(reply, max_words=15)` for both LLM and base messages
- **Status**: ✅ **Enforced**

---

## 2. RAG Query (`backend/api/rag_query.py`)

### Functions with 15-Word Limit:

#### `query_rag()` - General Knowledge Fallback (No Document Context)
- **Location**: Lines ~119, ~206
- **Purpose**: Fallback response when no document chunks found
- **Implementation**: `gemini_client.generate_response(fallback_prompt.format(query=query), max_tokens=800, max_words=15)`
- **Status**: ✅ **Enforced**

**Note**: The primary RAG response (with document context) is NOT limited to 15 words - it provides educational answers and should remain informative.

---

## 3. Chat Views (`backend/api/views/chat_views.py`)

### Functions with 15-Word Limit:

#### `ChatBotView.post()` - Emoji/Gibberish Validation
- **Location**: Lines ~34-43
- **Purpose**: Corrective messages for invalid chat inputs
- **Implementation**: 
  - `enforce_max_words("I noticed you reacted with an emoji...", max_words=15)`
  - `enforce_max_words("I couldn't understand that message...", max_words=15)`
- **Status**: ✅ **Enforced**

---

## 4. Agent Flow (`backend/api/agent_flow.py`)

### Functions WITHOUT 15-Word Limit (Educational Content):

#### `_answer_user_question_with_rag()` - RAG Answers to User Questions
- **Location**: Lines ~626-729
- **Purpose**: Answer user's clarification questions (e.g., "what is sensible heat?")
- **Implementation**: No word limit - provides detailed educational explanations
- **Reasoning**: Educational content should be informative, not artificially truncated
- **Status**: ✅ **Intentionally Unlimited**

#### Error Fallback Messages
- **Location**: Lines ~360, ~529
- **Message**: "Sorry, I couldn't fetch an answer right now."
- **Word Count**: 8 words
- **Status**: ✅ **Already Compliant** (< 15 words)

---

## 5. Gemini Client (`backend/api/gemini_client.py`)

### Core Word Limiting Mechanism:

#### `generate_response()` - Word Truncation
- **Location**: Lines ~54-186
- **Parameter**: `max_words: int | None = None`
- **Implementation**: 
  ```python
  if max_words is not None:
      words = response_text.split()
      if len(words) > max_words:
          truncated = ' '.join(words[:max_words])
          if not re.search(r'[.!?]$', truncated):
              truncated += '...'
          response_text = truncated
  ```
- **Status**: ✅ **Active**

---

## Summary of Changes Made

| File | Line(s) | Change | Status |
|------|---------|--------|--------|
| `message_validation.py` | 289, 445, 573 | Added `max_words=15` to all validation LLM calls | ✅ Complete |
| `rag_query.py` | 119, 206 | Added `max_words=15` to fallback responses | ✅ Complete |
| `chat_views.py` | 34, 40 | Wrapped corrective messages with `enforce_max_words()` | ✅ Complete |
| `agent_flow.py` | N/A | No changes (educational content exempt) | ✅ Reviewed |

---

## Testing Checklist

- [x] All edited files pass syntax validation (`get_errors`)
- [x] Corrective messages limited to 15 words
- [x] Educational RAG answers remain informative (not truncated)
- [x] Error fallback messages already compliant
- [ ] Manual testing: Trigger validation errors and verify concise responses
- [ ] Manual testing: Ask clarification questions and verify detailed answers

---

## Design Rationale

### Why 15 Words?

1. **User Experience**: Short, actionable feedback prevents information overload
2. **Mobile Optimization**: Concise messages display better on small screens
3. **Cognitive Load**: Quick corrections allow users to focus on learning, not debugging

### Why Educational Content is Exempt?

1. **Learning Effectiveness**: Detailed explanations are essential for understanding
2. **Context Preservation**: RAG-generated answers include relevant document excerpts
3. **User Expectations**: When users ask "what is X?", they expect comprehensive answers

---

## Future Enhancements

1. **Adaptive Limits**: Adjust word count based on message type (errors: 10 words, hints: 20 words)
2. **Language-Specific Limits**: Tanglish may need slightly higher limits due to code-mixing
3. **A/B Testing**: Measure learning outcomes with 10-word vs 15-word vs 20-word limits
4. **Analytics**: Track word count distribution across all response types

---

**Last Updated**: 2025-10-21  
**Maintainer**: GitHub Copilot  
**Related Docs**: `MESSAGE_VALIDATION.md`, `RAG_FALLBACK_IMPLEMENTATION.md`
