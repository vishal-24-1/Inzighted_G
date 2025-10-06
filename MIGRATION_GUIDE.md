# Migration Guide - Tanglish Agent Implementation

## Overview

This guide walks you through deploying the new Tanglish Agent flow to your existing HelloTutor backend.

## Prerequisites

- ✅ Existing HelloTutor project is working
- ✅ Python environment is activated
- ✅ Database is accessible (PostgreSQL)
- ✅ `.env` file has `LLM_API_KEY` and `EMBEDDING_API_KEY`

## Step-by-Step Migration

### 1. Backup Your Database (Recommended)

```powershell
# PostgreSQL backup
pg_dump -U your_username -d your_database -f backup_before_tanglish_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql
```

### 2. Create Django Migrations

```powershell
cd backend
python manage.py makemigrations api
```

Expected output:
```
Migrations for 'api':
  api/migrations/XXXX_add_tanglish_agent_models.py
    - Add field language to chatsession
    - Add field classifier_token to chatmessage
    - Create model QuestionItem
    - Create model EvaluatorResult
```

### 3. Review the Migration

```powershell
python manage.py sqlmigrate api XXXX
```

This shows you the SQL that will be executed. Verify it looks correct.

### 4. Apply the Migration

```powershell
python manage.py migrate api
```

Expected output:
```
Running migrations:
  Applying api.XXXX_add_tanglish_agent_models... OK
```

### 5. Verify Migration

```powershell
python manage.py shell
```

In the shell:
```python
from api.models import QuestionItem, EvaluatorResult, ChatSession
print(QuestionItem._meta.get_fields())
print(EvaluatorResult._meta.get_fields())
print("language" in [f.name for f in ChatSession._meta.get_fields()])
exit()
```

All should return successfully.

### 6. Run Test Script

```powershell
python test_tanglish_agent.py
```

This will verify:
- ✅ Models are accessible
- ✅ URL routes are registered
- ✅ Gemini client methods work
- ✅ Intent classifier fallback works

### 7. Test API Endpoints

#### 7.1 Get Authentication Token

```powershell
# Login to get token
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login/" -Method POST -Body (@{
    email = "your_email@example.com"
    password = "your_password"
} | ConvertTo-Json) -ContentType "application/json"

$token = $response.access
```

#### 7.2 Start Agent Session

```powershell
# Start a new Tanglish session
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Get a document ID first
$docs = Invoke-RestMethod -Uri "http://localhost:8000/api/documents/" -Headers $headers
$documentId = $docs[0].id

# Start agent session
$sessionResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/start/" -Method POST -Headers $headers -Body (@{
    document_id = $documentId
    language = "tanglish"
} | ConvertTo-Json)

$sessionId = $sessionResponse.session_id
$firstQuestion = $sessionResponse.first_question.text
Write-Host "Session started: $sessionId"
Write-Host "First question: $firstQuestion"
```

#### 7.3 Submit an Answer

```powershell
# Submit an answer
$answerResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/$sessionId/respond/" -Method POST -Headers $headers -Body (@{
    message = "My answer to the question"
} | ConvertTo-Json)

Write-Host "Evaluation XP: $($answerResponse.evaluation.xp)"
Write-Host "Score: $($answerResponse.evaluation.score)"
Write-Host "Next question: $($answerResponse.next_question.text)"
```

#### 7.4 Check Session Status

```powershell
# Get session status
$status = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/$sessionId/status/" -Headers $headers

Write-Host "Progress: $($status.current_question_index) / $($status.total_questions)"
Write-Host "Total XP: $($status.total_xp)"
```

### 8. Verify Database Records

```powershell
python manage.py shell
```

In the shell:
```python
from api.models import QuestionItem, EvaluatorResult, ChatSession

# Check question items were created
print(f"QuestionItems: {QuestionItem.objects.count()}")
print(QuestionItem.objects.first())

# Check evaluations
print(f"Evaluations: {EvaluatorResult.objects.count()}")
if EvaluatorResult.objects.exists():
    eval = EvaluatorResult.objects.first()
    print(f"Sample evaluation: score={eval.score}, xp={eval.xp}")

# Check session with language
sessions_with_language = ChatSession.objects.exclude(language__isnull=True)
print(f"Sessions with language: {sessions_with_language.count()}")

exit()
```

## Troubleshooting

### Issue: Migration fails with "column already exists"

**Solution**: Someone may have run migrations before. Check:
```powershell
python manage.py showmigrations api
```

If the migration is already applied, skip to verification steps.

### Issue: "ImportError: cannot import name 'AgentSessionStartView'"

**Solution**: Ensure `backend/api/views/__init__.py` exists and has correct imports. Restart Django server:
```powershell
python manage.py runserver
```

### Issue: "LLM_API_KEY not configured"

**Solution**: Check `.env` file has:
```env
LLM_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.0-flash-exp
```

### Issue: Intent classification always returns fallback

**Solution**: This is normal if Gemini API is unavailable. The fallback ensures the system continues working. Check:
1. API key is valid
2. You have API quota
3. Network connectivity to Gemini API

### Issue: Questions not generating

**Solution**: Check:
1. Document has been processed (status='completed')
2. Pinecone has vectors for the user's tenant_tag
3. Check Django logs for detailed error messages

### Issue: Evaluation fails

**Solution**: Ensure the evaluation prompt is working:
```powershell
python manage.py shell
```

```python
from api.gemini_client import gemini_client

eval_result = gemini_client.evaluate_answer(
    context="Test question about resonance",
    expected_answer="Current and voltage are in phase",
    student_answer="They are in phase"
)
print(eval_result)
```

## Rollback Procedure (If Needed)

If you need to rollback:

### 1. Revert Migration

```powershell
python manage.py migrate api <previous_migration_name>
```

### 2. Remove New Code

```powershell
# Remove new files
Remove-Item backend\api\tanglish_prompts.py
Remove-Item backend\api\agent_flow.py
Remove-Item backend\api\views\agent_views.py
Remove-Item backend\api\views\__init__.py

# Restore old files from git
git checkout HEAD -- backend/api/models.py
git checkout HEAD -- backend/api/gemini_client.py
git checkout HEAD -- backend/api/urls.py
git checkout HEAD -- .env.example
```

### 3. Restart Server

```powershell
python manage.py runserver
```

## Post-Migration Monitoring

### 1. Check Django Logs

Look for:
- `Intent classified as: DIRECT_ANSWER/MIXED/RETURN_QUESTION`
- `Answer evaluated: score=X.XX, XP=XX`
- `Session insights generated successfully`

### 2. Check Sentry

Monitor for:
- Intent classification failures
- Question generation errors
- Answer evaluation errors
- Insights generation failures

### 3. Database Growth

Monitor table sizes:
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('api_questionitem', 'api_evaluatorresult')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Performance Considerations

### Expected Latencies

- **Start Session**: 3-5 seconds (generates 10 questions)
- **Submit Answer**: 1-2 seconds (classification + evaluation)
- **Session Complete**: 2-3 seconds (insights generation)

### Optimization Tips

1. **Cache Question Batches**: Already implemented in TutoringQuestionBatch
2. **Async Processing**: Can add Celery task for insights generation
3. **Index Database**: Ensure indexes on:
   - `QuestionItem.batch_id`
   - `QuestionItem.order`
   - `EvaluatorResult.message_id`

### Scaling

For high traffic:
1. Add Redis caching for active sessions
2. Move insights generation to background task
3. Rate limit question generation endpoint
4. Add database read replicas

## Success Metrics

After migration, track:

- ✅ Number of agent sessions started
- ✅ Average XP per session
- ✅ Question archetype distribution
- ✅ Intent classification accuracy (DIRECT_ANSWER vs others)
- ✅ Session completion rate
- ✅ Insights generation success rate

## Next Steps

Once migration is successful:

1. **Update Frontend**: Add UI for new agent endpoints
2. **User Documentation**: Create user guide for Tanglish tutoring
3. **Analytics Dashboard**: Track XP, archetypes, completion rates
4. **A/B Testing**: Compare old vs new tutoring flow
5. **Feedback Loop**: Collect user feedback on Tanglish questions

## Support

If you encounter issues:

1. Check `TANGLISH_AGENT_IMPLEMENTATION.md` for API examples
2. Run `test_tanglish_agent.py` to diagnose
3. Check Django logs and Sentry
4. Review database records with shell commands above

---

**Last Updated**: October 6, 2025  
**Version**: 1.0  
**Status**: Ready for deployment
