# 🚀 Quick Start Guide - Celery Integration

## TL;DR - Get Started in 5 Minutes

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Redis
```bash
# Using Docker (easiest)
docker run -d -p 6379:6379 --name inzighted_redis redis:7-alpine

# Verify Redis is running
redis-cli ping  # Should return: PONG
```

### 3. Set Environment Variables
```bash
# Add to your .env file or export
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 4. Start Celery Workers

**Windows (PowerShell):**
```powershell
cd backend
.\start_celery_workers.ps1
```

**Linux/Mac:**
```bash
cd backend
chmod +x start_celery_workers.sh
./start_celery_workers.sh
```

**Or using Docker:**
```bash
docker-compose up -d
```

### 5. Test It Works
```bash
cd backend
python test_celery_integration.py
```

You should see all tests pass! ✅

---

## 🎯 What Changed?

### Before Celery
```
User uploads document → Wait 30-60 seconds → Get response
```

### After Celery
```
User uploads document → Get immediate response (2-3 seconds)
                     ↓
        Background worker processes document
```

---

## 📊 API Changes

### Document Upload Response

**Old Response:**
```json
{
  "message": "Document ingestion completed successfully.",
  "document": {...}
}
```

**New Response:**
```json
{
  "message": "Document uploaded successfully. Processing started in background.",
  "document": {...},
  "task_id": "celery-task-uuid",
  "async": true,
  "status": "processing"
}
```

### New Endpoint: Check Status

```bash
GET /api/documents/<document_id>/status/

Response:
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "processing",  // or "completed", "failed"
  "message": "Document is being processed...",
  "upload_date": "2025-10-05T..."
}
```

---

## 🔍 Quick Verification

### Check Redis
```bash
redis-cli ping
# Output: PONG
```

### Check Workers
```bash
celery -A hellotutor inspect active
# Should show 4 active workers
```

### Upload Test Document
```bash
curl -X POST http://localhost:8000/api/ingest/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"
  
# Should get immediate 202 Accepted response
```

---

## 🐛 Common Issues

### "Connection refused" error
**Fix:** Start Redis first
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### "No module named 'celery'"
**Fix:** Install dependencies
```bash
pip install -r requirements.txt
```

### Workers not starting
**Fix:** Check environment variables
```bash
echo $CELERY_BROKER_URL
# Should output: redis://localhost:6379/0
```

---

## 📚 More Information

- Full setup guide: See `CELERY_SETUP.md`
- Architecture details: See implementation comments in code
- Troubleshooting: See `CELERY_SETUP.md` troubleshooting section

---

## ✅ Success Checklist

- [ ] Redis installed and running
- [ ] Celery dependencies installed
- [ ] 4 workers started
- [ ] Test script passes
- [ ] Document upload returns immediately
- [ ] Status endpoint works

**All checked? You're ready to go! 🎉**
