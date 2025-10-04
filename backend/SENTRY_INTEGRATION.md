# Sentry Integration Documentation

## Overview

Sentry has been fully integrated into the HelloTutor backend to provide comprehensive error tracking, monitoring, and performance insights across all critical components of the application.

## What's Been Integrated

### ✅ 1. Global Sentry Initialization

**Location:** `backend/hellotutor/settings.py`

- Sentry SDK initialized at application startup
- DSN loaded from `SENTRY_DSN` environment variable
- Environment auto-detected from `SENTRY_ENVIRONMENT` or `ENV` variable
- Performance monitoring with configurable traces sample rate
- PII (Personally Identifiable Information) protection enabled by default

**Configuration:**
```python
SENTRY_DSN=your_sentry_dsn_here
SENTRY_ENVIRONMENT=development  # or production, staging, etc.
SENTRY_TRACES_SAMPLE_RATE=1.0  # 1.0 = 100% of transactions
```

### ✅ 2. Gemini LLM Client Error Tracking

**Location:** `backend/api/gemini_client.py`

**Monitored Operations:**
- Client initialization failures
- LLM API key configuration errors
- HTTP errors (401, 403, 429, 5xx) with status codes and response bodies
- Request exceptions with retry context
- All API keys exhaustion
- Embedding generation failures
- Token counting errors

**Context Captured:**
- Component: `gemini_client`
- Method name
- Key attempt number
- Retry attempt number
- Error status codes
- Response bodies (truncated for safety)
- Text count for embedding operations

### ✅ 3. API Endpoints Error Tracking

**Location:** `backend/api/views.py`

**Monitored Endpoints:**
- `GoogleAuthView` - Google OAuth authentication
  - Token verification failures
  - Unexpected authentication errors
- `IngestView` - Document upload and ingestion
  - Document processing failures with filename and user context
- `ChatBotView` - AI chatbot conversations
  - Response generation failures with session context
- `TutoringSessionStartView` - Start tutoring sessions
  - Session creation failures
- `TutoringSessionAnswerView` - Process student answers
  - Answer processing failures with session ID
- `SessionInsightsView` - Generate SWOT insights
  - Insights retrieval failures

**Context Captured:**
- Component: `auth`, `document_ingestion`, `chat`, `tutoring`, `insights`
- View class name
- User ID (when authenticated)
- Session ID (for session-based operations)
- Document ID (for document operations)
- Filename (for uploads)

### ✅ 4. RAG Pipeline Error Tracking

**Location:** `backend/api/rag_ingestion.py`

**Monitored Operations:**
- S3 document download failures
- Document reading and chunking errors
- Pinecone initialization failures
- Embedding generation errors with chunk counts
- Pinecone upsert failures with vector counts
- Catch-all for unexpected ingestion errors

**Context Captured:**
- Component: `rag_ingestion`
- Function: `ingest_document_from_s3`
- Stage: `document_reading_chunking`, `initialization`, `embedding`, `pinecone_upsert`
- S3 key
- User ID
- Chunks count
- Vectors count

**Location:** `backend/api/rag_query.py`

**Monitored Operations:**
- Question batch generation failures
- Question generation errors
- RAG query failures with query context (first 100 chars)

**Context Captured:**
- Component: `rag_query`
- Function: `generate_question_batch_for_session`, `generate_tutoring_question`, `query_rag`
- Session ID
- Document ID
- User ID
- Query snippet

### ✅ 5. S3 Storage Error Tracking

**Location:** `backend/api/s3_storage.py`

**Monitored Operations:**
- S3 client initialization failures
- AWS credentials not found errors
- Upload failures with user and filename context
- Download failures with S3 key context
- Delete failures with S3 key context
- All ClientError and generic exceptions

**Context Captured:**
- Component: `s3_storage`
- Method: `_initialize_client`, `upload_document`, `download_document`, `delete_document`
- User ID (for uploads)
- Filename (for uploads)
- S3 key (for downloads/deletes)

### ✅ 6. Insight Generator Error Tracking

**Location:** `backend/api/insight_generator.py`

**Monitored Operations:**
- Session insight generation failures
- SWOT analysis generation errors
- Insight record creation errors

**Context Captured:**
- Component: `insight_generator`
- Method/Function: `generate_session_insights`, `_generate_swot_analysis`, `generate_insights_for_session`
- Session ID
- Q&A pairs count

### ✅ 7. Authentication Error Tracking

**Location:** `backend/api/auth.py`

**Monitored Operations:**
- HMAC_SECRET configuration errors
- Tenant tag generation failures

**Context Captured:**
- Component: `auth`
- Function: `get_tenant_tag`
- User ID

## Setup Instructions

### 1. Install Sentry SDK

The Sentry SDK has been added to `requirements.txt`:

```bash
cd backend
pip install -r requirements.txt
```

Or install directly:

```bash
pip install "sentry-sdk[django]>=1.40.0"
```

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Sentry Configuration
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=development  # or production, staging
SENTRY_TRACES_SAMPLE_RATE=1.0  # 1.0 = 100%, 0.1 = 10%
```

**Getting Your Sentry DSN:**
1. Log in to your Sentry account
2. Create a new project (Django type)
3. Copy the DSN from the project settings
4. Paste it into your `.env` file

### 3. Environment-Specific Configuration

**Development:**
```bash
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0  # Capture all transactions
```

**Production:**
```bash
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # Capture 10% of transactions to reduce quota usage
```

### 4. Test the Integration

Create a test endpoint or trigger an error:

```python
# In Django shell or a test view
import sentry_sdk
sentry_sdk.capture_message("Test message from HelloTutor backend", level="info")
```

Or trigger a test error:

```python
1 / 0  # This will be automatically captured by Sentry
```

Check your Sentry dashboard to confirm the event appears.

## What Gets Captured

### Automatic Captures

1. **Unhandled Exceptions** - All uncaught exceptions in Django views
2. **HTTP Errors** - 500, 502, 503 errors from LLM/API calls
3. **Database Errors** - Django ORM errors
4. **Middleware Errors** - Errors in Django middleware chain

### Manual Captures

1. **Custom Exceptions** - Wrapped with `sentry_sdk.capture_exception(e, extras={...})`
2. **Messages** - Important warnings/info via `sentry_sdk.capture_message(...)`
3. **Rich Context** - All captures include component, method, and operation-specific data

### Context Information

Every error capture includes:
- **Component** - Which module/file the error occurred in
- **Method/Function** - The specific function that failed
- **User Context** - User ID (when available, without PII)
- **Request Context** - For API endpoints
- **Custom Extras** - Operation-specific data (file names, counts, IDs, etc.)

## Best Practices

### 1. Don't Log Sensitive Data

The integration is configured to **NOT** send PII by default:
```python
send_default_pii=False
```

Avoid capturing:
- Passwords
- Email addresses (use user IDs instead)
- API keys or tokens
- Full document content (truncate large text)

### 2. Use Meaningful Context

Good:
```python
sentry_sdk.capture_exception(e, extras={
    "component": "rag_ingestion",
    "stage": "embedding",
    "chunks_count": len(chunks),
    "s3_key": s3_key
})
```

Bad:
```python
sentry_sdk.capture_exception(e)  # No context
```

### 3. Set Appropriate Sample Rates

- **Development:** 100% (`SENTRY_TRACES_SAMPLE_RATE=1.0`)
- **Production:** 10-20% (`SENTRY_TRACES_SAMPLE_RATE=0.1`)

This helps manage your Sentry quota while still capturing representative data.

### 4. Use Breadcrumbs for Complex Flows

For multi-step operations, add breadcrumbs:
```python
sentry_sdk.add_breadcrumb(
    category='document_processing',
    message='Starting document chunking',
    level='info'
)
```

### 5. Set User Context When Available

```python
sentry_sdk.set_user({
    "id": str(user.id),
    "username": user.username
})
```

This is automatically done by Django integration but can be manually set for background tasks.

## Monitoring Checklist

### Daily Checks
- [ ] Review new error issues in Sentry dashboard
- [ ] Check error frequency trends
- [ ] Identify and prioritize high-impact errors

### Weekly Checks
- [ ] Review performance metrics (transaction times)
- [ ] Analyze error patterns across components
- [ ] Check LLM API key exhaustion alerts
- [ ] Monitor S3 upload/download failure rates

### Monthly Checks
- [ ] Review quota usage and adjust sample rates if needed
- [ ] Analyze long-term error trends
- [ ] Update alerting rules based on patterns

## Alerting Rules (Recommended)

Set up alerts in Sentry for:

1. **Critical Errors**
   - LLM client initialization failures
   - All API keys exhausted
   - Database connection errors

2. **High-Volume Errors**
   - >10 errors per minute for any endpoint
   - >50% error rate on document ingestion

3. **Performance Degradation**
   - API response times >5 seconds
   - Embedding generation taking >30 seconds

4. **Business-Critical**
   - User authentication failures spike
   - Document upload failures spike
   - SWOT insight generation failures

## Troubleshooting

### Sentry Not Capturing Errors

1. **Check DSN Configuration:**
   ```bash
   echo $SENTRY_DSN
   # Should output your DSN, not empty
   ```

2. **Verify Initialization:**
   Check Django logs for:
   ```
   ✅ Sentry initialized for environment: development
   ```

3. **Test Manually:**
   ```python
   import sentry_sdk
   sentry_sdk.capture_message("Test", level="info")
   ```

### Too Many Events

1. **Reduce Sample Rate:**
   ```bash
   SENTRY_TRACES_SAMPLE_RATE=0.1  # 10%
   ```

2. **Filter Noisy Errors:**
   Add to `settings.py`:
   ```python
   def before_send(event, hint):
       # Filter out specific errors
       if 'specific_error_pattern' in str(hint):
           return None
       return event
   
   sentry_sdk.init(
       dsn=SENTRY_DSN,
       before_send=before_send
   )
   ```

### Missing Context

Ensure all `sentry_sdk.capture_exception()` calls include `extras`:
```python
sentry_sdk.capture_exception(e, extras={
    "component": "your_component",
    "method": "your_method",
    # ... other context
})
```

## Security Considerations

1. **PII Protection** - Disabled by default (`send_default_pii=False`)
2. **Credential Safety** - Never log API keys, passwords, or tokens
3. **Data Minimization** - Truncate large payloads (e.g., response bodies limited to 500 chars)
4. **User Privacy** - Use user IDs instead of emails or names

## Performance Impact

Sentry SDK is designed to be lightweight:
- **Minimal overhead** - <5ms per request in most cases
- **Async sending** - Errors sent in background threads
- **Sampling** - Configurable to reduce data volume

## Additional Resources

- [Sentry Django Documentation](https://docs.sentry.io/platforms/python/guides/django/)
- [Sentry Best Practices](https://docs.sentry.io/product/best-practices/)
- [Sentry Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Sentry Quotas Management](https://docs.sentry.io/product/accounts/quotas/)

---

**Last Updated:** October 4, 2025  
**Maintainer:** Backend Engineering Team
