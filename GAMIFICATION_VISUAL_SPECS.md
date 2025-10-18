# Frontend Gamification - Visual Design Specifications

## Component Overview

### 1. StreakWidget (Dashboard Header)

**Location:** Top-right corner of Home page header, between profile button and library button

**Visual Specifications:**
```
Dimensions: Auto height, min-width 80px
Background: Linear gradient from #FED7AA (orange-100) to #FECACA (red-100)
Border-radius: 8px (rounded-lg)
Padding: 8px 12px
Shadow: sm (subtle shadow), md on hover
```

**Elements:**
- **Icon:** Flame from lucide-react
  - Size: 20px
  - Color: #F97316 (orange-500) when active, #9CA3AF (gray-400) when zero
  - Fill: currentColor when active, none when zero
- **Number:** Current streak count
  - Font-size: 18px (text-lg)
  - Font-weight: bold
  - Color: #1F2937 (gray-800)
- **Active Indicator:** Pulsing dot (top-right corner)
  - Size: 12px
  - Color: #F97316 (orange-500)
  - Animation: ping (built-in Tailwind)

**States:**
- **Active (streak > 0):** Flame filled, orange color, pulsing indicator visible
- **Inactive (streak = 0):** Flame outline, gray color, no pulsing indicator
- **Hover:** Slight scale increase, deeper shadow
- **Loading:** Pulse animation on entire widget

**Animations:**
- **New Milestone:** 2-second pulse animation + scale to 105%
- **Click:** Opens StreakModal with fade-in transition

---

### 2. StreakModal

**Layout:** Full-screen overlay (fixed positioning)

**Modal Dimensions:**
```
Width: 100%, max-width 28rem (448px)
Background: White
Border-radius: 16px (rounded-2xl)
Padding: 24px
Shadow: 2xl (prominent shadow)
```

**Sections:**

#### Header
- **Icon Circle:**
  - Size: 48px
  - Background: Gradient from #FB923C (orange-400) to #EF4444 (red-500)
  - Icon: TrendingUp (24px, white)
- **Title:** "Your Streak"
  - Font-size: 20px (text-xl)
  - Font-weight: bold
- **Subtitle:** "Keep learning daily!"
  - Font-size: 14px (text-sm)
  - Color: #6B7280 (gray-500)

#### Current Streak Display
```
Background: Gradient from #FFF7ED (orange-50) to #FEF2F2 (red-50)
Border-radius: 12px
Padding: 24px
Text-align: center
```
- **Number:** 
  - Font-size: 60px (text-6xl)
  - Font-weight: bold
  - Gradient text: orange-500 to red-500
- **Label:** "Day Streak 🔥"
  - Font-size: 16px
  - Font-weight: medium
  - Color: #4B5563 (gray-600)

#### New Milestone Banner (conditional)
```
Background: #FFFBEB (yellow-50)
Border: 2px solid #FCD34D (yellow-300)
Border-radius: 12px
Padding: 16px
Animation: bounce (2 seconds)
```
- **Icon:** Trophy (32px, #CA8A04 yellow-600)
- **Text:** "New Milestone Unlocked!"
- **Milestone Name:** From MILESTONE_BADGES

#### Progress Bar
- **Container:**
  - Height: 12px
  - Background: #E5E7EB (gray-200)
  - Border-radius: 9999px (full)
- **Fill:**
  - Background: Gradient orange-400 to red-500
  - Transition: width 500ms ease-out

#### Earned Milestones Grid
- **Layout:** 2-column grid, 12px gap
- **Milestone Card:**
  ```
  Background: Per-milestone color (10% opacity)
  Border: 1px, milestone color
  Border-radius: 8px
  Padding: 12px
  ```
  - **Icon:** Emoji from MILESTONE_BADGES (24px)
  - **Name:** Badge name (14px, bold)
  - **Label:** e.g., "Bronze (7)" (12px, gray-500)

#### Footer Tip
```
Background: #EFF6FF (blue-50)
Border-radius: 8px
Padding: 16px
```
- **Text:** "💡 Pro Tip: ..." (12px, #1E3A8A blue-900)

---

### 3. BatchWidget (Profile Popup)

**Location:** Inside UserProfilePopup, below user info, above member-since section

**Visual Specifications:**
```
Dimensions: Full width
Background: Linear gradient per batch (135deg)
  - Bronze: #CD7F3215 to #F4A46030
  - Silver: #C0C0C015 to #E8E8E830
  - Gold: #FFD70015 to #FFF8DC30
  - Platinum: #E5E4E215 to #F5F5F530
Border-radius: 16px (rounded-2xl)
Padding: 24px
Shadow: lg, xl on hover
```

**Elements:**

#### Header Row
- **Batch Icon Circle:**
  - Size: 56px
  - Background: Batch color with 30% opacity
  - Shadow: md
  - Content: Emoji from BATCH_COLORS (32px)
- **Title:** "{Batch} Batch"
  - Font-size: 18px (text-lg)
  - Font-weight: bold
- **Subtitle:** "Progress to mastery"
  - Font-size: 12px (text-xs)
  - Color: #4B5563 (gray-600)
- **Award Icon:** 24px, batch primary color

#### Stars Display
- **Layout:** Horizontal flex, 12px gap, centered
- **Star Icon:**
  - Size: 32px
  - Stroke-width: 2
  - Filled: #FBBF24 (yellow-400), fill currentColor
  - Empty: #D1D5DB (gray-300), no fill
- **Animation (new star):**
  - Bounce animation (500ms)
  - Scale to 125%

#### XP Progress Section
- **Label Row:**
  - "XP to next star" (14px, medium, gray-700)
  - "X / Y" (14px, bold, gray-900)
- **Progress Bar:**
  - Height: 8px
  - Background: White with 50% opacity
  - Fill: Linear gradient (batch primary to secondary)
  - Border-radius: 9999px
  - Transition: width 500ms ease-out

#### Next Batch Info (conditional)
```
Background: White with 80% opacity
Border-radius: 8px
Padding: 12px
Text-align: center
```
- **Text:** "🎉 All stars earned! Keep earning XP to advance to {Next Batch}"
- **Font-size:** 12px (text-xs)
- **Color:** #4B5563 (gray-600)

#### Footer Tip
```
Background: #EFF6FF (blue-50)
Border-radius: 8px
Padding: 12px
Margin-top: 16px
```
- **Text:** "💡 Earn XP by completing tests. Each star represents your progress!"
- **Font-size:** 12px (text-xs)
- **Color:** #1E3A8A (blue-900)

---

## Color Palette Reference

### Streak System (Warm Colors)
```
Primary: #F97316 (orange-500)
Secondary: #EF4444 (red-500)
Background Light: #FED7AA (orange-100)
Background Dark: #FECACA (red-100)
Text: #1F2937 (gray-800)
```

### Batch System (Cool Colors per Level)

**Bronze:**
```
Primary: #CD7F32
Secondary: #F4A460
Icon: 🥉
```

**Silver:**
```
Primary: #C0C0C0
Secondary: #E8E8E8
Icon: 🥈
```

**Gold:**
```
Primary: #FFD700
Secondary: #FFF8DC
Icon: #🥇
```

**Platinum:**
```
Primary: #E5E4E2
Secondary: #F5F5F5
Icon: 💎
```

---

## Animation Specifications

### Pulse Animation (New Milestone)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
duration: 2s
timing-function: cubic-bezier(0.4, 0, 0.6, 1)
```

### Bounce Animation (New Star/Milestone)
```css
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-25%); }
}
duration: 1s
timing-function: cubic-bezier(0.8, 0, 1, 1)
```

### Scale Animation (Active Element)
```css
transform: scale(1.05);
transition: all 300ms ease-in-out;
```

### Ping Animation (Active Indicator)
```css
@keyframes ping {
  75%, 100% { transform: scale(2); opacity: 0; }
}
duration: 1s
timing-function: cubic-bezier(0, 0, 0.2, 1)
iteration-count: infinite
```

---

## Responsive Behavior

### Mobile (< 768px)
- **StreakWidget:** Full width in header row
- **StreakModal:** Full screen with 16px padding
- **BatchWidget:** Full width, slightly reduced padding (16px)

### Desktop (≥ 768px)
- **StreakWidget:** Fixed position in header
- **StreakModal:** Centered, max-width 448px
- **BatchWidget:** Max-width in profile popup

---

## Accessibility Requirements

### Keyboard Navigation
- All interactive elements must be tabbable
- Escape key closes modals
- Enter/Space activates buttons

### Screen Reader Support
```html
<!-- StreakWidget -->
<button aria-label="Current streak: 12 days">...</button>

<!-- StreakModal -->
<div role="dialog" aria-labelledby="streak-title">...</div>

<!-- Stars -->
<div aria-label="3 of 5 stars earned">...</div>
```

### Focus States
- Visible focus ring (2px, blue-500)
- High contrast in all states
- Minimum touch target: 44x44px

---

## Icon Reference (lucide-react)

Used icons:
- `Flame` - Streak widget
- `TrendingUp` - Streak modal header
- `Trophy` - Milestones
- `Star` - Batch stars
- `Award` - Batch header
- `X` - Close button

All icons use consistent sizing and stroke-width (2) for visual harmony.

---

## Testing Checklist

### Visual Testing
- [ ] StreakWidget renders in correct position
- [ ] Colors match specifications
- [ ] Animations smooth on all devices
- [ ] Modal overlay darkens background
- [ ] BatchWidget gradients display correctly
- [ ] Stars animate when unlocked
- [ ] Responsive on mobile/tablet/desktop

### Interaction Testing
- [ ] Click streak opens modal
- [ ] Close modal with X button
- [ ] Close modal with overlay click
- [ ] Progress bars animate smoothly
- [ ] New milestone banner appears
- [ ] Tooltips show on hover

### Data Testing
- [ ] API data displays correctly
- [ ] Loading states show while fetching
- [ ] Error states handled gracefully
- [ ] Real-time updates after test completion

---

**Design System Version:** 1.0  
**Framework:** React + TypeScript + Tailwind CSS  
**Icons:** lucide-react  
**Animations:** Tailwind built-in + custom CSS
