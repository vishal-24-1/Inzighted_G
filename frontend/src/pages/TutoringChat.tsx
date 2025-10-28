import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { tutoringAPI } from '../utils/api';
import { Mic, Send, Square } from 'lucide-react';
import SessionFeedback from '../components/SessionFeedback';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  questionNumber?: number;
  totalQuestions?: number;
}

// Avoid duplicating DOM SpeechRecognition types; use runtime checks and `any` for instances

interface TutoringChatProps {
  sessionIdOverride?: string;
  onEndSession?: () => void; // called when session ends or user cancels
  onStartSession?: (session_id: string) => void; // called after creating a session
}

const TutoringChat: React.FC<TutoringChatProps> = ({ sessionIdOverride, onEndSession, onStartSession }) => {
  const { user } = useAuth();
  const { sessionId: sessionIdParam } = useParams<{ sessionId: string }>();
  const sessionId = sessionIdOverride || sessionIdParam;
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any | null>(null);
  const [sessionFinished, setSessionFinished] = useState(false);
  const [isEndingSession, setIsEndingSession] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [pasteBlocked, setPasteBlocked] = useState(false);
  // This page is mobile-first. Force mobile mode to simplify behavior and
  // avoid desktop-specific branches.
  const isMobile = true;

  const [sessionDocument, setSessionDocument] = useState<string | null>(null);
  const [sessionCreatedAt, setSessionCreatedAt] = useState<Date | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(900); // 15 minutes = 900 seconds
  const [timeoutMins, setTimeoutMins] = useState<number>(15);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const baseInputRef = useRef<string>('');
  const keepListeningRef = useRef<boolean>(false);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const initialInputHeight = 44; // px - used to reset after send
  const inputBarRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement | null>(null);
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const [inputBarHeight, setInputBarHeight] = useState<number>(64);
  const [viewportHeight, setViewportHeight] = useState<number>(0);

  useEffect(() => {
    // Set CSS variable --vh to handle mobile browser toolbar + keyboard resizing.
    const setVh = () => {
      try {
        document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
      } catch (e) {
        // ignore
      }
    };
    setVh();
    window.addEventListener('resize', setVh);
    window.addEventListener('orientationchange', setVh);

    // Mobile-only: skip user-agent detection and treat as mobile device.
    // Initialize speech recognition
    if ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognitionInstance = new SR();

      // Keep the recognition running continuously until the user explicitly
      // stops it by pressing the mic button again.
      recognitionInstance.continuous = true;
      // Enable interim results so we can show speaking text as it's recognized
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-IN';

      recognitionInstance.onstart = () => setIsListening(true);

      // When recognition ends (e.g., browser stops due to network/timeout),
      // restart it automatically only if the user hasn't explicitly stopped
      // listening. This keeps the mic active until the user toggles it off.
      recognitionInstance.onend = () => {
        setIsListening(false);
        try {
          if (keepListeningRef.current) {
            // small delay before restarting avoids rapid start/stop loops
            setTimeout(() => {
              try {
                recognitionInstance.start();
              } catch (e) {
                // ignore start errors
              }
            }, 250);
          }
        } catch (e) {
          // ignore
        }
      };

      // When interimResults=true, the event.results array will contain a mix
      // of final and interim transcripts. We'll keep a base input (what the
      // user typed + finalized recognition) in baseInputRef and append the
      // interim transcript for live feedback.
      recognitionInstance.onresult = (event: any) => {
        try {
          let interim = '';
          let final = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const res = event.results[i];
            const t = res[0]?.transcript || '';
            if (res.isFinal) {
              final += (final ? ' ' : '') + t.trim();
            } else {
              interim += (interim ? ' ' : '') + t.trim();
            }
          }

          // If we got a final segment, commit it to the base input
          if (final) {
            baseInputRef.current = baseInputRef.current && baseInputRef.current.trim()
              ? `${baseInputRef.current} ${final}`
              : final;
          }

          // Update visible textarea to show base + interim (if any)
          const combined = baseInputRef.current && baseInputRef.current.trim()
            ? `${baseInputRef.current}${interim ? ' ' + interim : ''}`
            : (interim || '');

          setInputText(combined);

          // Focus and move caret to end so user sees the live transcription
          setTimeout(() => {
            try {
              const el = inputRef.current;
              if (el) {
                el.focus();
                const len = el.value.length;
                el.selectionStart = el.selectionEnd = len;
                el.style.height = 'auto';
                el.style.height = Math.min(el.scrollHeight, 240) + 'px';
              }
            } catch (e) {
              // ignore
            }
          }, 0);
        } catch (err) {
          console.error('Speech recognition onresult error:', err);
        }
      };

      recognitionInstance.onerror = (event: any) => {
        console.error('Speech recognition error:', event);
        setIsListening(false);
      };

      setRecognition(recognitionInstance);
    }

    // Load session messages when component mounts
    if (sessionId) {
      loadSessionMessages();
    }

    // Track visual viewport height so we can size the outer container to the
    // available visual viewport (prevents the page from staying full-height
    // and leaving a gap when the on-screen keyboard opens).
    const updateViewportHeight = () => {
      try {
        const vv = (window as any).visualViewport;
        setViewportHeight(vv?.height || window.innerHeight);
      } catch (e) {
        setViewportHeight(window.innerHeight);
      }
    };
    updateViewportHeight();
    window.addEventListener('resize', updateViewportHeight);
    (window as any).visualViewport?.addEventListener('resize', updateViewportHeight);

    // Cleanup timer and listeners on unmount
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      try {
        window.removeEventListener('resize', setVh);
        window.removeEventListener('orientationchange', setVh);
        window.removeEventListener('resize', updateViewportHeight);
        (window as any).visualViewport?.removeEventListener('resize', updateViewportHeight);
      } catch (e) {
        // ignore
      }
    };
  }, [sessionId, searchParams]);

  // Lock body scroll and stabilize viewport height using visualViewport; keep last message visible
  useEffect(() => {
    // Save previous body/html styles so we can restore on cleanup
    const body = document.body;
    const docEl = document.documentElement;
    const prevBodyOverflow = body.style.overflow;
    const prevBodyPosition = body.style.position;
    const prevBodyTop = body.style.top;
    const prevBodyLeft = body.style.left;
    const prevBodyRight = body.style.right;
    const prevBodyWidth = body.style.width;
    const prevHtmlOverscroll = docEl.style.overscrollBehavior;
    const prevBodyOverscroll = body.style.overscrollBehavior;
    const scrollY = window.scrollY || window.pageYOffset || 0;

    // Lock body in place to prevent background scrolling / bounce
    try {
      body.style.overflow = 'hidden';
      body.style.position = 'fixed';
      body.style.top = `-${scrollY}px`;
      body.style.left = '0';
      body.style.right = '0';
      body.style.width = '100%';
      // Prevent overscroll/bounce on iOS/modern browsers
      docEl.style.overscrollBehavior = 'none';
      body.style.overscrollBehavior = 'none';
    } catch (e) {
      // ignore
    }

    // Update CSS var for viewport height and position the input bar above
    // the on-screen keyboard on mobile using visualViewport. When visualViewport
    // is not available we fallback to window.innerHeight behavior.
    const updateVvh = () => {
      try {
        const vv = (window as any).visualViewport?.height;
        const vvHeight = vv || window.innerHeight;
        document.documentElement.style.setProperty('--vvh', `${vvHeight}px`);

        // If we're on mobile and have an input bar element, adjust its position
        // so it sits above the virtual keyboard. When visualViewport is present
        // calculate the keyboard offset as the difference between the full
        // window.innerHeight and the visual viewport height. Otherwise 0.
        if (isMobile && inputBarRef.current) {
          const keyboardOffset = vv ? Math.max(0, window.innerHeight - vv) : 0;
          inputBarRef.current.style.transform = keyboardOffset
            ? `translateX(-50%) translateY(-${keyboardOffset}px)`
            : 'translateX(-50%)';
        } else if (inputBarRef.current) {
          // restore centering transform by default
          inputBarRef.current.style.transform = 'translateX(-50%)';
        }
      } catch (e) {
        // ignore
      }
    };

    const onViewportResize = () => {
      updateVvh();
    };

    updateVvh();
    window.addEventListener('resize', onViewportResize);
    (window as any).visualViewport?.addEventListener('resize', onViewportResize);

    // Observe input bar height so we can pad the message list accordingly
    let ro: any = null;
    try {
      if (inputBarRef.current && 'ResizeObserver' in window) {
        ro = new (window as any).ResizeObserver((entries: any) => {
          const h = entries?.[0]?.contentRect?.height;
          if (h && h !== inputBarHeight) {
            setInputBarHeight(Math.ceil(h));
          }
        });
        ro.observe(inputBarRef.current);
        // initial measurement
        setInputBarHeight(inputBarRef.current.clientHeight || inputBarHeight);
      }
    } catch (e) {
      // ignore
    }

    return () => {
      // restore page scroll position and styles
      try {
        window.removeEventListener('resize', onViewportResize);
        (window as any).visualViewport?.removeEventListener('resize', onViewportResize);

        if (ro && inputBarRef.current) {
          ro.unobserve(inputBarRef.current);
          ro.disconnect();
        }

        // clear any inline bottom style we added
        if (inputBarRef.current) inputBarRef.current.style.bottom = '';

        // restore overscroll and body styles
        docEl.style.overscrollBehavior = prevHtmlOverscroll || '';
        body.style.overscrollBehavior = prevBodyOverscroll || '';
        body.style.overflow = prevBodyOverflow || '';
        body.style.position = prevBodyPosition || '';
        body.style.top = prevBodyTop || '';
        body.style.left = prevBodyLeft || '';
        body.style.right = prevBodyRight || '';
        body.style.width = prevBodyWidth || '';

        // restore original scroll position
        if (scrollY) {
          window.scrollTo(0, scrollY);
        }
      } catch (e) {
        // ignore
      }
    };
    // Mobile-only: no mobile state changes to watch.
  }, []);

  // Prevent touch scrolling on header and input areas so only messages area scrolls
  useEffect(() => {
    const preventTouchScroll = (e: TouchEvent) => {
      try {
        // If a modal like SessionFeedback is open, allow touch events so the
        // modal can handle scrolling and so we don't block its interactions.
        if (showFeedback) return;

        const target = e.target as HTMLElement;
        const messagesArea = messagesScrollRef.current;

        if (messagesArea && !messagesArea.contains(target)) {
          e.preventDefault();
        }
      } catch (err) {
        // ignore
      }
    };

    document.addEventListener('touchmove', preventTouchScroll, { passive: false });

    return () => {
      document.removeEventListener('touchmove', preventTouchScroll as EventListener);
    };
  }, [showFeedback]);

  // Keep only the messages area scrollable by positioning it between
  // the fixed header and the fixed input bar. This ensures the header
  // and input/footer remain visible when the keyboard opens and the
  // page resizes (visualViewport). We measure heights and apply
  // absolute positioning to the messages container accordingly.
  useEffect(() => {
    const updateScrollableArea = () => {
      try {
        const msgs = messagesScrollRef.current;
        const hdr = headerRef.current;
        const inputBar = inputBarRef.current;
        if (!msgs || !hdr || !inputBar) return;

        const headerRect = hdr.getBoundingClientRect();
        const headerHeight = Math.ceil(headerRect.height);

        // Calculate available height for messages (fill between header and viewport bottom)
        const availableHeight = Math.max(0, viewportHeight - headerHeight);

        // Get input bar height (fallback to measured state)
        const inputRect = inputBar.getBoundingClientRect();
        const inputHeight = Math.ceil(inputRect.height) || inputBarHeight || 64;

        msgs.style.position = 'absolute';
        msgs.style.top = headerHeight + 'px';
        // Set height to fill the area, messages will be padded at the bottom so
        // the last message sits above the input bar.
        msgs.style.height = availableHeight + 'px';
        msgs.style.left = '0';
        msgs.style.right = '0';
        msgs.style.overflowY = 'auto';
        msgs.style.overflowX = 'hidden';
        // Ensure there's space at the bottom so last messages aren't hidden by the input
        msgs.style.paddingBottom = (inputHeight + 16) + 'px';

        // Force reflow and ensure proper scrolling to bottom
        setTimeout(() => {
          // scroll to bottom, accounting for the bottom padding
          msgs.scrollTop = msgs.scrollHeight;
        }, 50);
      } catch (e) {
        console.error('Error updating scrollable area:', e);
      }
    };

    updateScrollableArea();
    window.addEventListener('resize', updateScrollableArea);
    (window as any).visualViewport?.addEventListener('resize', updateScrollableArea);

    return () => {
      window.removeEventListener('resize', updateScrollableArea);
      (window as any).visualViewport?.removeEventListener('resize', updateScrollableArea);
    };
  }, [inputBarHeight, viewportHeight]);

  // Timer effect - start countdown after session data is loaded
  useEffect(() => {
    if (!sessionCreatedAt || sessionFinished || !sessionId) return;

    // Clear any existing timer
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }

    // Calculate initial remaining time
    const updateRemainingTime = () => {
      const now = new Date();
      const elapsed = Math.floor((now.getTime() - sessionCreatedAt.getTime()) / 1000);
      const remaining = Math.max(0, (timeoutMins * 60) - elapsed);

      setRemainingSeconds(remaining);

      // Auto-end session when timer reaches 0: mark session finished so the
      // feedback flow can run (we avoid calling handleEndSession here to keep
      // the UX consistent and let the feedback effect handle presentation).
      if (remaining === 0 && !isEndingSession && !sessionFinished) {
        console.log('Session timeout reached, marking session finished');
        if (timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
        }
        setSessionFinished(true);
      }
    };

    // Initial calculation
    updateRemainingTime();

    // Update every second
    timerIntervalRef.current = setInterval(updateRemainingTime, 1000);

    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [sessionCreatedAt, sessionFinished, timeoutMins, isEndingSession, sessionId]);

  // Simplified scroll helper and single effect to avoid conflicting scroll operations
  const scrollMessagesToBottom = () => {
    const container = messagesScrollRef.current;
    if (!container) return;

    try {
      // Immediate scroll to bottom to avoid bouncing
      container.scrollTop = container.scrollHeight;
    } catch (e) {
      // silent fail
    }
  };

  useEffect(() => {
    // Don't attempt to scroll while the feedback modal is visible because the
    // modal overlay may be intercepting pointer/touch events or the user may
    // be interacting with the modal.
    if (messages.length === 0 || showFeedback) return;

    const scrollToBottom = () => {
      const container = messagesScrollRef.current;
      if (!container) return;

      try {
        container.scrollTop = container.scrollHeight;
      } catch (error) {
        // ignore
      }
    };

    const timeoutId = setTimeout(scrollToBottom, 50);
    return () => clearTimeout(timeoutId);
  }, [messages, showFeedback]);

  // When the feedback modal closes, ensure the messages container is restored
  // to the bottom (in case the modal stole focus or blocked scroll during
  // its lifetime).
  useEffect(() => {
    if (!showFeedback && messages.length > 0) {
      const timeoutId = setTimeout(() => {
        scrollMessagesToBottom();
      }, 200);
      return () => clearTimeout(timeoutId);
    }
    // If modal is open, we don't force-scroll.
    return;
  }, [showFeedback]);

  // Automatically show feedback when the session finishes (completed or
  // timed out). Small delay so the user briefly sees the completion message
  // before the feedback form appears.
  useEffect(() => {
    if (sessionFinished && !showFeedback && sessionId) {
      const t = setTimeout(() => {
        setShowFeedback(true);
      }, 1500);
      return () => clearTimeout(t);
    }
    return;
  }, [sessionFinished, showFeedback, sessionId]);

  // Auto-focus intentionally omitted for mobile to avoid opening the virtual
  // keyboard automatically. The input will be focused when the user interacts.

  const loadSessionMessages = async () => {
    if (!sessionId) return;

    try {
      const response = await tutoringAPI.getSessionDetail(sessionId);
      const sessionData = response.data;

      // Convert session messages to our message format
      const sessionMessages: Message[] = sessionData.messages.map((msg: any) => ({
        id: msg.id,
        text: msg.content,
        isUser: msg.is_user_message,
        timestamp: new Date(msg.created_at),
        questionNumber: msg.question_number,
        totalQuestions: msg.total_questions
      }));

      setMessages(sessionMessages);

      // scrolling is handled by the centralized messages effect

      // Set document information if available
      if (sessionData.document) {
        setSessionDocument(sessionData.document.filename);
      }

      // Set session created time for timer
      if (sessionData.created_at) {
        setSessionCreatedAt(new Date(sessionData.created_at));
      }

      // Set timeout configuration from server
      if (sessionData.timeout_mins) {
        setTimeoutMins(sessionData.timeout_mins);
      }

      // Check if session is already expired
      if (sessionData.session_expired || !sessionData.is_active) {
        console.log('Session already expired or inactive');
        setSessionFinished(true);
        // Auto-trigger end flow
        if (!isEndingSession) {
          handleEndSession();
        }
      }
    } catch (error: any) {
      console.error('Failed to load session messages:', error);
      if (error.response?.status === 404) {
        alert('Tutoring session not found.');
        if (onEndSession) onEndSession();
        else navigate('/boost');
      } else if (error.response?.status === 410) {
        // Session expired on server
        console.log('Session expired (410 response)');
        setSessionFinished(true);
        setShowFeedback(true);
      }
    }
  };

  const handleSubmitAnswer = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    // Stop listening if mic is active when user submits
    if (recognition && isListening) {
      stopListening();
    }

    if (!inputText.trim() || isLoading || sessionFinished || !sessionId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText.trim(),
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    // clear base input so interim transcription doesn't resurrect old text
    baseInputRef.current = '';
    // Reset textarea height to initial value after sending
    try {
      if (inputRef.current) {
        inputRef.current.style.height = initialInputHeight + 'px';
      }
    } catch (e) { }
    setIsLoading(true);

    try {
      const response = await tutoringAPI.submitAnswer(sessionId, userMessage.text);

      if (response.data.finished) {
        // Session is complete
        setSessionFinished(true);
        const completionMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: response.data.message,
          isUser: false,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, completionMessage]);
      } else {
        // If the agent provided feedback (reply), show it immediately
        const itemsToAppend: Message[] = [];

        if (response.data.feedback && response.data.feedback.text) {
          const feedbackMessage: Message = {
            id: response.data.feedback.id || (Date.now() + 2).toString(),
            text: response.data.feedback.text,
            isUser: false,
            timestamp: new Date()
          };
          itemsToAppend.push(feedbackMessage);
        }

        // Add the next question if present
        if (response.data.next_question && response.data.next_question.text) {
          const nextQuestion: Message = {
            id: response.data.next_question.id,
            text: response.data.next_question.text,
            isUser: false,
            timestamp: new Date(response.data.next_question.created_at),
            questionNumber: response.data.next_question.question_number,
            totalQuestions: response.data.next_question.total_questions
          };
          itemsToAppend.push(nextQuestion);
        }

        if (itemsToAppend.length > 0) {
          setMessages(prev => [...prev, ...itemsToAppend]);
        }
      }
    } catch (error: any) {
      // Check if session has expired (410 Gone)
      if (error.response?.status === 410) {
        console.log('Session expired during answer submission');
        setSessionFinished(true);
        const expiredMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: 'Your session has automatically ended after 15 minutes. Great work! 🎉',
          isUser: false,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, expiredMessage]);
        // The automatic feedback effect will handle showing the feedback form
        // after sessionFinished is set, so no need to call handleEndSession()
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, I encountered an error. Please try again.',
          isUser: false,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        console.error('Tutoring error:', error);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Handle key events inside the textarea: Enter = send, Shift+Enter = newline
  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      // Only submit if we have non-empty content
      if (!isLoading && inputText.trim() && !sessionFinished) {
        // call submit without synthetic event
        // eslint-disable-next-line @typescript-eslint/no-floating-promises
        handleSubmitAnswer();
      }
    }
  };

  const handlePasteBlock = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    // prevent pasting into the answer input
    e.preventDefault();
    setPasteBlocked(true);
    // hide the message after 2s
    setTimeout(() => setPasteBlocked(false), 2000);
  };

  const handleDropBlock = (e: React.DragEvent<HTMLTextAreaElement>) => {
    // also prevent dropping text/files into textarea
    e.preventDefault();
    setPasteBlocked(true);
    setTimeout(() => setPasteBlocked(false), 2000);
  };

  const handleEndSession = async () => {
    if (!sessionId) return;
    // prevent multiple clicks
    if (isEndingSession) return;
    setIsEndingSession(true);

    try {
      await tutoringAPI.endSession(sessionId);

      // Show feedback form instead of navigating immediately
      setShowFeedback(true);
      setIsEndingSession(false);
    } catch (error: any) {
      console.error('Failed to end session:', error);
      // Still show feedback even if end request fails
      setShowFeedback(true);
      setIsEndingSession(false);
    }
  };

  const handleFeedbackComplete = () => {
    // Navigate to insights page after feedback is submitted
    if (onEndSession) {
      onEndSession();
    } else {
      navigate(`/boost?session=${sessionId}`);
    }
  };

  const handleFeedbackSkip = () => {
    // Navigate to insights page after skipping feedback
    if (onEndSession) {
      onEndSession();
    } else {
      navigate(`/boost?session=${sessionId}`);
    }
  };

  // Format remaining time as MM:SS
  const formatRemainingTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Determine timer color based on remaining time
  const getTimerColor = (): string => {
    if (remainingSeconds <= 60) return 'text-red-600'; // Last minute - red
    if (remainingSeconds <= 180) return 'text-orange-500'; // Last 3 minutes - orange
    return 'text-gray-700'; // Normal - gray
  };

  // Document selection is handled before arriving on this page; no selector here.

  const startListening = () => {
    if (recognition && !isListening && !sessionFinished) {
      keepListeningRef.current = true;
      try {
        recognition.start();
      } catch (e) {
        // Some browsers throw if start is called multiple times; ignore.
      }
    }
  };

  const stopListening = () => {
    if (recognition && isListening) {
      // Mark that the user requested stop so onend won't auto-restart
      keepListeningRef.current = false;
      try {
        recognition.stop();
      } catch (e) {
        // ignore
      }
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // The tutoring chat page assumes a session is already created and will
  // redirect to home if no session id is provided.

  // If embedded (parent provided onEndSession) and no session ID, simply render nothing.
  if (!sessionId) {
    if (onEndSession) return null;
    // Redirect to boost page if no session ID and not embedded
    navigate('/boost');
    return null;
  }

  return (
    <>
      {/* Show feedback modal when session is finished */}
      {showFeedback && sessionId && (
        <div style={{ zIndex: 1000, position: 'relative' }}>
          <SessionFeedback
            sessionId={sessionId}
            onComplete={handleFeedbackComplete}
            onSkip={handleFeedbackSkip}
          />
        </div>
      )}

      {/* Outer container fixed to viewport to prevent body scrolling. Uses --vvh for stable height with mobile keyboards. */}
      <div
        className="fixed inset-0 bg-gray-50 font-sans w-full"
        style={{ height: viewportHeight ? `${viewportHeight}px` : 'var(--vvh, 100dvh)' }}
      >
        <div className="max-w-3xl mx-auto flex flex-col h-full">
          <header
            ref={headerRef}
            className="bg-white border-b text-gray-900 p-4 sticky top-0 z-50 touch-none select-none"
            style={{ touchAction: 'none' }}
          >
            <div className="flex justify-between items-center gap-3">
              <h1 className="text-lg font-semibold m-0 truncate max-w-[8rem]">{sessionDocument || 'AI Tutor'}</h1>

              {/* Countdown Timer */}
              <div
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 border ${remainingSeconds <= 60 ? 'border-red-300 bg-red-50' :
                  remainingSeconds <= 180 ? 'border-orange-300 bg-orange-50' :
                    'border-gray-200'
                  }`}
                aria-live="polite"
                aria-atomic="true"
              >
                <svg
                  className={`h-4 w-4 ${getTimerColor()}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span
                  className={`text-sm font-mono font-semibold ${getTimerColor()}`}
                  title="Session will automatically end when timer reaches 0"
                >
                  {formatRemainingTime(remainingSeconds)}
                </span>
              </div>

              <button
                onClick={handleEndSession}
                className="bg-red-100 text-red-600 font-semibold border border-red-600 rounded-xl px-3 py-1.5 text-sm cursor-pointer transition-all duration-300 hover:bg-red-300 hover:-translate-y-0.5 shadow-sm disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap"
                disabled={isEndingSession}
              >
                {isEndingSession ? (
                  <span className="inline-flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                    </svg>
                    Ending...
                  </span>
                ) : (
                  'End Session'
                )}
              </button>
            </div>
          </header>

          <main className="flex-1 flex flex-col bg-gray-50 overflow-hidden">
            <div
              ref={messagesScrollRef}
              className="overflow-y-auto overscroll-contain p-4"
              style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'contain' }}
            >
              <div className="flex flex-col gap-2">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex w-full ${message.isUser ? 'justify-end' : 'justify-start'} mb-3`}
                  >
                    {/* Mobile layout: constrain width for message bubbles */}
                    <div className={`max-w-[80%]`}>
                      {/* Show question number badge for bot messages that have question_number */}
                      {!message.isUser && message.questionNumber && message.totalQuestions && (
                        <div className="mb-1.5 flex items-center gap-1.5">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            Q.{message.questionNumber}/{message.totalQuestions}
                          </span>
                        </div>
                      )}
                      <div className={`rounded-2xl py-3 px-4 shadow-md relative hover:shadow-lg transition-shadow duration-200 ${message.isUser ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' : 'bg-white text-gray-800'}`}>
                        <div className="text-sm leading-relaxed text-left whitespace-pre-wrap break-words">{message.text}</div>
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex w-full justify-start mb-3">
                    <div className="max-w-[80%]">
                      <div className="bg-white rounded-2xl py-3 px-4 shadow-md">
                        <div className="flex gap-1 p-2">
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></span>
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                {/* Scroll anchor with height to ensure proper scroll behavior */}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            {!sessionFinished && (
              // Floating "dynamic island" input for mobile: centered, elevated pill
              <div
                ref={inputBarRef}
                className="fixed left-1/2 bottom-4 z-40 transform -translate-x-1/2 w-full max-w-md px-4 touch-none select-none"
                style={{
                  paddingBottom: 'env(safe-area-inset-bottom)',
                  touchAction: 'none'
                }}
              >
                <form onSubmit={handleSubmitAnswer} className="w-full">
                  <div className="bg-white rounded-xl shadow-lg px-3 py-2 flex items-end gap-2 border border-gray-200 relative">
                    <textarea
                      ref={inputRef}
                      value={inputText}
                      onChange={(e) => {
                        const val = e.target.value;
                        setInputText(val);
                        // keep base input in sync with user edits so interim appends correctly
                        baseInputRef.current = val;
                        // Auto-resize textarea
                        const el = e.target as HTMLTextAreaElement;
                        el.style.height = 'auto';
                        el.style.height = Math.min(el.scrollHeight, 240) + 'px';
                      }}

                      onKeyDown={handleInputKeyDown}
                      onPaste={handlePasteBlock}
                      onDrop={handleDropBlock}
                      placeholder="Type your answer"
                      aria-label="Type your answer"
                      className="flex-1 resize-none bg-transparent px-3 py-2 text-base outline-none placeholder-gray-400 max-h-60"
                      disabled={isLoading || sessionFinished}
                      rows={1}
                    />

                    <button
                      type="button"
                      onClick={isListening ? stopListening : startListening}
                      title={isListening ? 'Stop recording' : 'Start speech input'}
                      aria-pressed={isListening}
                      aria-label={isListening ? 'Stop recording' : 'Start speech input'}
                      className={`w-10 h-10 rounded-full flex items-center justify-center self-end cursor-pointer transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${isListening ? 'bg-red-600 text-white ring-4 ring-red-200' : 'bg-gray-200 text-gray-700'}`}
                      disabled={isLoading || sessionFinished}
                    >
                      {isListening ? <Square size={14} /> : <Mic size={18} />}
                    </button>

                    {/* Listening indicator similar to ChatGPT's recording UX: visible above the input when active */}
                    {isListening && (
                      <div
                        role="status"
                        aria-live="polite"
                        className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-full px-3 py-1.5 flex items-center gap-2 shadow-lg"
                      >
                        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span className="text-sm font-medium text-gray-800">Listening</span>
                        <div className="flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0s' }} />
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.08s' }} />
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.16s' }} />
                        </div>
                      </div>
                    )}

                    <button
                      type="submit"
                      title="Send answer"
                      className="w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center self-end cursor-pointer transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={isLoading || !inputText.trim() || sessionFinished}
                    >
                      <Send size={16} />
                    </button>
                  </div>

                  {pasteBlocked && (
                    <div className="mt-2 text-sm text-red-600 text-center">Pasting is disabled — please type your answer.</div>
                  )}
                </form>
              </div>
            )}

            {sessionFinished && !showFeedback && (
              <div className="bg-white border-t border-gray-200 p-8 text-center">
                <div>
                  <h3 className="text-green-500 m-0 mb-2 text-xl font-semibold">Session Complete!</h3>
                  <p className="text-gray-600 m-0 mb-6 leading-relaxed">Preparing your feedback form...</p>
                  <div className="flex gap-2 p-2 justify-center">
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce"></span>
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                    <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                  </div>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </>
  );
};

export default TutoringChat;