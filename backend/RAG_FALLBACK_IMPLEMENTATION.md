# RAG Fallback to General Knowledge LLM - Implementation Summary

## Overview
Enhanced the RAG (Retrieval Augmented Generation) system to intelligently fall back to general LLM knowledge when user documents don't contain relevant information to answer their question.

## Problem
Previously, when RAG couldn't find relevant content in user documents, it would simply return "I don't know based on the provided documents" - a poor user experience.

## Solution
Implemented a two-tier fallback system:

### Tier 1: No Chunks Found
- **Scenario**: Pinecone returns 0 matches for the query
- **Action**: Immediately use general LLM to answer the question
- **Response**: Includes note "(Note: This answer is based on general knowledge as no specific content was found in your uploaded documents.)"

### Tier 2: Chunks Found but Irrelevant
- **Scenario**: Pinecone returns chunks BUT they don't contain the answer
- **Detection**: LLM responds with "NO_ANSWER_IN_CONTEXT" or similar phrases
- **Action**: Fallback to general LLM to answer the question
- **Response**: Includes note "(Note: This answer is based on general knowledge as the specific information wasn't found in your uploaded documents.)"

## Files Modified

### 1. `backend/api/rag_query.py`
- **Function**: `query_rag(user_id: str, query: str, top_k: int = 5)`
- **Changes**:
  - Enhanced RAG context prompt to be stricter about detecting when context doesn't contain the answer
  - Added explicit "NO_ANSWER_IN_CONTEXT" trigger phrase
  - Implemented fallback prompt when no chunks found
  - Implemented fallback prompt when LLM can't answer from context
  - Added multiple detection patterns for "I don't know" scenarios
  - Added length check for suspiciously short responses (likely irrelevant context)

#### Key prompt changes:
```python
# OLD PROMPT (too lenient)
"If the answer cannot be found in the context, respond exactly: 'I don't know based on the provided documents.'"

# NEW PROMPT (stricter)
"CRITICAL RULES:
- If the context does NOT contain information to answer the question, you MUST respond EXACTLY with: 'NO_ANSWER_IN_CONTEXT'
- Only provide an answer if you can directly find the information in the context.
- Do NOT try to infer, deduce, or piece together partial information."
```

#### Fallback detection logic:
```python
no_answer_indicators = [
    "NO_ANSWER_IN_CONTEXT",
    "I don't know based on the provided documents",
    "cannot be found in the context",
    "not found in the context",
    "no information in the context"
]

# Also check for suspiciously short responses
if len(llm_response.strip()) < 30:
    should_fallback = True
```

### 2. `backend/api/agent_flow.py`
- **Function**: `_answer_user_question_with_rag(self, user_message: str)`
- **Changes**:
  - Updated detection logic to recognize general knowledge fallback responses
  - Properly handle the "(Note: This answer is based on general knowledge..." marker
  - Don't try to summarize or rewrite general knowledge responses

#### Key change:
```python
# Check if RAG returned general knowledge fallback (contains the note)
if "(Note: This answer is based on general knowledge" in rag_response:
    logger.info("[RAG] Received general knowledge fallback response")
    # Return the RAG response as-is. The tutoring agent will attach a separate
    # proceed prompt message (not concatenated into the same reply).
    return rag_response
```

## Flow Diagram

```
User asks question
       ↓
Embed query & retrieve from Pinecone
       ↓
   ┌─────────────────┐
   │ Chunks found?   │
   └─────────────────┘
         ↙     ↘
      NO       YES
       ↓         ↓
   Fallback   Build RAG prompt with chunks
   to LLM        ↓
   (Tier 1)   Call LLM with context
       ↓         ↓
       │     ┌──────────────────────┐
       │     │ Can LLM answer from  │
       │     │ context?             │
       │     └──────────────────────┘
       │           ↙        ↘
       │         YES        NO
       │          ↓          ↓
       │     Return      Fallback to LLM
       │     answer      (Tier 2)
       │          ↓          ↓
       └──────────┴──────────┘
                  ↓
        Add general knowledge note
                  ↓
        Return to user
```

## Testing

### Automated Tests
- `backend/test_rag_fallback.py` - Unit tests with mocks
- `backend/test_rag_fallback_real.py` - Real-world tests with actual API calls

### Manual Testing
Run the real-world test:
```bash
cd backend
python test_rag_fallback_real.py
```

Expected results:
1. Questions about topics NOT in user's documents → General knowledge response with note
2. Questions about topics IN user's documents → RAG context response (no note)
3. Edge cases handled gracefully

## Benefits

1. **Better UX**: Users get helpful answers even when their documents don't contain the information
2. **Transparent**: Clear note indicates when general knowledge is used vs. document-specific content
3. **Smart Detection**: Multiple fallback triggers ensure irrelevant context doesn't produce bad answers
4. **Maintains Security**: Tenant isolation still enforced; only falls back when user's own documents don't help

## Configuration

No new settings required. Uses existing:
- `LLM_API_KEY` - For Gemini LLM calls
- `EMBEDDING_API_KEY` - For embeddings
- `PINECONE_API_KEY` - For vector search

## Limitations

1. Fallback adds 1-2 extra LLM calls in "no answer" scenarios (acceptable trade-off for UX)
2. General knowledge responses may not be as specific as document-based answers
3. Relies on LLM to correctly identify when context doesn't contain the answer

## Future Enhancements

1. Add confidence scoring to determine fallback threshold
2. Cache general knowledge responses for common questions
3. Add user preference to disable/enable general knowledge fallback
4. Track metrics on fallback frequency to identify document gaps
5. Implement hybrid responses that combine partial document context with general knowledge

## Rollout Checklist

- [x] Implementation complete
- [x] Unit tests added
- [x] Real-world test script created
- [ ] Manual testing in development environment
- [ ] Code review
- [ ] Deploy to staging
- [ ] Monitor fallback frequency and user feedback
- [ ] Deploy to production

## Support & Debugging

If issues arise:
1. Check logs for "Falling back to general knowledge..." messages
2. Verify LLM API key is valid
3. Check Pinecone query returns expected chunks
4. Review prompt templates in `rag_query.py`
5. Test with `test_rag_fallback_real.py`

## Related Files
- `backend/api/rag_query.py` - Main RAG logic
- `backend/api/agent_flow.py` - Agent flow integration
- `backend/api/gemini_client.py` - LLM client
- `backend/api/tanglish_prompts.py` - Prompt templates
