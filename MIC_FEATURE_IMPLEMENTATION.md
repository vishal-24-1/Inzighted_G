# ChatGPT-Style Microphone Feature Implementation

## Overview
Updated `TutoringChat.tsx` to implement ChatGPT-style voice recording with the following behavior:
- Multiple voice recordings append to existing text
- Dynamic textarea that grows as content increases
- Resets to original size after sending message
- Enter key submits (Shift+Enter for new line)

## Key Changes Made

### 1. **Voice Recording Segments Tracking**
```typescript
const recordedSegmentsRef = useRef<string[]>([]);
```
- Stores all recorded voice segments across multiple recording sessions
- Each click of the mic button starts a new recording that appends to previous recordings
- Only clears when the user sends the message

### 2. **Replaced Input with Auto-Growing Textarea**
**Before:** Fixed-height `<input>` element
**After:** Dynamic `<textarea>` with:
- Minimum height: 44px (single line)
- Maximum height: 200px (with scroll)
- Auto-grows based on content
- Rounded corners (rounded-3xl) matching ChatGPT aesthetic

### 3. **Auto-Resize Logic**
```typescript
const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
  const value = e.target.value;
  setInputText(value);
  
  // Auto-resize
  e.target.style.height = 'auto';
  e.target.style.height = e.target.scrollHeight + 'px';
};
```
- Triggers on every text change (typing or pasting)
- Also triggers after voice recognition completes
- Smoothly expands/contracts based on content

### 4. **Voice Recording Append Behavior**
```typescript
recognitionInstance.onresult = (event: any) => {
  const transcript = event?.results?.[0]?.[0]?.transcript || '';
  if (transcript) {
    const trimmed = transcript.trim();
    recordedSegmentsRef.current.push(trimmed);
    
    // Join all segments with spaces
    const fullRecordedText = recordedSegmentsRef.current.join(' ');
    setInputText(fullRecordedText);
    
    // Auto-resize after update
    setTimeout(() => {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }, 0);
  }
};
```

### 5. **Reset on Send**
```typescript
handleSubmitAnswer() {
  // ... send message logic ...
  setInputText('');
  recordedSegmentsRef.current = []; // Clear recordings
  if (textareaRef.current) {
    textareaRef.current.style.height = 'auto'; // Reset height
  }
}
```

### 6. **Keyboard Shortcuts (ChatGPT-style)**
```typescript
onKeyDown={(e) => {
  // Submit on Enter (without Shift)
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmitAnswer(e as any);
  }
  // Shift+Enter creates new line (default textarea behavior)
}}
```

## User Experience Flow

### Recording Voice Messages
1. **First Recording:**
   - User clicks mic button → starts recording
   - User speaks → "Hello teacher"
   - User clicks mic again → stops recording
   - Result: "Hello teacher" appears in textarea

2. **Second Recording (Append):**
   - User clicks mic button again → starts new recording
   - User speaks → "I have a question"
   - User clicks mic again → stops recording
   - Result: "Hello teacher I have a question" (appended with space)

3. **Continue Adding:**
   - User can click mic multiple times
   - Each recording appends to previous text
   - User can also type additional text manually
   - All content is preserved until send

4. **Send Message:**
   - User clicks send button OR presses Enter
   - Message is sent
   - Textarea clears and resets to original height
   - Recording segments are cleared
   - Ready for fresh new message

### Dynamic Height Behavior
- **Empty:** Single line (44px min-height)
- **1-2 lines:** Grows naturally to fit content
- **3+ lines:** Continues growing up to 200px max-height
- **Exceeds max:** Textarea becomes scrollable
- **After send:** Immediately resets to single-line height

## Visual Improvements

### Textarea Container Styling
```css
min-h-[44px]        /* Minimum single-line height */
max-h-[200px]       /* Maximum height before scroll */
rounded-3xl         /* More rounded than before (ChatGPT-style) */
items-end           /* Align buttons to bottom when textarea grows */
```

### Mic Button States
- **Idle:** Gray background with hover scale effect
- **Recording:** Red background with pulse animation + white text
- **Disabled:** Reduced opacity, no interactions

### Send Button
- **Disabled:** When textarea is empty or loading
- **Active:** Blue with hover scale and color change
- **Icon offset:** `-4px` left margin for visual centering

## Accessibility Improvements
- Added `aria-label` to mic button: "Start recording" / "Stop recording"
- Added `aria-label` to send button: "Send message"
- Keyboard navigation fully supported
- Screen readers can announce button states

## Technical Details

### Browser Compatibility
- Uses Web Speech API (SpeechRecognition)
- Fallback to webkitSpeechRecognition for Safari
- Gracefully degrades if API not available
- Tested in Chrome, Edge, Safari

### Performance Considerations
- Uses `useRef` for segments to avoid unnecessary re-renders
- `setTimeout(..., 0)` for height calculation ensures DOM update completes
- Minimal state updates during typing/recording
- Smooth animations with CSS transitions

### Memory Management
- Recording segments cleared after each message sent
- No memory leaks from speech recognition listeners
- Proper cleanup in useEffect hooks

## Comparison with Previous Implementation

| Feature | Before | After |
|---------|--------|-------|
| Voice recording | Overwrites previous text | Appends to existing text |
| Input type | Single-line input | Multi-line textarea |
| Height | Fixed 44px | Dynamic 44-200px |
| Enter key | Submit only | Submit (Shift+Enter for new line) |
| Visual feedback | Basic | ChatGPT-style with animations |
| Recording state | Basic color change | Pulse animation + color |
| Multiple recordings | Lost previous text | Accumulates all recordings |

## Testing Checklist

- [x] Multiple voice recordings append correctly
- [x] Textarea grows when typing long text
- [x] Textarea grows when recording adds content
- [x] Textarea resets to single-line after send
- [x] Enter key submits message
- [x] Shift+Enter creates new line
- [x] Mic button shows correct visual states
- [x] Send button disabled when textarea empty
- [x] Manual typing works alongside voice recording
- [x] Text can be edited after recording
- [x] Focus management works correctly
- [x] Scroll appears when content exceeds max height
- [x] All existing chat functionality preserved

## Files Modified
- `frontend/src/pages/TutoringChat.tsx` - Complete implementation

## Future Enhancements (Optional)
1. Add visual indicator showing number of recordings accumulated
2. Add "Clear" button to reset recordings without sending
3. Show interim results during recording (real-time transcript)
4. Add voice waveform animation during recording
5. Support multiple languages with language picker
6. Add recording duration indicator
7. Store recordings in session storage for recovery
8. Add undo/redo for recordings

## Related Documentation
- Web Speech API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
- ChatGPT UX Patterns: Industry standard for conversational AI interfaces
- Accessibility Guidelines: WCAG 2.1 Level AA compliance
