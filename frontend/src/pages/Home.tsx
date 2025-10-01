import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { documentsAPI, tutoringAPI } from '../utils/api';
import { useNavigate } from 'react-router-dom';
import DocumentSelector from '../components/DocumentSelector';
import UserProfilePopup from '../components/UserProfilePopup';
import './Home.css';

interface Document {
  id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  status: string;
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

const Home: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [showTutoringPopup, setShowTutoringPopup] = useState(false);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [showProfilePopup, setShowProfilePopup] = useState(false);
  const [lastUploadedDocumentId, setLastUploadedDocumentId] = useState<string | null>(null);

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
        setChatInput(transcript);
        // Auto-open document selector for tutoring with the transcript
        setTimeout(() => {
          setShowDocumentSelector(true);
        }, 500);
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event);
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
    }
  }, [navigate]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const response = await documentsAPI.upload(file);
      // Reset file input
      event.target.value = '';
      
      // Store the document ID and show tutoring popup
      const documentId = response.data.document.id;
      setLastUploadedDocumentId(documentId);
      setShowTutoringPopup(true);
      
    } catch (error: any) {
      alert('Upload failed: ' + (error.response?.data?.error || 'Unknown error'));
    } finally {
      setUploading(false);
    }
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (chatInput.trim()) {
      // Open document selector for tutoring instead of navigating to chat
      setShowDocumentSelector(true);
    }
  };

  const handleUploadQP = () => {
    alert('Upload QP functionality coming soon!');
  };

  const handleBoostMe = () => {
    navigate('/boost');
  };

  const handleVoiceRecord = () => {
    if (recognition && !isListening) {
      recognition.start();
    }
  };

  const handleStartTutoring = async () => {
    if (!lastUploadedDocumentId) return;
    
    try {
      const response = await tutoringAPI.startSession(lastUploadedDocumentId);
      const { session_id } = response.data;
      
      // Close popup and navigate to tutoring session
      setShowTutoringPopup(false);
      navigate(`/tutoring/${session_id}`);
      
    } catch (error: any) {
      alert('Failed to start tutoring session: ' + (error.response?.data?.error || 'Unknown error'));
    }
  };

  const handleCloseTutoringPopup = () => {
    setShowTutoringPopup(false);
    setLastUploadedDocumentId(null);
  };

  const handleDocumentSelect = async (documentId: string | null) => {
    setShowDocumentSelector(false);
    
    try {
      const response = await tutoringAPI.startSession(documentId || undefined);
      const { session_id } = response.data;
      
      // Navigate to tutoring session
      navigate(`/tutoring/${session_id}`);
      
      // Clear the chat input after successful session creation
      setChatInput('');
      
    } catch (error: any) {
      alert('Failed to start tutoring session: ' + (error.response?.data?.error || 'Unknown error'));
    }
  };

  const handleCancelDocumentSelection = () => {
    setShowDocumentSelector(false);
  };

  const handleProfileClick = () => {
    setShowProfilePopup(true);
  };

  const handleCloseProfilePopup = () => {
    setShowProfilePopup(false);
  };

  return (
    <div className="home-container">
      <header className="home-header">
        <div className="header-content">
          <div className="header-left">
            <div className="menu-icon" title="Menu">
              ≡
            </div>
          </div>
          <div className="header-center">
            <h1 className="app-title">InzightEd</h1>
          </div>
          <div className="header-right">
            <div 
              className="profile-icon" 
              title={`${user?.name}'s Profile`}
              onClick={handleProfileClick}
            >
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
          </div>
        </div>
      </header>

      <main className="home-main">
        <div className="greeting-section">
          <h2 className="greeting">What's the plan today?</h2>
        </div>

        <div className="action-cards">
          <div className="card-row">
            <div className="action-card" onClick={() => document.getElementById('file-upload')?.click()}>
              <div className="card-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h3>Drop Your Notes</h3>
            </div>
            
            <div className="action-card" onClick={handleUploadQP}>
              <div className="card-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="7,10 12,15 17,10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="12" y1="15" x2="12" y2="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h3>Upload QP</h3>
            </div>
          </div>

          <div className="boost-button" onClick={handleBoostMe}>
            BOOST ME
          </div>
        </div>

        <div className="motivation-text">
          <p>Last time you nailed Bio, but Chem needs love!</p>
        </div>

        <div className="voice-record-section">
          <div 
            className={`voice-button ${isListening ? 'listening' : ''}`}
            onClick={handleVoiceRecord}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 14C13.66 14 15 12.66 15 11V5C15 3.34 13.66 2 12 2C10.34 2 9 3.34 9 5V11C9 12.66 10.34 14 12 14Z" fill="white"/>
              <path d="M17 11C17 14.53 14.39 17.44 11 17.93V21H13C13.55 21 14 21.45 14 22C14 22.55 13.55 23 13 23H11C10.45 23 10 22.55 10 22C10 21.45 10.45 21 11 21H13V17.93C9.61 17.44 7 14.53 7 11H5C5 15.49 8.23 19.16 12.44 19.88C12.78 19.95 13.22 19.95 13.56 19.88C17.77 19.16 21 15.49 21 11H19C19 11 17 11 17 11Z" fill="white"/>
            </svg>
          </div>
        </div>

        <div className="chat-input-section">
          <form onSubmit={handleChatSubmit} className="chat-form">
            <div className="chat-input-wrapper">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type here ..."
                className="chat-input"
              />
              <button type="submit" className="chat-send-button">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </form>
        </div>

        {/* Hidden file input */}
        <input
          type="file"
          id="file-upload"
          accept=".pdf,.docx,.txt"
          onChange={handleFileUpload}
          disabled={uploading}
          style={{ display: 'none' }}
        />
      </main>

      {/* Tutoring Ready Popup */}
      {showTutoringPopup && (
        <div className="popup-overlay">
          <div className="popup-content">
            <h3>Ready for Tutoring!</h3>
            <p>Your document has been processed successfully. Would you like to start a tutoring session?</p>
            <div className="popup-buttons">
              <button 
                className="btn-primary" 
                onClick={handleStartTutoring}
              >
                Start Session
              </button>
              <button 
                className="btn-secondary" 
                onClick={handleCloseTutoringPopup}
              >
                Later
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Selector Modal */}
      {showDocumentSelector && (
        <DocumentSelector
          onDocumentSelect={handleDocumentSelect}
          onCancel={handleCancelDocumentSelection}
        />
      )}

      {/* User Profile Popup */}
      {showProfilePopup && (
        <UserProfilePopup onClose={handleCloseProfilePopup} />
      )}
    </div>
  );
};

export default Home;