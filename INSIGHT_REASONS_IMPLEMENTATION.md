# BoostMe Insight Reasons Implementation Summary

## Overview
Added "reason" explanations for each BoostMe insight zone (Focus, Steady, Edge) so users can understand WHY they received specific insights. Frontend displays an info button (i) in each zone that shows the reasons in a popover.

## Changes Made

### 1. Backend - Database Schema
**File:** `backend/api/models.py`
- Added 3 new JSONField columns to `SessionInsight` model:
  - `focus_zone_reasons` (nullable array of 2 strings)
  - `steady_zone_reasons` (nullable array of 2 strings)
  - `edge_zone_reasons` (nullable array of 2 strings)

**Migration:** `api/migrations/0015_sessioninsight_edge_zone_reasons_and_more.py`
- Applied successfully
- Backward compatible (nullable fields)

### 2. Backend - LLM Prompt & Parser
**File:** `backend/api/gemini_client.py`

**Changes to `generate_boostme_insights()`:**
- Updated system prompt to request reason arrays for each zone
- Prompt instructs LLM to:
  - Reference specific questions (e.g., "Question 2 and 5 showed confusion")
  - Cite performance patterns
  - Keep reasons concise (<= 30 words)
- Added validation for reason arrays (must be array of 2 strings)
- Auto-generates fallback reasons if LLM doesn't provide them
- Updated docstring to document new return format

**Changes to `_generate_fallback_boostme_insights()`:**
- Now generates reason arrays based on QA statistics
- Reasons reference actual scores and patterns (e.g., "5 questions scored below 50%")

### 3. Backend - Persistence
**File:** `backend/api/agent_flow.py`
- Updated `_generate_session_insights()` to save reason arrays to DB:
  ```python
  "focus_zone_reasons": boostme_insights.get('focus_zone_reasons', []),
  "steady_zone_reasons": boostme_insights.get('steady_zone_reasons', []),
  "edge_zone_reasons": boostme_insights.get('edge_zone_reasons', [])
  ```

### 4. Backend - API Response
**File:** `backend/api/views/tutoring_views.py`
- Updated `SessionInsightsView.get()` to include reason arrays in response:
  ```python
  "insights": {
      "focus_zone": insight.focus_zone,
      "focus_zone_reasons": insight.focus_zone_reasons or [],
      "steady_zone": insight.steady_zone,
      "steady_zone_reasons": insight.steady_zone_reasons or [],
      "edge_zone": insight.edge_zone,
      "edge_zone_reasons": insight.edge_zone_reasons or []
  }
  ```
- Safely handles null values for backward compatibility

### 5. Frontend - BoostMe UI
**File:** `frontend/src/pages/BoostMe.tsx`

**Interface Updates:**
- Added reason fields to `Insights` interface
- Parse reasons from API response

**UI Changes:**
- Added Info icon button in each zone card header
- Implemented popover showing reasons on click
- Added click-outside-to-close behavior
- Added fade-in animation for smooth appearance
- Gracefully handles missing reasons (hides button if no reasons)

**File:** `frontend/src/index.css`
- Added `@keyframes fadeIn` animation
- Added `.animate-fadeIn` utility class

### 6. Frontend - Question Numbering Fix (Bonus)
**File:** `frontend/src/pages/TutoringChat.tsx`

**Fixed missing question numbers in chat:**
- Added `questionNumber` and `totalQuestions` to `Message` interface
- Parse these fields from API responses
- Display badge above each question: `Q.X/Y`
- Styled with blue background for visibility
- Only shows for bot messages (questions)

## API Response Format

### Before
```json
{
  "insights": {
    "focus_zone": ["Weak area 1", "Weak area 2"],
    "steady_zone": ["Strong area 1", "Strong area 2"],
    "edge_zone": ["Edge area 1", "Edge area 2"]
  }
}
```

### After (backward compatible)
```json
{
  "insights": {
    "focus_zone": ["Weak area 1", "Weak area 2"],
    "focus_zone_reasons": ["Low scores in Q2 and Q5", "Concept confusion observed"],
    "steady_zone": ["Strong area 1", "Strong area 2"],
    "steady_zone_reasons": ["Correct in Q1, Q3, Q7", "Consistent performance"],
    "edge_zone": ["Edge area 1", "Edge area 2"],
    "edge_zone_reasons": ["Nearly correct in Q4", "Right approach, minor errors"]
  }
}
```

## Testing
**File:** `backend/api/tests/test_insights_with_reasons.py`

**Test Coverage:**
1. Valid LLM response with reasons → correctly parsed
2. Missing reasons → fallback generates reasons
3. Fallback generator produces meaningful reasons
4. Empty QA records → fallback provides generic reasons
5. DB persistence → reasons saved and retrieved correctly
6. Backward compatibility → null reasons don't break system

**Run tests:**
```bash
cd backend
python manage.py test api.tests.test_insights_with_reasons
```

## Deployment Checklist

### Pre-deployment
- [x] Database migration created and tested locally
- [x] All tests passing
- [x] Frontend builds without errors
- [x] Backward compatibility verified

### Deployment Steps
1. **Backend:**
   ```bash
   cd backend
   python manage.py migrate
   python manage.py test
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm run build
   ```

3. **Verify:**
   - Complete a tutoring session
   - Check BoostMe page shows insights with (i) buttons
   - Click (i) button → should show reasons
   - Check question numbers appear in chat (Q.1/10, Q.2/10, etc.)

### Rollback Plan
If issues occur:
1. Reasons are nullable - existing insights will still work
2. Frontend gracefully hides (i) button if no reasons
3. Can rollback migration: `python manage.py migrate api 0014`

## Benefits
1. **User transparency:** Users understand why they got specific insights
2. **Actionable feedback:** Reasons reference specific questions/patterns
3. **Trust building:** Showing reasoning increases confidence in AI
4. **Debugging:** Helps identify when LLM provides poor insights
5. **Backward compatible:** Old sessions without reasons still work

## Example UI Flow
1. User completes tutoring session
2. Navigate to BoostMe page
3. See 3 zone cards (Focus/Steady/Edge)
4. Each card has small (i) icon in top-right
5. Click (i) → popover appears with 2 bullet points explaining why
6. Click outside or X → popover closes

## Question Numbering Fix
- Questions now show "Q.1/10", "Q.2/10" etc. above each question
- Small blue badge, non-intrusive
- Only shows for questions (not user answers)
- Helps users track progress through session
