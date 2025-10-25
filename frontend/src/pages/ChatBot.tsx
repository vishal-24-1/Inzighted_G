import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useLocation } from 'react-router-dom';
import { chatAPI } from '../utils/api';
import { Mic, Send, LogOut } from 'lucide-react';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

// Avoid duplicating DOM SpeechRecognition types; use runtime checks and `any` for instances

const ChatBot: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasAutoSentRef = useRef(false); // Prevent duplicate auto-send

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
    <div className="flex flex-col h-screen bg-gray-50 font-sans">
      <header className="bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 text-white px-6 py-4 sticky top-0 shadow z-10">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <h1 className="text-lg font-semibold">InzightEd AI</h1>
          <div className="flex items-center gap-4 text-sm">
            <span className="hidden sm:inline">Welcome, {user?.name}</span>
            <button
              onClick={logout}
              className="inline-flex items-center gap-2 bg-white/20 border border-white/30 px-3 py-1 rounded-md text-white text-sm hover:bg-white/30"
            >
              <LogOut size={16} />
              <span className="sr-only">Logout</span>
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4">
        <div className="flex-1 overflow-hidden py-4">
          <div className="flex-1 overflow-y-auto px-2 flex flex-col gap-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex max-w-[80%] ${message.isUser ? 'self-end' : 'self-start'}`}
              >
                <div className={`rounded-2xl p-3 shadow ${message.isUser ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white' : 'bg-white text-gray-800'}`}>
                  <div className="whitespace-pre-wrap">{message.text}</div>
                  <div className={`text-xs mt-1 ${message.isUser ? 'text-white/80' : 'text-gray-500'}`}>{formatTime(message.timestamp)}</div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex">
                <div className="rounded-2xl p-3 bg-white text-gray-800 shadow">
                  <div className="flex items-center gap-2 px-2 py-1">
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse delay-75" />
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse delay-150" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="sticky bottom-0 bg-white border-t border-gray-200 p-4">
          <form onSubmit={handleSendMessage} className="max-w-full">
            <div className="flex items-center bg-gray-100 rounded-full p-2 border border-gray-200 focus-within:border-indigo-500">
              <input
                ref={inputRef}
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Type here ..."
                className="flex-1 bg-transparent outline-none px-4 text-base"
                disabled={isLoading}
              />

              <button
                type="button"
                onClick={isListening ? stopListening : startListening}
                className={`p-2 rounded-full text-gray-600 hover:bg-gray-200 ${isListening ? 'text-red-500 bg-red-50' : ''}`}
                disabled={isLoading}
                aria-pressed={isListening}
                title={isListening ? 'Stop listening' : 'Start voice input'}
              >
                <Mic size={18} />
              </button>

              <button
                type="submit"
                className="ml-2 p-2 rounded-full text-indigo-600 hover:bg-indigo-50 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isLoading || !inputText.trim()}
              >
                <Send size={18} />
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
};

export default ChatBot;