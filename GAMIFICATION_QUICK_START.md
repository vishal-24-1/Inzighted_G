# Gamification System - Quick Start Guide

## 🚀 What's New?

Two independent gamification systems have been added:

### 1. 🔥 Streak System (Top Dashboard)
- **What it tracks:** Consecutive days of learning
- **How it works:** Complete one test per day to maintain your streak
- **Rewards:** Earn permanent milestone badges (Bronze, Silver, Gold, Platinum, Diamond)
- **Reset behavior:** Streak resets if you miss a day, but earned badges stay forever

### 2. 🏆 Batch System (Profile)
- **What it tracks:** Overall XP progress and mastery
- **How it works:** Earn XP from tests → unlock stars → advance batch levels
- **Progression:** 5 stars per batch (Bronze → Silver → Gold → Platinum)
- **XP Calculation:** Average XP across all your tests

---

## 📱 Where to Find Them

### Streak Widget
- **Location:** Top-right of dashboard (next to library icon)
- **Appearance:** Orange flame icon with your current streak number
- **Click:** Opens modal showing earned badges and progress to next milestone

### Batch Widget
- **Location:** Profile popup (click user icon)
- **Appearance:** Badge icon with 5 stars and XP progress bar
- **Shows:** Current batch level, stars earned, XP to next star

---

## 🎮 How to Use

### Earning Streak Progress
1. Complete any tutoring test
2. Your streak increments (if it's a new day)
3. Reach milestones to earn permanent badges:
   - 🥉 Bronze (7 days)
   - 🥈 Silver (15 days)
   - 🥇 Gold (30 days)
   - 💎 Platinum (45 days)
   - 💠 Diamond (100 days)

**Important:** Only one test per day counts toward streak. Multiple tests on the same day won't increase your streak but will still earn XP!

### Earning Batch Progress
1. Complete tutoring tests and answer questions
2. Earn XP based on answer quality
3. XP unlocks stars (200 XP per star by default)
4. Earn all 5 stars to advance to next batch level

**Note:** Your XP is calculated as the average across all tests, ensuring fair progression regardless of how many tests you've taken.

---

## 🎨 Visual Differences

| Feature | Streak | Batch |
|---------|--------|-------|
| **Icon** | 🔥 Flame | 🏆 Badge |
| **Colors** | Warm (orange/red) | Cool (blue/teal) |
| **Location** | Dashboard header | Profile modal |
| **Label** | "X Day Streak" | "X Batch" |

---

## ❓ FAQ

**Q: What happens if I miss a day?**  
A: Your streak resets to 0, but all earned milestone badges remain permanently in your collection!

**Q: Can I complete multiple tests per day?**  
A: Yes! But only the first test counts toward your daily streak. All tests earn XP for batch progression.

**Q: How is XP calculated?**  
A: XP is the average of all your test scores. This ensures fair progression whether you've taken 10 tests or 100 tests.

**Q: What happens when I earn all 5 stars?**  
A: You advance to the next batch level (Bronze → Silver → Gold → Platinum) and start earning stars in the new batch.

**Q: Do batch levels ever reset?**  
A: No! Your batch progress is permanent and never resets.

**Q: Can I see my progress history?**  
A: Click the streak icon to see all earned milestone badges and progress toward the next one.

---

## 🎯 Tips for Success

### Maintaining Your Streak
- Set a daily reminder to complete at least one test
- Even a short 5-minute session counts!
- Plan ahead for busy days

### Maximizing XP
- Answer questions thoroughly for higher evaluation scores
- Review feedback to improve future answers
- Consistency matters more than speed

### Earning Badges
- Focus on daily consistency for streak badges
- Earn quality XP for batch progression
- Celebrate each milestone - they're permanent achievements!

---

## 🔧 Technical Details (For Developers)

### API Endpoint
```
GET /api/progress/
Authorization: Bearer {token}
```

Response:
```json
{
  "streak": {
    "current": 12,
    "earned_milestones": ["Bronze (7)"],
    "next_milestone": 15
  },
  "batch": {
    "current_batch": "Silver",
    "current_star": 2,
    "xp_points": 450.5,
    "xp_to_next_star": 150
  }
}
```

### React Components
- `<StreakWidget />` - Dashboard streak display
- `<StreakModal />` - Detailed streak popup
- `<BatchWidget />` - Profile batch display

### Backend Integration
- Progress updated automatically after each test evaluation
- Idempotent: won't double-count same evaluation
- Atomic transactions prevent race conditions
- Failed updates don't break tutoring flow

---

## 🐛 Known Issues & Limitations

1. **Timezone:** All dates use server UTC time. Future: add user timezone support.
2. **Animations:** Some animations may vary by browser/device performance.
3. **Historical Data:** Existing users start with streak = 0. Future: backfill option.

---

## 📞 Support

Having issues? Check:
1. Browser console for errors
2. Network tab for API failures
3. Verify you're logged in with valid token

Contact: support@inzighted.com

---

**Last Updated:** October 17, 2025  
**Version:** 1.0.0
