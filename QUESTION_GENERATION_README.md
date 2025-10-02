# Improved Question Generation System

## Problem Solved

The previous question generation system had a major flaw: it used a static embedding query (`"generate tutoring question key concepts important topics"`) that always retrieved the same chunks from Pinecone, leading to repetitive questions.

## New Implementation

### 🎯 Core Concept
The new system pre-generates a **batch of unique questions** from ALL chunks of a document, stores them temporarily, and serves them one by one during tutoring sessions.

### 🔧 How It Works

1. **Batch Generation**: When questions are needed, the system:
   - Retrieves ALL chunks for a specific document/user from Pinecone
   - Groups chunks strategically across the document
   - Generates unique questions for each group using different content sections
   - Shuffles questions for variety

2. **Temporary Storage**: Questions are cached using Django's cache framework with a 1-hour expiration

3. **Sequential Serving**: Questions are served one by one, with automatic regeneration when the batch is exhausted

### 📁 Key Files Added/Modified

- `backend/api/rag_query.py` - Core batch generation logic
- `backend/api/views.py` - New endpoint for manual batch generation
- `backend/api/urls.py` - URL routing for new endpoint
- `backend/test_question_batch.py` - Test script
- `backend/api/management/commands/pregenerate_questions.py` - Management command

### 🚀 New Functions

#### Core Functions
```python
# Generate a batch of unique questions
generate_question_batch(user_id, document_id, num_questions=10)

# Store questions in cache
store_question_batch(user_id, document_id, questions)

# Get next question from batch
get_next_question(user_id, document_id)

# Clear cached questions
clear_question_cache(user_id, document_id)

# High-level function for session setup
pregenerate_questions_for_session(user_id, document_id, num_questions=10)
```

#### Backward Compatibility
```python
# This still works but now uses the batch system internally
generate_tutoring_question(user_id, document_id)
```

### 🌐 New API Endpoint

**POST** `/api/tutoring/questions/batch/`
```json
{
  "document_id": "uuid-here",
  "num_questions": 10
}
```

**DELETE** `/api/tutoring/questions/batch/?document_id=uuid-here`

### 🎮 Usage Examples

#### 1. Test the System
```powershell
# Run the test script
python .\backend\test_question_batch.py
```

#### 2. Pre-generate Questions via Management Command
```powershell
# Pre-generate 15 questions for a specific user/document
python .\backend\manage.py pregenerate_questions --user-id "user-uuid" --document-id "doc-uuid" --count 15
```

#### 3. Start Session with Pre-generation
```javascript
// Frontend: Start session with automatic question pre-generation
const response = await tutoringAPI.startSession(documentId, {
  pregenerate_questions: true,
  question_batch_size: 15
});
```

#### 4. Manual Batch Generation via API
```javascript
// Pre-generate questions manually
const response = await fetch('/api/tutoring/questions/batch/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    document_id: 'doc-uuid',
    num_questions: 10
  })
});
```

### 🔍 How Questions Are Made Unique

1. **Document Segmentation**: The entire document is divided into groups
2. **Content Diversity**: Each question group uses different chunks/sections
3. **Unique Prompting**: Each group gets a focused prompt for its specific content
4. **Randomization**: Questions are shuffled after generation
5. **Context Awareness**: Questions are tailored to the actual content available

### 🧪 Testing

Run comprehensive tests:
```powershell
# Test the batch generation system
python .\backend\test_question_batch.py

# Test the original RAG flow (should still work)
python .\backend\test_rag_flow.py
```

### ⚡ Performance Benefits

- **Faster Response**: No repeated embedding/retrieval during sessions
- **Better Coverage**: Questions span the entire document content
- **No Repetition**: Systematic approach prevents duplicate questions
- **Scalable**: Cached questions reduce LLM API calls

### 🔧 Configuration

Default settings in your Django settings:
```python
# Cache timeout for question batches (seconds)
QUESTION_CACHE_TIMEOUT = 3600  # 1 hour

# Maximum questions per batch
MAX_QUESTIONS_PER_BATCH = 20

# Default batch size
DEFAULT_QUESTION_BATCH_SIZE = 10
```

### 🐛 Troubleshooting

#### No Questions Generated
- Check if document chunks exist in Pinecone
- Verify tenant isolation (user has access to document)
- Check Gemini LLM availability

#### Cache Issues
- Clear cache manually: `clear_question_cache(user_id, document_id)`
- Check Django cache configuration
- Verify cache backend is working

#### API Errors
- Ensure user authentication
- Validate document ownership
- Check request payload format

### 🚀 Next Steps

1. **Run Tests**: Execute the test script to verify everything works
2. **Try Manual Generation**: Use the management command to pre-generate questions
3. **Test in Frontend**: Modify frontend to use the new batch generation options
4. **Monitor Performance**: Check cache hit rates and question quality

The system maintains full backward compatibility while providing much better question diversity and performance!