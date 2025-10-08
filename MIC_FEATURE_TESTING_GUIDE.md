# Testing Guide: ChatGPT-Style Mic Feature

## Quick Test Steps

### Test 1: Multiple Voice Recordings Append ✅
**Expected:** Each recording adds to previous text

1. Open TutoringChat page in browser
2. Click mic button 🎤
3. Say "Hello teacher"
4. Click mic button again (stop recording)
5. **Verify:** "Hello teacher" appears in textarea
6. Click mic button again (new recording)
7. Say "I have a question"
8. Click mic button again (stop recording)
9. **Verify:** "Hello teacher I have a question" (both parts present)
10. Repeat steps 6-8 with more text
11. **Verify:** All recordings are accumulated

**Pass Criteria:** ✅ All recordings visible, no text lost

---

### Test 2: Textarea Dynamic Growth ✅
**Expected:** Height increases as content grows

1. Start with empty textarea
2. **Verify:** Height is ~44px (single line)
3. Click mic and record short text (1 line)
4. **Verify:** Height stays ~44px
5. Click mic and record more text (total 2 lines)
6. **Verify:** Height grows to ~66px
7. Click mic and record more text (total 3-4 lines)
8. **Verify:** Height grows to ~88-110px
9. Continue until text exceeds 200px
10. **Verify:** Height caps at 200px, scroll appears

**Pass Criteria:** ✅ Height adjusts smoothly without jumps

---

### Test 3: Manual Typing Integration ✅
**Expected:** Voice and typing work together

1. Type "Hello" manually in textarea
2. **Verify:** Text appears, height adjusts if needed
3. Click mic and record "teacher"
4. **Verify:** Result is "teacher" only (current bug or expected?)

**Note:** Current implementation replaces text when recording starts. If you want voice to append to typed text, we need to modify the logic.

**Pass Criteria:** ✅ User can edit text after recording

---

### Test 4: Height Reset After Send ✅
**Expected:** Textarea returns to original size

1. Record or type multiple lines (textarea grows)
2. **Verify:** Textarea is taller than 44px
3. Click Send button 📤
4. **Verify:** Message sent successfully
5. **Verify:** Textarea clears (empty)
6. **Verify:** Textarea height resets to 44px

**Pass Criteria:** ✅ Clean slate for next message

---

### Test 5: Enter Key Behavior ✅
**Expected:** Enter submits, Shift+Enter adds line

1. Type or record some text
2. Press **Enter** key
3. **Verify:** Message is sent immediately
4. Type or record new text
5. Press **Shift+Enter**
6. **Verify:** New line added, message NOT sent
7. Press **Enter** alone
8. **Verify:** Message sent

**Pass Criteria:** ✅ Keyboard shortcuts work correctly

---

### Test 6: Mic Button States ✅
**Expected:** Visual feedback for recording state

**Idle State:**
- Background: Gray (#E5E7EB)
- Icon: Mic 🎤
- Hover: Slightly darker, scale 1.05

**Recording State:**
- Background: Red (#EF4444)
- Icon: Mic 🎤 (white)
- Animation: Pulse effect
- Hover: No scale (pulsing already)

**Disabled State:**
- Background: Gray
- Opacity: 50%
- Cursor: not-allowed
- No interactions

**Pass Criteria:** ✅ Clear visual distinction between states

---

### Test 7: Send Button State ✅
**Expected:** Disabled when no text, enabled when text present

1. **Verify:** Send button disabled (50% opacity) when textarea empty
2. Type or record any text
3. **Verify:** Send button enabled (full color)
4. Clear all text (backspace/delete)
5. **Verify:** Send button disabled again

**Pass Criteria:** ✅ Button state matches content state

---

### Test 8: Loading State ✅
**Expected:** All inputs disabled during API call

1. Type or record a message
2. Click Send
3. **Verify:** During loading:
   - Textarea disabled (grayed out)
   - Mic button disabled
   - Send button disabled
4. Wait for response
5. **Verify:** All inputs re-enabled

**Pass Criteria:** ✅ No race conditions, smooth UX

---

### Test 9: Browser Compatibility 🌐

**Chrome/Edge:**
1. Test all features above
2. **Verify:** Voice recording works
3. **Verify:** No console errors

**Safari:**
1. Test all features above
2. **Verify:** Voice recording works (webkit prefix)
3. **Verify:** No console errors

**Firefox:**
1. Test all features above
2. **Note:** Voice may be limited or unavailable
3. **Verify:** Textarea and typing still work
4. **Verify:** Graceful degradation (mic button disabled)

**Pass Criteria:** ✅ Works in supported browsers, degrades gracefully

---

### Test 10: Mobile Behavior 📱

**Mobile Chrome/Safari:**
1. Open on mobile device
2. Click mic button
3. **Verify:** Mobile voice input activated
4. Speak into microphone
5. **Verify:** Text appears in textarea
6. **Verify:** Textarea grows appropriately
7. **Verify:** Buttons remain tappable
8. **Verify:** Keyboard appears when tapping textarea

**Pass Criteria:** ✅ Touch-friendly, no layout issues

---

## Edge Cases to Test

### Edge Case 1: Very Long Recording
**Scenario:** User records a very long message (>200px height)

**Steps:**
1. Click mic and record continuously for 30+ seconds
2. Stop recording
3. **Verify:** Textarea caps at 200px height
4. **Verify:** Scroll bar appears
5. **Verify:** User can scroll to see all text
6. **Verify:** Send button works correctly

**Expected:** ✅ No overflow, content accessible

---

### Edge Case 2: Rapid Mic Clicks
**Scenario:** User clicks mic button rapidly (double-click, spam)

**Steps:**
1. Click mic button very quickly (5+ times)
2. **Verify:** No crashes or errors
3. **Verify:** Recording state toggles correctly
4. **Verify:** No duplicate text inserted

**Expected:** ✅ Stable behavior, no glitches

---

### Edge Case 3: Recording Then Typing
**Scenario:** Mix voice and manual input

**Steps:**
1. Record "Hello" (stop recording)
2. **Current Behavior:** "Hello" in textarea
3. Manually type " world" at the end
4. **Current Behavior:** "Hello world"
5. Record "How are you"
6. **Current Behavior:** Only "How are you" (typed text lost)

**Note:** If you want typed text preserved, we need to adjust the logic.

**Expected:** Document current behavior or fix if needed

---

### Edge Case 4: Empty Recording
**Scenario:** User starts mic but doesn't speak

**Steps:**
1. Click mic (start recording)
2. Wait 5 seconds without speaking
3. Click mic (stop recording)
4. **Verify:** No text added (or empty string trimmed)
5. **Verify:** Textarea remains at previous state

**Expected:** ✅ No empty segments added

---

### Edge Case 5: Special Characters in Speech
**Scenario:** Speech recognition returns punctuation

**Steps:**
1. Record "Hello comma how are you question mark"
2. **Verify:** Text may include commas and punctuation
3. **Verify:** Textarea handles special characters correctly
4. **Verify:** Send works with special characters

**Expected:** ✅ No encoding issues

---

## Performance Tests

### Performance 1: Large Text Handling
**Test:** Paste or record 5000+ characters

**Steps:**
1. Copy large text (5000 characters)
2. Paste into textarea
3. **Verify:** Textarea renders without lag
4. **Verify:** Height caps at 200px
5. **Verify:** Smooth scrolling
6. **Verify:** Send works correctly

**Expected:** ✅ No performance degradation

---

### Performance 2: Height Calculation Speed
**Test:** Measure textarea resize time

**Steps:**
1. Open browser DevTools → Performance tab
2. Start recording
3. Record short text
4. Stop recording
5. **Verify:** Height calculation < 10ms
6. **Verify:** No jank or layout shift

**Expected:** ✅ Instant visual feedback

---

## Regression Tests (Existing Functionality)

### Regression 1: Message Sending ✅
**Verify:** Normal chat flow still works

**Steps:**
1. Type a message manually (no voice)
2. Click Send
3. **Verify:** Message appears in chat
4. **Verify:** API call succeeds
5. **Verify:** Response appears

**Pass Criteria:** ✅ Chat functionality unchanged

---

### Regression 2: Session End ✅
**Verify:** End session button works

**Steps:**
1. Click "End Session" button
2. **Verify:** Confirmation or immediate end
3. **Verify:** Redirects to correct page
4. **Verify:** No errors

**Pass Criteria:** ✅ Session management unchanged

---

### Regression 3: Loading Indicators ✅
**Verify:** Loading states display correctly

**Steps:**
1. Send a message
2. **Verify:** Loading spinner appears
3. **Verify:** Input disabled during loading
4. **Verify:** Spinner disappears after response

**Pass Criteria:** ✅ Loading UX unchanged

---

## Accessibility Tests

### A11y 1: Screen Reader ♿
**Test:** VoiceOver/NVDA compatibility

**Steps:**
1. Enable screen reader
2. Navigate to mic button
3. **Verify:** Announces "Start recording" or "Stop recording"
4. Navigate to send button
5. **Verify:** Announces "Send message"
6. Focus textarea
7. **Verify:** Announces placeholder or content

**Pass Criteria:** ✅ All elements announced correctly

---

### A11y 2: Keyboard Navigation ⌨️
**Test:** Full keyboard control

**Steps:**
1. Press Tab repeatedly
2. **Verify:** Focus moves: textarea → mic → send → next element
3. With textarea focused, press Enter
4. **Verify:** Message sent
5. With mic focused, press Space
6. **Verify:** Recording toggles

**Pass Criteria:** ✅ No keyboard traps, all controls accessible

---

### A11y 3: Color Contrast 🎨
**Test:** WCAG compliance

**Steps:**
1. Check mic button (idle): Gray on white
2. Check mic button (recording): Red on white
3. Check send button: Blue on white
4. **Verify:** All have contrast ratio ≥ 4.5:1

**Pass Criteria:** ✅ Passes WCAG AA standards

---

## Bug Report Template

If you find issues during testing, use this format:

```
### Bug: [Short Description]

**Severity:** Critical / High / Medium / Low

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Browser/Device:**
- Browser: Chrome 131 / Safari 18 / etc.
- OS: Windows 11 / macOS 15 / iOS 18
- Device: Desktop / iPhone 15 / etc.

**Screenshots/Videos:**
[Attach if applicable]

**Console Errors:**
```
[Paste any console errors]
```

**Workaround:**
[If you found a temporary fix]
```

---

## Test Results Summary

Fill out after testing:

| Test | Status | Notes |
|------|--------|-------|
| Multiple Recordings Append | ⬜ Pass / ⬜ Fail | |
| Dynamic Height Growth | ⬜ Pass / ⬜ Fail | |
| Manual Typing Integration | ⬜ Pass / ⬜ Fail | |
| Height Reset After Send | ⬜ Pass / ⬜ Fail | |
| Enter Key Behavior | ⬜ Pass / ⬜ Fail | |
| Mic Button States | ⬜ Pass / ⬜ Fail | |
| Send Button State | ⬜ Pass / ⬜ Fail | |
| Loading State | ⬜ Pass / ⬜ Fail | |
| Browser Compatibility | ⬜ Pass / ⬜ Fail | |
| Mobile Behavior | ⬜ Pass / ⬜ Fail | |

**Overall Status:** ⬜ All Pass / ⬜ Some Fail / ⬜ Major Issues

**Tester:** [Your Name]  
**Date:** [Test Date]  
**Build/Commit:** [Git commit hash]

---

## Automated Test Script (Optional)

For future CI/CD integration:

```typescript
// Jest + React Testing Library example

describe('TutoringChat Voice Recording', () => {
  it('should append multiple recordings', async () => {
    const { getByLabelText, getByPlaceholderText } = render(<TutoringChat />);
    const textarea = getByPlaceholderText('Type your answer here...');
    const micButton = getByLabelText('Start recording');
    
    // First recording
    fireEvent.click(micButton);
    await waitFor(() => expect(micButton).toHaveAttribute('aria-label', 'Stop recording'));
    // Simulate speech recognition result
    act(() => {
      mockSpeechRecognition.triggerResult('Hello');
    });
    fireEvent.click(micButton);
    
    expect(textarea.value).toBe('Hello');
    
    // Second recording
    fireEvent.click(micButton);
    act(() => {
      mockSpeechRecognition.triggerResult('teacher');
    });
    fireEvent.click(micButton);
    
    expect(textarea.value).toBe('Hello teacher'); // ✅ Appended
  });
  
  it('should reset height after send', async () => {
    const { getByPlaceholderText, getByLabelText } = render(<TutoringChat />);
    const textarea = getByPlaceholderText('Type your answer here...');
    const sendButton = getByLabelText('Send message');
    
    // Add multi-line text
    fireEvent.change(textarea, { target: { value: 'Line 1\nLine 2\nLine 3' } });
    
    const grownHeight = textarea.style.height;
    expect(parseInt(grownHeight)).toBeGreaterThan(44);
    
    // Send message
    fireEvent.click(sendButton);
    await waitFor(() => expect(textarea.value).toBe(''));
    
    expect(textarea.style.height).toBe('auto'); // Reset
  });
});
```
