# 🚀 Quick Start: Testing the Onboarding Feature

## How to Test the Onboarding Flow

### 1. Start the Development Server

```powershell
# Terminal 1: Start backend
cd backend
python manage.py runserver

# Terminal 2: Start frontend
cd frontend
npm start
```

### 2. Test as First-Time User

**Option A: Register a new account**
1. Go to http://localhost:3000/register
2. Create a new account
3. After successful registration, you'll be redirected to Home
4. The Welcome Screen should appear automatically
5. Click "Start Tour" to see the interactive guide

**Option B: Login with existing account (after clearing data)**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Run: `localStorage.clear()`
4. Refresh the page
5. Login with your credentials
6. Welcome screen should appear

### 3. Test Tour Navigation

**During the tour:**
- ✅ Click **"Next"** to move to next step
- ✅ Click **"Back"** to go to previous step
- ✅ Click **"X"** or **"Skip Tour"** to exit anytime
- ✅ Complete all 7 steps to reach "Get Started" button
- ✅ Watch the spotlight highlight each feature

**Tour Steps:**
1. Welcome message (center overlay)
2. Profile button (top left)
3. Streak widget (top right)
4. Library button (top right)
5. Boost Me card (center)
6. Chat input (bottom)
7. Mobile dock (bottom navigation)

### 4. Verify Persistence

**After completing tour:**
1. Refresh the page → Onboarding should NOT show again
2. Logout and login → Onboarding should NOT show again
3. Open DevTools → Application → Local Storage
4. Look for `inzighted_onboarding_completed` key
5. You should see your user ID with completion timestamp

### 5. Reset and Test Again

**Method 1: Browser Console**
```javascript
// Clear onboarding for specific user
const userId = "your-user-id"; // Get from user object
const data = JSON.parse(localStorage.getItem('inzighted_onboarding_completed') || '{}');
delete data[userId];
localStorage.setItem('inzighted_onboarding_completed', JSON.stringify(data));
location.reload();
```

**Method 2: Clear All Storage**
```javascript
localStorage.clear();
location.reload();
```

### 6. Test Responsive Design

**Mobile View (< 768px):**
- Press F12 → Toggle device toolbar (Ctrl+Shift+M)
- Select iPhone or Android device
- Test tour navigation with touch gestures
- Verify tooltip sizes are appropriate

**Tablet View (768px - 1024px):**
- Resize browser window to tablet size
- Check layout adjustments
- Test tour tooltips

**Desktop View (> 1024px):**
- Full screen browser
- Check all animations
- Verify sidebar doesn't block tour

### 7. Test Skip Functionality

**Test both skip options:**

**Skip from Welcome Screen:**
1. Clear localStorage
2. Login/Register
3. Click "Skip for Now" on welcome screen
4. Should go directly to Home without tour
5. Verify completion is saved in localStorage

**Skip from Tour:**
1. Clear localStorage
2. Login/Register
3. Click "Start Tour"
4. Click X button or "Skip Tour" during any step
5. Should exit tour immediately
6. Verify completion is saved

### 8. Test Edge Cases

**Empty State:**
- Test when user has no documents
- Tour should still work
- Elements should be present

**Mobile Dock:**
- Navigate between Home and Boost pages
- Onboarding should only show once on Home

**Concurrent Sessions:**
- Login on two different browsers
- Complete onboarding on one
- Refresh the other → Should still show (different localStorage)

## Troubleshooting

### Onboarding Doesn't Show
```javascript
// Check storage
console.log(localStorage.getItem('inzighted_onboarding_completed'));

// Check user ID
const user = JSON.parse(localStorage.getItem('user')); // If stored
console.log(user?.id);

// Force clear
localStorage.removeItem('inzighted_onboarding_completed');
```

### Tour Targets Not Found
- Check browser console for errors
- Verify elements exist: `document.querySelector('[aria-label="Open profile"]')`
- Some elements may be conditionally rendered

### Animations Lag
- Check CPU usage
- Disable other browser extensions
- Test in Incognito mode
- Reduce motion in OS settings

## Development Commands

```powershell
# Install dependencies (if not already done)
cd frontend
npm install react-joyride framer-motion

# Run with hot reload
npm start

# Build for production
npm run build

# Run tests (when added)
npm test
```

## Browser DevTools Tips

**Watch localStorage in real-time:**
1. Open DevTools (F12)
2. Application tab → Local Storage
3. Select your domain
4. Watch `inzighted_onboarding_completed` key

**Debug tour steps:**
```javascript
// In Console during tour
// Check current Joyride state
window.__REACT_JOYRIDE__ // If available
```

**Performance monitoring:**
1. DevTools → Performance tab
2. Record during welcome screen animation
3. Check for 60fps frame rate
4. Look for long tasks or layout shifts

## Expected User Experience

### First-Time User Flow (Happy Path)
```
1. User logs in → 0s
2. Welcome screen appears → 0.3s (with animation)
3. User reads welcome → 5-10s
4. User clicks "Start Tour" → 0.2s transition
5. Tour begins → First tooltip appears
6. User navigates through 7 steps → 60-90s
7. User clicks "Get Started" → Tour completes
8. Home page is now accessible
Total time: ~90-120 seconds
```

### Quick Skip Flow
```
1. User logs in → 0s
2. Welcome screen appears → 0.3s
3. User clicks "Skip for Now" → Immediate
Total time: ~1-2 seconds
```

## Visual Verification Checklist

- [ ] Logo bounces in with rotation
- [ ] Sparkle appears on logo
- [ ] Feature cards stagger in
- [ ] Gradient backgrounds render smoothly
- [ ] Buttons have hover effects
- [ ] Tour spotlight dims background
- [ ] Progress dots animate
- [ ] Tooltips slide in smoothly
- [ ] Mobile dock is visible
- [ ] No layout shifts or jumps

## Ready for Production?

Before deploying:

1. ✅ All tour targets exist and are stable
2. ✅ localStorage works across browsers
3. ✅ Responsive design tested on real devices
4. ✅ Accessibility tested with screen reader
5. ✅ Performance is acceptable (< 3s to interactive)
6. ✅ Skip functionality works everywhere
7. ✅ Documentation is up to date
8. ✅ Analytics events tracked (if applicable)

---

**Need Help?** Check `ONBOARDING_FEATURE.md` for detailed documentation.
