import React, { useState, useEffect } from 'react';
import { documentsAPI, tutoringAPI } from '../utils/api';
import { useNavigate } from 'react-router-dom';
import DocumentSelector from '../components/DocumentSelector';
import UserProfilePopup from '../components/UserProfilePopup';
import Sidebar from '../components/Sidebar';
import { FileText, Send, Menu, Rocket, Mic } from 'lucide-react';

// runtime feature detection is used below; avoid global type redeclarations

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<any | null>(null);
  const [showTutoringPopup, setShowTutoringPopup] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [showProfilePopup, setShowProfilePopup] = useState(false);
  const [lastUploadedDocumentId, setLastUploadedDocumentId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    // Initialize speech recognition if available
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
          setChatInput(transcript);
          setTimeout(() => setShowDocumentSelector(true), 500);
        }
      };

      recognitionInstance.onerror = (err: any) => {
        console.error('Speech recognition error:', err);
        setIsListening(false);
      };

      setRecognition(recognitionInstance);

      // cleanup
      return () => {
        try {
          recognitionInstance.onstart = null;
          recognitionInstance.onend = null;
          recognitionInstance.onresult = null;
          recognitionInstance.onerror = null;
          if (typeof recognitionInstance.abort === 'function') recognitionInstance.abort();
        } catch (e) {
          // ignore
        }
      };
    }
    return;
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB in bytes

    // Enforce maximum file size before attempting upload
    if (file.size > MAX_FILE_SIZE) {
      // Reset file input so user can select again
      event.target.value = '';
      // Exact required message
      alert('File size is too high. Please upload a file that is 5 MB or less.');
      return;
    }

    setUploading(true);
    try {
      const response = await documentsAPI.upload(file);
      // Reset file input
      event.target.value = '';

      // Store the document ID and show tutoring popup
      const documentId = response?.data?.document?.id;
      if (documentId) {
        setLastUploadedDocumentId(documentId);
        setShowTutoringPopup(true);
      } else {
        alert('Upload succeeded but no document id returned');
      }

    } catch (error: any) {
      alert('Upload failed: ' + (error?.response?.data?.error || error?.message || 'Unknown error'));
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

  const handleBoostMe = () => {
    navigate('/boost');
  };

  const handleVoiceRecord = () => {
    if (!recognition) return;
    try {
      if (!isListening && typeof recognition.start === 'function') {
        recognition.start();
      } else if (isListening && typeof recognition.stop === 'function') {
        recognition.stop();
      }
    } catch (err) {
      console.error('Voice record error:', err);
    }
  };

  const handleStartTutoring = async () => {
    if (!lastUploadedDocumentId) return;
    setStartingSession(true);
    try {
      const response = await tutoringAPI.startSession(lastUploadedDocumentId);
      const { session_id } = response.data;

      // Close popup and navigate to tutoring session
      setShowTutoringPopup(false);
      navigate(`/tutoring/${session_id}`);

    } catch (error: any) {
      alert('Failed to start tutoring session: ' + (error.response?.data?.error || 'Unknown error'));
    } finally {
      setStartingSession(false);
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
    <div className="w-full min-h-screen bg-white text-gray-900 p-4 pb-24 md:hidden flex flex-col">
      <header className="flex items-center justify-between mb-4">
        <button
          className="w-10 h-10 flex items-center justify-center bg-white rounded-full shadow-sm text-gray-700 border border-gray-100 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={18} />
        </button>

        <div className="flex-1" />
        <button
          className="inline-flex items-center gap-2 px-3 py-2 bg-white rounded-full shadow-sm text-gray-700 border border-gray-100 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          aria-label="Boost Me"
          onClick={handleBoostMe}
        >
          <Rocket size={16} className="text-blue-600" />
          <span className="text-sm font-medium">Boost Me</span>
        </button>
      </header>

      {/* Sidebar and backdrop */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onProfileClick={handleProfileClick} />

      <main className="flex-1 flex flex-col items-center justify-center space-y-6">

        <div className="w-full flex-1 flex flex-col items-center justify-center">
          <h2 className="text-2xl font-semibold mb-4">Let's get started</h2>

          <div className="w-full flex justify-center px-2">
            <button
              type="button"
              onClick={() => document.getElementById('file-upload')?.click()}
              className="w-40 aspect-square bg-white rounded-xl shadow-md p-4 flex flex-col items-center justify-center space-y-2 border border-gray-100"
            >
              <div className="w-12 h-12 flex items-center justify-center bg-gray-50 rounded-lg">
                <FileText size={20} className="text-gray-700" />
              </div>
              <span className="text-sm font-medium">Drop Your Notes</span>
              <p className="text-xs text-gray-500">Upload PDF, DOCX or TXT</p>
            </button>
          </div>
        </div>

        {/* chat input moved to fixed bottom bar */}

        {/* Hidden file input */}
        <input
          type="file"
          id="file-upload"
          accept=".pdf,.docx,.txt"
          onChange={handleFileUpload}
          disabled={uploading}
          className="hidden"
        />

        {/* Uploading overlay */}
        {uploading && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="bg-white rounded-lg p-6 flex flex-col items-center">
              <div className="loading-spinner" style={{ width: 48, height: 48 }}></div>
              <p className="mt-3 text-gray-700">Uploading and processing document...</p>
            </div>
          </div>
        )}
      </main>

      {/* Tutoring Ready Popup */}
      {showTutoringPopup && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm bg-white rounded-lg p-4 shadow">
            <h3 className="text-lg font-semibold">Ready for Tutoring!</h3>
            <p className="text-sm text-gray-600 mt-2">Your document has been processed successfully. Would you like to start a tutoring session?</p>
            <div className="mt-4 flex gap-2">
              <button
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg"
                onClick={handleStartTutoring}
                disabled={startingSession}
              >
                {startingSession ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="loading-spinner" style={{ width: 20, height: 20, borderWidth: 2 }}></div>
                    <span>Starting...</span>
                  </div>
                ) : (
                  'Start Session'
                )}
              </button>
              <button
                className="flex-1 bg-gray-100 text-gray-700 py-2 rounded-lg"
                onClick={handleCloseTutoringPopup}
                disabled={startingSession}
              >
                Later
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Document Selector Modal */}
      {showDocumentSelector && (
        <div className="fixed inset-0 z-40 flex items-end md:items-center justify-center">
          <DocumentSelector
            onDocumentSelect={handleDocumentSelect}
            onCancel={handleCancelDocumentSelection}
            startingSession={startingSession}
          />
        </div>
      )}

      {/* User Profile Popup */}
      {showProfilePopup && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <UserProfilePopup onClose={handleCloseProfilePopup} />
        </div>
      )}

      {/* Fixed bottom chat input bar (mobile) */}
      <div className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-200 p-4 z-30 md:hidden">
        <form onSubmit={handleChatSubmit} className="flex items-center gap-2 max-w-3xl mx-auto">
          <div className="flex-1 h-11 bg-gray-50 rounded-full border-2 border-gray-200 focus-within:border-blue-500 transition-colors duration-300 flex items-center">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Type here ..."
              className="flex-1 border-none bg-transparent px-3 text-base outline-none placeholder-gray-400"
            />
          </div>
          <button
            type="button"
            onClick={handleVoiceRecord}
            className={`w-11 h-11 rounded-full flex items-center justify-center cursor-pointer transition-all duration-300 ${isListening ? 'bg-red-500 animate-pulse' : 'bg-gray-200 hover:bg-gray-300 hover:scale-105'} disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
            disabled={uploading}
          >
            <Mic size={19} />
          </button>
          <button
            type="submit"
            className="w-11 h-11 rounded-full bg-blue-500 text-white flex items-center justify-center cursor-pointer transition-all duration-300 hover:bg-blue-600 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            disabled={!chatInput.trim() || uploading}
          >
            <Send size={19} style={{ marginLeft: '-4px' }} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default Home;