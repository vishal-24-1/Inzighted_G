# Quick Start - Tanglish Agent

## 🚀 Get Started in 5 Minutes

### 1. Run Migrations (1 min)

```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor\backend
python manage.py makemigrations
python manage.py migrate
```

### 2. Verify Installation (30 sec)

```powershell
cd f:\ZAIFI\Tech\Projects\hellotutor
python test_tanglish_agent.py
```

Expected: All tests pass ✅

### 3. Start Django Server (30 sec)

```powershell
cd backend
python manage.py runserver
```

### 4. Test the Agent (3 min)

#### Option A: Using PowerShell

```powershell
# 1. Login and get token
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login/" `
    -Method POST `
    -Body (@{
        email = "your_email@example.com"
        password = "your_password"
    } | ConvertTo-Json) `
    -ContentType "application/json"

$token = $loginResponse.access
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# 2. Get your documents
$docs = Invoke-RestMethod -Uri "http://localhost:8000/api/documents/" -Headers $headers
$documentId = $docs[0].id
Write-Host "Using document: $($docs[0].filename)"

# 3. Start Tanglish session
$session = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/start/" `
    -Method POST `
    -Headers $headers `
    -Body (@{
        document_id = $documentId
        language = "tanglish"
    } | ConvertTo-Json)

$sessionId = $session.session_id
Write-Host "`nFirst Question:`n$($session.first_question.text)`n"

# 4. Submit an answer
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/$sessionId/respond/" `
    -Method POST `
    -Headers $headers `
    -Body (@{
        message = "Let me try to answer this question..."
    } | ConvertTo-Json)

Write-Host "Evaluation:"
Write-Host "  Score: $($response.evaluation.score)"
Write-Host "  XP: $($response.evaluation.xp)"
Write-Host "  Correct: $($response.evaluation.correct)"
Write-Host "  Explanation: $($response.evaluation.explanation)"
Write-Host "`nNext Question:`n$($response.next_question.text)`n"

# 5. Check status
$status = Invoke-RestMethod -Uri "http://localhost:8000/api/agent/session/$sessionId/status/" -Headers $headers
Write-Host "Session Progress: $($status.current_question_index)/$($status.total_questions)"
Write-Host "Total XP: $($status.total_xp)"
```

#### Option B: Using cURL (if you prefer)

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your_email@example.com","password":"your_password"}' \
  | jq -r '.access')

# 2. Get documents
DOC_ID=$(curl http://localhost:8000/api/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[0].id')

# 3. Start session
SESSION=$(curl -X POST http://localhost:8000/api/agent/session/start/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_ID\",\"language\":\"tanglish\"}")

echo $SESSION | jq '.first_question.text'
SESSION_ID=$(echo $SESSION | jq -r '.session_id')

# 4. Submit answer
curl -X POST http://localhost:8000/api/agent/session/$SESSION_ID/respond/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"My answer here"}' \
  | jq '{score:.evaluation.score, xp:.evaluation.xp, next:.next_question.text}'

# 5. Check status
curl http://localhost:8000/api/agent/session/$SESSION_ID/status/ \
  -H "Authorization: Bearer $TOKEN" \
  | jq '{progress:.current_question_index, total:.total_questions, xp:.total_xp}'
```

## 📚 What You Get

### New API Endpoints

1. **Start Session**: `POST /api/agent/session/start/`
   - Creates session with 10 structured questions
   - Returns first question in Tanglish
   
2. **Respond**: `POST /api/agent/session/<id>/respond/`
   - Submits user answer or question
   - Classifies intent automatically
   - Returns evaluation with XP
   - Provides next question
   
3. **Status**: `GET /api/agent/session/<id>/status/`
   - Shows progress and total XP
   
4. **Toggle Language**: `POST /api/agent/session/<id>/language/`
   - Switch between Tanglish and English

### Key Features

- ✨ **Intent Classification**: Automatically detects if user is answering, asking, or both
- 📝 **Structured Questions**: 7 archetypes (Concept Unfold, Critical Reversal, etc.)
- 🎮 **Gamification**: XP points (1-100) per question
- 🇮🇳 **Tanglish Support**: Native Tamil words in Latin script
- 📊 **SWOT Insights**: Automatic analysis after session completion
- 🔄 **Language Toggle**: Switch between Tanglish and English anytime

### Example Question Format

```json
{
  "text": "RLC circuit la resonance nadakkum bodhu current-um voltage-um epadi phase la irukkum? Simple-a sollu.",
  "question_id": "q_abc123",
  "archetype": "Concept Unfold",
  "difficulty": "easy"
}
```

### Example Evaluation Format

```json
{
  "score": 0.85,
  "xp": 75,
  "correct": true,
  "explanation": "Correct! Resonance la current-um voltage-um same phase la irukkum.",
  "confidence": 0.9,
  "followup_action": "none"
}
```

## 📖 Full Documentation

- **Implementation Details**: See `TANGLISH_AGENT_IMPLEMENTATION.md`
- **Migration Steps**: See `MIGRATION_GUIDE.md`
- **Summary**: See `IMPLEMENTATION_SUMMARY.md`

## ✅ What's Safe

- ✅ Existing tutoring flow unchanged
- ✅ All old endpoints still work
- ✅ New features use separate URLs (`/api/agent/...`)
- ✅ Backward compatible migrations

## 🎯 Next Steps

1. Test the API endpoints above
2. Review evaluation results
3. Complete a full session (10 questions)
4. Check insights generation
5. Integrate with your frontend

## 💡 Tips

- Use `language: "tanglish"` for Tamil-English mix
- Use `language: "english"` for pure English
- XP ranges: 80-100 (excellent), 60-79 (good), 40-59 (okay), 20-39 (needs work), 1-19 (incorrect)
- Each session has 10 questions by default
- Insights auto-generate after completing all questions

## 🐛 Troubleshooting

**No questions generated?**
- Check document is processed (status='completed')
- Verify Pinecone has vectors for your user

**Intent classifier not working?**
- Check LLM_API_KEY in `.env`
- Fallback rule will activate automatically

**Low XP scores?**
- XP is calculated from score (0.0-1.0)
- Partial credit is given for partial correctness

## 📞 Need Help?

1. Run: `python test_tanglish_agent.py`
2. Check Django logs
3. Check Sentry for errors
4. Review `MIGRATION_GUIDE.md` troubleshooting section

---

**Ready to go!** 🚀 Start testing the agent now.
