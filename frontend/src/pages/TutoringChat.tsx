import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { tutoringAPI } from '../utils/api';
import { Mic, Send } from 'lucide-react';
import SessionFeedback from '../components/SessionFeedback';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
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
  const [isMobile, setIsMobile] = useState(false);

  const [sessionDocument, setSessionDocument] = useState<string | null>(null);
  const [sessionCreatedAt, setSessionCreatedAt] = useState<Date | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(900); // 15 minutes = 900 seconds
  const [timeoutMins, setTimeoutMins] = useState<number>(15);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const initialInputHeight = 44; // px - used to reset after send

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

    // detect mobile user agents to avoid auto-focusing which opens virtual keyboard
    const ua = navigator.userAgent || navigator.vendor || (window as any).opera;
    const mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
    setIsMobile(Boolean(mobile));
    // Initialize speech recognition
    if ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) {
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognitionInstance = new SR();

      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onstart = () => setIsListening(true);
      recognitionInstance.onend = () => setIsListening(false);

      recognitionInstance.onresult = (event: any) => {
        const transcript = event?.results?.[0]?.[0]?.transcript || '';
        if (transcript) {
          // Append transcript to existing text (ChatGPT-like behaviour)
          setInputText((prev) => {
            const next = prev && prev.trim() ? `${prev} ${transcript}` : transcript;
            return next;
          });

          // Focus and move caret to end after a tick so the textarea updates first
          setTimeout(() => {
            try {
              const el = inputRef.current;
              if (el) {
                el.focus();
                // move caret to end
                const len = el.value.length;
                el.selectionStart = el.selectionEnd = len;
                // adjust height to fit new content
                el.style.height = 'auto';
                el.style.height = Math.min(el.scrollHeight, 240) + 'px';
              }
            } catch (e) {
              // ignore
            }
          }, 0);
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

    // Cleanup timer and listeners on unmount
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      try {
        window.removeEventListener('resize', setVh);
        window.removeEventListener('orientationchange', setVh);
      } catch (e) {
        // ignore
      }
    };
  }, [sessionId, searchParams]);

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

      // Auto-end session when timer reaches 0
      if (remaining === 0 && !isEndingSession) {
        console.log('Session timeout reached, auto-ending session');
        if (timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
        }
        handleEndSession();
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

  useEffect(() => {
    // Auto-scroll to bottom when new messages are added
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-focus the input when the chat is visible and ready.
  useEffect(() => {
    // Only focus when there's a session and the input isn't disabled by loading/finished state.
    if (!sessionId || isLoading || sessionFinished) return;

    // Slight delay ensures the input is mounted and visible (helps with some browsers)
    // Avoid auto-focusing on mobile to prevent the virtual keyboard from opening automatically.
    let t: any = null;
    if (!isMobile) {
      t = setTimeout(() => {
        try {
          inputRef.current?.focus();
        } catch (e) {
          // ignore focus errors
        }
      }, 50);
    }

    return () => {
      if (t) clearTimeout(t);
    };
  }, [sessionId, isLoading, sessionFinished, isMobile]);

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
        timestamp: new Date(msg.created_at)
      }));

      setMessages(sessionMessages);

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

    if (!inputText.trim() || isLoading || sessionFinished || !sessionId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText.trim(),
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
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
            timestamp: new Date(response.data.next_question.created_at)
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
        // Trigger end flow
        setTimeout(() => handleEndSession(), 1000);
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
      recognition.start();
    }
  };

  const stopListening = () => {
    if (recognition && isListening) {
      recognition.stop();
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
        <SessionFeedback
          sessionId={sessionId}
          onComplete={handleFeedbackComplete}
          onSkip={handleFeedbackSkip}
        />
      )}

      {/* Outer full-width background so mobile remains unchanged but desktop can center a wider container */}
      <div className="min-h-screen bg-gray-50 font-sans w-full">
        <div className="max-w-sm md:max-w-full mx-auto shadow-xl flex flex-col min-h-screen">
          <header className="bg-white border-b text-gray-900 p-4 sticky top-0 z-20">
            <div className="flex justify-between items-center gap-3">
              <h1 className="text-lg font-semibold m-0 truncate max-w-[8rem] md:max-w-xl">{sessionDocument || 'AI Tutor'}</h1>

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

          <main className="flex-1 flex flex-col" style={{ height: 'calc(var(--vh, 1vh) * 100 - 80px)' }}>
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex flex-col gap-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex w-full ${message.isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {/* On mobile keep 80% width; on desktop reduce to ~60% for better visuals */}
                    <div className={`max-w-[80%] md:max-w-[60%]`}>
                      <div className={`bg-white rounded-2xl py-2 px-3 shadow-md relative hover:shadow-lg transition-shadow duration-200 ${message.isUser ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' : 'bg-white text-gray-800'}`}>
                        <div className="text-sm leading-relaxed text-left">{message.text}</div>
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex w-full justify-start">
                    <div className="max-w-[80%] md:max-w-[60%]">
                      <div className="bg-white rounded-2xl py-2 px-3 shadow-md">
                        <div className="flex gap-1 p-2">
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce"></span>
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                          <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>

            {!sessionFinished && (
              <div className={`bg-white border-t border-gray-200 p-4 ${isMobile ? 'fixed left-0 right-0 bottom-0 z-40' : 'sticky bottom-0'}`} style={isMobile ? { WebkitBackdropFilter: 'blur(6px)', backdropFilter: 'blur(6px)' } : undefined}>
                <div className="max-w-sm md:max-w-full mx-auto">
                  <form onSubmit={handleSubmitAnswer} className="w-full">
                    <div className="flex items-end gap-2">
                      <div className="flex-1 bg-gray-50 rounded-xl border-2 border-gray-200 focus-within:border-blue-500 transition-colors duration-300 flex items-end">
                        <textarea
                          ref={inputRef}
                          value={inputText}
                          onChange={(e) => {
                            setInputText(e.target.value);
                            // Auto-resize textarea
                            const el = e.target as HTMLTextAreaElement;
                            el.style.height = 'auto';
                            el.style.height = Math.min(el.scrollHeight, 240) + 'px';
                          }}
                          onKeyDown={handleInputKeyDown}
                          onPaste={handlePasteBlock}
                          onDrop={handleDropBlock}
                          placeholder="Type your answer here"
                          aria-label="Type your answer"
                          className="flex-1 resize-none border-none bg-transparent px-3 py-2 text-base outline-none placeholder-gray-400"
                          disabled={isLoading || sessionFinished}
                          rows={1}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={isListening ? stopListening : startListening}
                        title={isListening ? 'Stop listening' : 'Start speech input'}
                        className={`w-11 h-11 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 ${isListening ? 'bg-red-500 animate-pulse' : 'bg-gray-200 hover:bg-gray-300 hover:scale-105'} disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none self-end`}
                        disabled={isLoading || sessionFinished}
                      >
                        <Mic size={19} />
                      </button>
                      <button
                        type="submit"
                        title="Send answer (Enter)"
                        className="w-11 h-11 rounded-full bg-blue-500 text-white flex items-center justify-center cursor-pointer transition-all duration-300 hover:bg-blue-600 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none self-end"
                        disabled={isLoading || !inputText.trim() || sessionFinished}
                      >
                        <Send size={19} style={{ marginLeft: '-4px' }} />
                      </button>
                    </div>
                    {pasteBlocked && (
                      <div className="mt-2 text-sm text-red-600">Pasting is disabled — please type your answer.</div>
                    )}
                  </form>
                </div>
              </div>
            )}

            {sessionFinished && (
              <div className="bg-white border-t border-gray-200 p-8 text-center">
                <div>
                  <h3 className="text-green-500 m-0 mb-2 text-xl font-semibold">Session Complete!</h3>
                  <p className="text-gray-600 m-0 mb-6 leading-relaxed">Great job! You've finished this tutoring session.</p>
                  <button
                    onClick={handleEndSession}
                    className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-none rounded-full px-8 py-4 font-semibold text-base cursor-pointer transition-all duration-300 shadow-lg shadow-blue-500/40 hover:-translate-y-1 hover:shadow-blue-500/60 disabled:opacity-60 disabled:cursor-not-allowed"
                    disabled={isEndingSession}
                  >
                    {isEndingSession ? (
                      <span className="inline-flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                        </svg>
                        Ending...
                      </span>
                    ) : (
                      'Return Home'
                    )}
                  </button>
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