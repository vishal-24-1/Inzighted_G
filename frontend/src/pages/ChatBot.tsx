import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useLocation } from 'react-router-dom';
import { chatAPI } from '../utils/api';
import './ChatBot.css';

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

const ChatBot: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoSentRef = useRef(false); // Prevent duplicate auto-send

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

    // Add initial greeting message only once
    const initialMessage: Message = {
      id: '1',
      text: 'Hello! I\'m your AI assistant. How can I help you today?',
      isUser: false,
      timestamp: new Date()
    };
    setMessages([initialMessage]);
  }, []); // Empty dependency array - run only once on mount

  useEffect(() => {
    // Handle initial message from navigation
    const state = location.state as { initialMessage?: string };
    if (state?.initialMessage && !hasAutoSentRef.current) {
      hasAutoSentRef.current = true; // Mark as sent to prevent duplicates
      setInputText(state.initialMessage);
      // Auto-send the message after a short delay
      setTimeout(() => {
        if (state.initialMessage) {
          handleSendMessage(state.initialMessage);
        }
      }, 500);
    }
  }, [location.state]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages are added
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (messageOrEvent: React.FormEvent | string) => {
    let messageText: string;
    
    if (typeof messageOrEvent === 'string') {
      messageText = messageOrEvent;
    } else {
      messageOrEvent.preventDefault();
      messageText = inputText.trim();
    }
    
    if (!messageText || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: messageText,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response = await chatAPI.sendMessage(userMessage.text);
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.response,
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const startListening = () => {
    if (recognition && !isListening) {
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

  return (
    <div className="chatbot-container">
      <header className="chatbot-header">
        <div className="header-content">
          <h1>InzightEd AI</h1>
          <div className="user-info">
            <span>Welcome, {user?.name}</span>
            <button onClick={logout} className="logout-button">Logout</button>
          </div>
        </div>
      </header>

      <main className="chatbot-main">
        <div className="messages-container">
          <div className="messages-list">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.isUser ? 'user-message' : 'bot-message'}`}
              >
                <div className="message-content">
                  <div className="message-text">{message.text}</div>
                  <div className="message-time">{formatTime(message.timestamp)}</div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message bot-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="input-container">
          <form onSubmit={handleSendMessage} className="input-form">
            <div className="input-wrapper">
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Type here ..."
                className="message-input"
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={isListening ? stopListening : startListening}
                className={`voice-button ${isListening ? 'listening' : ''}`}
                disabled={isLoading}
              >
                <svg
                  width="24"
                  height="24"
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
                className="send-button"
                disabled={isLoading || !inputText.trim()}
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z"
                    fill="currentColor"
                  />
                </svg>
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatBot;