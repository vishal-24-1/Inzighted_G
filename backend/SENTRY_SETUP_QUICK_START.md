# Sentry Setup - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Install Sentry SDK

```powershell
cd backend
pip install "sentry-sdk[django]>=1.40.0"
```

Or if you have the full `requirements.txt`:

```powershell
pip install -r requirements.txt
```

### Step 2: Get Your Sentry DSN

1. **Go to:** https://sentry.io/
2. **Sign up or log in**
3. **Create a new project:**
   - Click "Projects" → "Create Project"
   - Select "Django" as the platform
   - Name it "HelloTutor-Backend" (or similar)
4. **Copy your DSN** - It looks like:
   ```
   https://abc123def456@o123456.ingest.sentry.io/7890123
   ```

### Step 3: Configure Environment Variables

Add to your `.env` file (create one if it doesn't exist):

```bash
# Sentry Configuration
SENTRY_DSN=https://your-actual-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0
```

**Important:** Replace `https://your-actual-dsn@sentry.io/project-id` with your real DSN from Step 2!

### Step 4: Restart Django Server

```powershell
cd backend
python manage.py runserver
```

Look for this confirmation in the console:
```
✅ Sentry initialized for environment: development
```

### Step 5: Test It Works

**Option A - Test Endpoint (if you have one):**

Visit: `http://localhost:8000/sentry-debug/`

**Option B - Django Shell:**

```powershell
python manage.py shell
```

Then run:
```python
import sentry_sdk
sentry_sdk.capture_message("Hello from HelloTutor backend!", level="info")
```

**Option C - Trigger Test Error:**

In any view, temporarily add:
```python
raise Exception("Test error for Sentry")
```

### Step 6: Check Sentry Dashboard

1. Go to https://sentry.io/
2. Open your project
3. You should see the test message or error appear within seconds!

## 🎯 What's Now Being Monitored

### ✅ Critical Components

1. **LLM/AI Calls** (`gemini_client.py`)
   - API failures, key exhaustion, rate limits

2. **Document Processing** (`rag_ingestion.py`)
   - Upload failures, parsing errors, embedding issues

3. **API Endpoints** (`views.py`)
   - Auth errors, chat failures, tutoring issues

4. **RAG Queries** (`rag_query.py`)
   - Query failures, question generation errors

5. **S3 Storage** (`s3_storage.py`)
   - Upload/download failures, credential issues

6. **Insights** (`insight_generator.py`)
   - SWOT analysis failures

7. **Authentication** (`auth.py`)
   - HMAC errors, tenant tag issues

## 🔧 Environment-Specific Settings

### Development (Local Testing)
```bash
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0  # Capture 100%
```

### Staging
```bash
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=0.5  # Capture 50%
```

### Production
```bash
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # Capture 10% to save quota
```

## 📊 What You'll See in Sentry

### Error Details Include:
- **Component** - Which file/module
- **Method** - Which function
- **Context** - User ID, session ID, file names, etc.
- **Stack trace** - Full Python traceback
- **Request data** - HTTP method, URL, headers
- **Environment** - Django version, Python version, OS

### Example Error Event:
```
Component: gemini_client
Method: generate_response
Status Code: 429
Key Attempt: 2
User ID: abc-123-def
Error: Rate limit exceeded
```

## 🚨 Common Issues & Fixes

### Issue: "Sentry not capturing errors"

**Fix 1:** Check your DSN is set correctly:
```powershell
# Windows PowerShell
$env:SENTRY_DSN
# Should show your DSN, not empty
```

**Fix 2:** Verify the import:
```python
# In Python shell
import sentry_sdk
print(sentry_sdk.Hub.current.client)
# Should show a Client object, not None
```

### Issue: "Too many events, quota exceeded"

**Fix:** Reduce sample rate in `.env`:
```bash
SENTRY_TRACES_SAMPLE_RATE=0.1  # Only 10% of transactions
```

### Issue: "Not seeing context in errors"

**Fix:** The integration automatically adds context. If missing, check that:
- User is authenticated (for user_id)
- Request object is available
- Django middleware is properly configured

## 📈 Next Steps

1. **Set up Alerts:**
   - Go to Sentry → Alerts → Create Alert Rule
   - Set thresholds (e.g., >10 errors per hour)
   - Choose notification channel (email, Slack, etc.)

2. **Review Performance:**
   - Navigate to Performance tab in Sentry
   - Identify slow endpoints
   - Optimize based on data

3. **Create Dashboards:**
   - Use Sentry Dashboards to visualize error trends
   - Track error rates by component
   - Monitor LLM API success rates

4. **Read Full Documentation:**
   - See `SENTRY_INTEGRATION.md` for complete details
   - Review best practices and security considerations

## 📞 Support

**Issues?** Check the full documentation: `SENTRY_INTEGRATION.md`

**Sentry Help:** https://docs.sentry.io/platforms/python/guides/django/

---

**Setup Time:** ~5 minutes  
**Last Updated:** October 4, 2025
