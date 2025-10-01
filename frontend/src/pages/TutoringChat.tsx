import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { tutoringAPI } from '../utils/api';
import DocumentSelector from '../components/DocumentSelector';
import './TutoringChat.css';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognition, ev: Event) => any) | null;
}

declare global {
  interface Window {
    SpeechRecognition: {
      new(): SpeechRecognition;
    };
    webkitSpeechRecognition: {
      new(): SpeechRecognition;
    };
  }
}

const TutoringChat: React.FC = () => {
  const { user } = useAuth();
  const { sessionId } = useParams<{ sessionId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [sessionFinished, setSessionFinished] = useState(false);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [sessionDocument, setSessionDocument] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Initialize speech recognition
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';
      
      recognitionInstance.onstart = () => {
        setIsListening(true);
      };
      
      recognitionInstance.onend = () => {
        setIsListening(false);
      };
      
      recognitionInstance.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
        inputRef.current?.focus();
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event);
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
    }

    // Load session messages when component mounts
    if (sessionId) {
      loadSessionMessages();
    } else {
      // Check if we should show document selector for new session
      const selectDoc = searchParams.get('select_doc');
      if (selectDoc === 'true') {
        setShowDocumentSelector(true);
      }
    }
  }, [sessionId, searchParams]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages are added
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
    } catch (error: any) {
      console.error('Failed to load session messages:', error);
      if (error.response?.status === 404) {
        alert('Tutoring session not found. Redirecting to home.');
        navigate('/');
      }
    }
  };

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputText.trim() || isLoading || sessionFinished || !sessionId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText.trim(),
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
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
        // Add the next question
        const nextQuestion: Message = {
          id: response.data.next_question.id,
          text: response.data.next_question.text,
          isUser: false,
          timestamp: new Date(response.data.next_question.created_at)
        };
        setMessages(prev => [...prev, nextQuestion]);
      }
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error('Tutoring error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndSession = async () => {
    if (!sessionId) return;
    
    try {
      await tutoringAPI.endSession(sessionId);
      navigate('/');
    } catch (error: any) {
      console.error('Failed to end session:', error);
      // Still navigate home even if end request fails
      navigate('/');
    }
  };

  const handleDocumentSelect = async (documentId: string | null) => {
    setShowDocumentSelector(false);
    
    try {
      const response = await tutoringAPI.startSession(documentId || undefined);
      const { session_id } = response.data;
      
      // Navigate to the new session
      navigate(`/tutoring/${session_id}`, { replace: true });
      
    } catch (error: any) {
      console.error('Failed to start tutoring session:', error);
      alert('Failed to start tutoring session: ' + (error.response?.data?.error || 'Unknown error'));
      navigate('/');
    }
  };

  const handleCancelDocumentSelection = () => {
    setShowDocumentSelector(false);
    navigate('/');
  };

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

  // Show document selector if no session ID is provided
  if (!sessionId && showDocumentSelector) {
    return (
      <DocumentSelector
        onDocumentSelect={handleDocumentSelect}
        onCancel={handleCancelDocumentSelection}
      />
    );
  }

  // Redirect to home if no session ID and not showing selector
  if (!sessionId) {
    navigate('/');
    return null;
  }

  return (
    <div className="tutoring-container">
      <header className="tutoring-header">
        <div className="header-content">
          <div className="header-left">
            <h1>AI Tutor</h1>
            {sessionDocument && (
              <p className="document-name">Document: {sessionDocument}</p>
            )}
          </div>
          <div className="header-actions">
            <button 
              onClick={handleEndSession}
              className="end-session-button"
            >
              End Session
            </button>
          </div>
        </div>
      </header>

      <main className="tutoring-main">
        <div className="messages-container">
          <div className="messages-list">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.isUser ? 'user-message' : 'tutor-message'}`}
              >
                <div className="message-content">
                  <div className="message-avatar">
                    {message.isUser ? 'S' : 'T'}
                  </div>
                  <div className="message-bubble">
                    <div className="message-text">{message.text}</div>
                    <div className="message-time">{formatTime(message.timestamp)}</div>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message tutor-message">
                <div className="message-content">
                  <div className="message-avatar">T</div>
                  <div className="message-bubble">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {!sessionFinished && (
          <div className="input-container">
            <div className="input-header">
              <p>Please answer the question above:</p>
            </div>
            <form onSubmit={handleSubmitAnswer} className="input-form">
              <div className="input-wrapper">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Type your answer here..."
                  className="answer-input"
                  disabled={isLoading || sessionFinished}
                />
                <button
                  type="button"
                  onClick={isListening ? stopListening : startListening}
                  className={`voice-button ${isListening ? 'listening' : ''}`}
                  disabled={isLoading || sessionFinished}
                >
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M12 14C13.66 14 15 12.66 15 11V5C15 3.34 13.66 2 12 2C10.34 2 9 3.34 9 5V11C9 12.66 10.34 14 12 14Z"
                      fill="currentColor"
                    />
                    <path
                      d="M17 11C17 14.53 14.39 17.44 11 17.93V21H13C13.55 21 14 21.45 14 22C14 22.55 13.55 23 13 23H11C10.45 23 10 22.55 10 22C10 21.45 10.45 21 11 21H13V17.93C9.61 17.44 7 14.53 7 11H5C5 15.49 8.23 19.16 12.44 19.88C12.78 19.95 13.22 19.95 13.56 19.88C17.77 19.16 21 15.49 21 11H19C19 11 17 11 17 11Z"
                      fill="currentColor"
                    />
                  </svg>
                </button>
                <button
                  type="submit"
                  className="submit-button"
                  disabled={isLoading || !inputText.trim() || sessionFinished}
                >
                  Submit
                </button>
              </div>
            </form>
          </div>
        )}

        {sessionFinished && (
          <div className="session-complete">
            <div className="complete-content">
              <h3>Session Complete!</h3>
              <p>Great job! You've finished this tutoring session.</p>
              <button 
                onClick={handleEndSession}
                className="return-home-button"
              >
                Return Home
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default TutoringChat;