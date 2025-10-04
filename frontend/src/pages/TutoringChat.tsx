import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { tutoringAPI } from '../utils/api';
import DocumentSelector from '../components/DocumentSelector';
import { Mic, Send } from 'lucide-react';

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
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [sessionDocument, setSessionDocument] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
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
          setInputText(transcript);
          inputRef.current?.focus();
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
        alert('Tutoring session not found.');
        if (onEndSession) onEndSession();
        else navigate('/');
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
      if (onEndSession) onEndSession();
      else navigate('/');
    } catch (error: any) {
      console.error('Failed to end session:', error);
      // Still return to parent or navigate home even if end request fails
      if (onEndSession) onEndSession();
      else navigate('/');
    }
  };

  const handleDocumentSelect = async (documentId: string | null) => {
    setShowDocumentSelector(false);

    try {
      const response = await tutoringAPI.startSession(documentId || undefined);
      const { session_id } = response.data;
      // If parent provided a handler, call it so the parent can render the session in-place.
      if (onStartSession) {
        onStartSession(session_id);
      } else {
        // Navigate to the new session route
        navigate(`/tutoring/${session_id}`, { replace: true });
      }

    } catch (error: any) {
      console.error('Failed to start tutoring session:', error);
      alert('Failed to start tutoring session: ' + (error.response?.data?.error || 'Unknown error'));
      if (onEndSession) onEndSession();
      else navigate('/');
    }
  };

  const handleCancelDocumentSelection = () => {
    setShowDocumentSelector(false);
    if (onEndSession) onEndSession();
    else navigate('/');
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

  // If embedded (parent provided onEndSession) and no session ID, simply render nothing.
  if (!sessionId) {
    if (onEndSession) return null;
    // Redirect to home if no session ID and not embedded
    navigate('/');
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 font-sans max-w-sm mx-auto shadow-xl flex flex-col">
      <header className="bg-white border-b text-gray-900 p-4 sticky top-0 z-20">
        <div className="flex justify-between items-center">
          <h1 className="text-lg font-semibold m-0 truncate max-w-32">{sessionDocument || 'AI Tutor'}</h1>
          <button
            onClick={handleEndSession}
            className="bg-red-100 text-red-600 font-bold border border-red-600 rounded-xl px-3 py-1.5 text-sm font-medium cursor-pointer transition-all duration-300 hover:bg-red-300 hover:-translate-y-0.5 shadow-sm"
          >
            End Session
          </button>
        </div>
      </header>

      <main className="flex-1 flex flex-col h-[calc(100vh-80px)]">
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex w-full ${message.isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%]`}>
                  <div className={`bg-white rounded-2xl py-2 px-3 shadow-md relative hover:shadow-lg transition-shadow duration-200 ${message.isUser ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' : 'bg-white text-gray-800'}`}>
                    <div className="text-sm leading-relaxed text-left">{message.text}</div>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex w-full justify-start">
                <div className="max-w-[80%]">
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
          <div className="bg-white border-t border-gray-200 p-4 sticky bottom-0">
            <form onSubmit={handleSubmitAnswer} className="w-full">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-11 bg-gray-50 rounded-full border-2 border-gray-200 focus-within:border-blue-500 transition-colors duration-300 flex items-center">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type your answer here..."
                    className="flex-1 border-none bg-transparent px-3 text-base outline-none placeholder-gray-400"
                    disabled={isLoading || sessionFinished}
                  />
                </div>
                <button
                  type="button"
                  onClick={isListening ? stopListening : startListening}
                  className={`w-11 h-11 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 ${isListening ? 'bg-red-500 animate-pulse' : 'bg-gray-200 hover:bg-gray-300 hover:scale-105'} disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
                  disabled={isLoading || sessionFinished}
                >
                  <Mic size={19} />
                </button>
                <button
                  type="submit"
                  className="w-11 h-11 rounded-full bg-blue-500 text-white flex items-center justify-center cursor-pointer transition-all duration-300 hover:bg-blue-600 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  disabled={isLoading || !inputText.trim() || sessionFinished}
                >
                  <Send size={19} style={{ marginLeft: '-4px' }} />
                </button>
              </div>
            </form>
          </div>
        )}

        {sessionFinished && (
          <div className="bg-white border-t border-gray-200 p-8 text-center">
            <div>
              <h3 className="text-green-500 m-0 mb-2 text-xl font-semibold">Session Complete!</h3>
              <p className="text-gray-600 m-0 mb-6 leading-relaxed">Great job! You've finished this tutoring session.</p>
              <button
                onClick={handleEndSession}
                className="bg-gradient-to-br from-blue-500 to-blue-600 text-white border-none rounded-full px-8 py-4 font-semibold text-base cursor-pointer transition-all duration-300 shadow-lg shadow-blue-500/40 hover:-translate-y-1 hover:shadow-blue-500/60"
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