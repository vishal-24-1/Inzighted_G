# Gamification System - Deployment Checklist

## ✅ Pre-Deployment Verification

### Backend Checklist

- [x] **Database Migration Created**
  - File: `backend/api/migrations/0012_evaluatorresult_progress_processed_and_more.py`
  - Fields added to User model
  - Field added to EvaluatorResult model

- [x] **Migration Applied**
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```

- [x] **Core Modules Created**
  - [x] `backend/api/progress.py` - Progress calculation logic
  - [x] `backend/api/progress_views.py` - API endpoints
  - [x] `backend/api/serializers.py` - ProgressSerializer added
  - [x] `backend/api/tests/test_progress.py` - Unit tests

- [x] **Integration Points Updated**
  - [x] `backend/api/agent_flow.py` - Progress update hook in `_evaluate_answer()`
  - [x] `backend/api/urls.py` - Progress endpoint registered

- [ ] **Tests Passing**
  ```bash
  python manage.py test api.tests.test_progress
  ```
  _Note: Skipped due to DB permissions. Manual testing recommended._

- [x] **Configuration Ready**
  - Default thresholds in `progress.py`
  - Optional overrides in `settings.py`

### Frontend Checklist

- [x] **Types Defined**
  - File: `frontend/src/types/progress.ts`
  - Interfaces: StreakInfo, BatchInfo, ProgressResponse
  - Constants: MILESTONE_BADGES, BATCH_COLORS

- [x] **API Service Added**
  - File: `frontend/src/utils/api.ts`
  - Functions: getProgress(), refreshProgress()

- [x] **Components Created**
  - [x] `frontend/src/components/StreakWidget.tsx`
  - [x] `frontend/src/components/StreakModal.tsx`
  - [x] `frontend/src/components/BatchWidget.tsx`

- [x] **Integration Complete**
  - [x] StreakWidget added to Home.tsx header
  - [x] BatchWidget added to UserProfilePopup.tsx

- [ ] **Build Successful**
  ```bash
  cd frontend
  npm run build
  ```

- [ ] **No TypeScript Errors**
  ```bash
  npm run build
  # Check for compilation errors
  ```

---

## 🧪 Testing Checklist

### Backend Testing

#### Unit Tests
- [ ] Test streak increment logic
- [ ] Test streak reset logic
- [ ] Test milestone persistence
- [ ] Test XP averaging calculation
- [ ] Test star unlock thresholds
- [ ] Test batch progression
- [ ] Test idempotence (progress_processed flag)

#### Integration Tests
- [ ] Complete a tutoring session
- [ ] Verify progress updates in database
- [ ] Call `/api/progress/` endpoint
- [ ] Verify response format
- [ ] Test with multiple tests same day
- [ ] Test with missed day (streak reset)

### Frontend Testing

#### Component Tests
- [ ] StreakWidget renders correctly
- [ ] StreakModal opens/closes
- [ ] BatchWidget displays correct data
- [ ] Loading states show properly
- [ ] Error states handled gracefully

#### Visual Tests
- [ ] Colors match specifications
- [ ] Icons display correctly
- [ ] Animations smooth
- [ ] Responsive on mobile
- [ ] Responsive on tablet
- [ ] Responsive on desktop

#### Interaction Tests
- [ ] Click streak widget → modal opens
- [ ] Click modal overlay → modal closes
- [ ] Click X button → modal closes
- [ ] Progress bars animate
- [ ] Stars fill with animation
- [ ] New milestone banner appears

#### Data Flow Tests
- [ ] Complete test → progress updates
- [ ] Refresh page → data persists
- [ ] Multiple tabs → data syncs
- [ ] Network error → graceful handling

---

## 🚀 Deployment Steps

### Step 1: Backup Database
```bash
# Production database backup
pg_dump -U username -d database_name > backup_$(date +%Y%m%d).sql
```

### Step 2: Deploy Backend

```bash
cd backend

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies (if any new)
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart server
systemctl restart gunicorn  # or your deployment method
```

### Step 3: Deploy Frontend

```bash
cd frontend

# Pull latest code
git pull origin main

# Install dependencies
npm install

# Build production bundle
npm run build

# Deploy to hosting (example: copy to server)
rsync -avz build/ user@server:/var/www/app/

# Or use your deployment method (Netlify, Vercel, etc.)
```

### Step 4: Verify Deployment

#### Backend Verification
```bash
# Check migrations applied
python manage.py showmigrations api

# Check API endpoint
curl -H "Authorization: Bearer TOKEN" https://your-domain.com/api/progress/
```

#### Frontend Verification
- [ ] Visit homepage
- [ ] Check StreakWidget visible
- [ ] Open profile popup
- [ ] Check BatchWidget visible
- [ ] Complete a test
- [ ] Verify progress updates

---

## 🔍 Post-Deployment Monitoring

### Metrics to Watch

#### Backend Metrics
- [ ] `/api/progress/` response time < 200ms
- [ ] Progress update success rate > 99%
- [ ] Database query performance
- [ ] Sentry error rate (should be 0)

#### Frontend Metrics
- [ ] Component render time
- [ ] API call success rate
- [ ] User engagement with gamification
- [ ] Animation performance

### Logging Points

Check logs for:
```python
# Backend
logger.info("Progress updated: {progress_update}")
logger.error("Progress update failed: {error}")

# Frontend
console.log("Progress fetched:", progress)
console.error("Failed to fetch progress:", error)
```

---

## 🐛 Rollback Plan

If issues arise:

### Backend Rollback
```bash
# Revert migration
python manage.py migrate api 0011  # Previous migration number

# Restart server
systemctl restart gunicorn
```

### Frontend Rollback
```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Rebuild and deploy
npm run build
# Deploy previous build
```

### Database Cleanup (if needed)
```sql
-- Remove progress fields (CAUTION: test in staging first)
ALTER TABLE api_user DROP COLUMN streak_current;
ALTER TABLE api_user DROP COLUMN streak_last_test_date;
-- ... etc
```

---

## 📊 Success Metrics

Track these KPIs post-launch:

### Engagement Metrics
- % of users with active streaks
- Average streak length
- Milestone badge distribution
- Batch progression rates

### Technical Metrics
- API endpoint latency
- Frontend load time
- Error rates
- Database query performance

### User Feedback
- Session completion rates
- Time spent per session
- Feature usage analytics
- User satisfaction surveys

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue: "Progress not updating after test"**
- Check: `progress_processed` flag in EvaluatorResult
- Check: Network logs for API calls
- Check: Server logs for exceptions

**Issue: "Streak shows 0 but I completed test today"**
- Check: Timezone consistency (server vs user)
- Check: `streak_last_test_date` value in database
- Verify: Test was evaluated (EvaluatorResult created)

**Issue: "XP not calculating correctly"**
- Check: `total_xp_sum` and `total_tests_taken` in database
- Verify: Division by zero protection
- Check: `evaluator_result.xp` has valid value

**Issue: "Frontend components not rendering"**
- Check: Browser console for errors
- Verify: API endpoint accessible
- Check: JWT token valid
- Clear: Browser cache and reload

### Debug Commands

```bash
# Check user progress data
python manage.py shell
>>> from api.models import User
>>> user = User.objects.get(email='test@example.com')
>>> user.streak_current, user.xp_points, user.batch_current

# Check evaluator results
>>> from api.models import EvaluatorResult
>>> EvaluatorResult.objects.filter(progress_processed=False).count()

# Manually trigger progress update
>>> from api.progress import update_on_test_completion
>>> result = EvaluatorResult.objects.last()
>>> update_on_test_completion(result.message.session.user, result)
```

---

## 📝 Documentation Links

- [GAMIFICATION_IMPLEMENTATION.md](./GAMIFICATION_IMPLEMENTATION.md) - Full technical documentation
- [GAMIFICATION_QUICK_START.md](./GAMIFICATION_QUICK_START.md) - User-facing guide
- [GAMIFICATION_VISUAL_SPECS.md](./GAMIFICATION_VISUAL_SPECS.md) - Design specifications

---

## ✨ Post-Launch Tasks

- [ ] Monitor error rates for first 24 hours
- [ ] Collect user feedback
- [ ] Analyze engagement metrics
- [ ] Plan v2 enhancements
- [ ] Document lessons learned

---

**Deployment Date:** ___________  
**Deployed By:** ___________  
**Version:** 1.0.0  
**Status:** ⏳ Pending / ✅ Deployed / ❌ Rolled Back
