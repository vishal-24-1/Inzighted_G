import React, { useState, useEffect, useRef } from 'react';
import { documentsAPI, tutoringAPI } from '../utils/api';
import { useNavigate } from 'react-router-dom';
import DocumentSelector from '../components/DocumentSelector';
import UserProfilePopup from '../components/UserProfilePopup';
import Sidebar from '../components/Sidebar';
import { FileText, Send, Menu, Mic } from 'lucide-react';

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
  const [notificationMessage, setNotificationMessage] = useState<string | null>(null);
  const notificationTimerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

      // Store the document ID and poll backend for processing completion
      const documentId = response?.data?.document?.id;
      if (documentId) {
        setLastUploadedDocumentId(documentId);

        // Poll document status until 'completed' or timeout
        const maxWaitMs = 2 * 60 * 1000; // 2 minutes
        const start = Date.now();
        let attempt = 0;

        const poll = async (): Promise<void> => {
          attempt += 1;
          try {
            const statusRes = await documentsAPI.status(documentId);
            const status = statusRes?.data?.status;

            if (status === 'completed') {
              setShowTutoringPopup(true);
              setUploading(false);
              return;
            }

            if (status === 'failed') {
              alert('Document processing failed on the server. Please try uploading again.');
              setUploading(false);
              return;
            }

            // Not completed yet - check timeout
            if (Date.now() - start >= maxWaitMs) {
              // Timeout - show a gentle message and provide option to open document selector
              setShowDocumentSelector(true);
              setUploading(false);
              return;
            }

            // Exponential backoff: base 1s, cap 8s
            const delay = Math.min(1000 * Math.pow(2, attempt - 1), 8000);
            setTimeout(poll, delay + Math.floor(Math.random() * 500));

          } catch (err) {
            console.error('Error polling document status:', err);
            // On error, if still within timeout, retry after short delay
            if (Date.now() - start < maxWaitMs) {
              setTimeout(poll, 2000);
            } else {
              setShowDocumentSelector(true);
              setUploading(false);
            }
          }
        };

        // Start polling
        poll();

      } else {
        alert('Upload succeeded but no document id returned');
        setUploading(false);
      }

    } catch (error: any) {
      alert('Upload failed: ' + (error?.response?.data?.error || error?.message || 'Unknown error'));
      setUploading(false);
    }
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (chatInput.trim()) {
      // Instead of showing a toast, open the document selector modal
      setShowDocumentSelector(true);
      // Clear the chat input
      setChatInput('');
    }
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

  const handleDocumentSelect = async (documentIds: string[]) => {
    setShowDocumentSelector(false);

    try {
      // If documentIds is empty, start a general session. If multiple ids provided, pass them.
      const payload = documentIds.length === 0 ? undefined : (documentIds.length === 1 ? documentIds[0] : documentIds);
      const response = await tutoringAPI.startSession(payload as any);
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
    <>
      {/* Mobile view (used for all screen sizes) */}
      <div className="w-full min-h-screen bg-white text-gray-900 p-4 pb-24 flex flex-col">
        <header className="flex items-center justify-between mb-4">
          <button
            className="md:hidden w-10 h-10 flex items-center justify-center bg-white rounded-full shadow-sm text-gray-700 border border-gray-100 hover:bg-gray-50"
            aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={18} />
          </button>

          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowDocumentSelector(true)}
              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 text-gray-700 rounded-full shadow-sm hover:bg-gray-50"
              aria-haspopup="dialog"
              aria-label="Open Library"
            >
              <FileText size={16} />
              <span className="text-sm font-medium">Library</span>
            </button>
          </div>
        </header>

        {/* Sidebar and backdrop (mobile/off-canvas) */}
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black/40 z-30" onClick={() => setSidebarOpen(false)} />
        )}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onProfileClick={handleProfileClick} />

        {/* Static desktop sidebar (always visible on md+) */}
        <div className="hidden md:block md:flex-shrink-0">
          <Sidebar isOpen={true} inlineOnDesktop={true} onProfileClick={handleProfileClick} />
        </div>

        <main className="flex-1 flex flex-col items-center justify-center space-y-6 md:ml-72">

          <div className="w-full flex-1 flex flex-col items-center justify-center">
            <h2 className="text-2xl font-semibold mb-4">Let's get started</h2>

            <div className="w-full flex justify-center px-2">
              <button
                type="button"
                onClick={() => { if (!uploading) fileInputRef.current?.click(); }}
                className="w-40 aspect-square bg-white rounded-xl shadow-md p-4 flex flex-col items-center justify-center space-y-2 border border-gray-100 disabled:opacity-60 disabled:cursor-not-allowed"
                disabled={uploading}
                aria-busy={uploading}
              >
                <div className="w-12 h-12 flex items-center justify-center bg-gray-50 rounded-lg">
                  <FileText size={20} className="text-gray-700" />
                </div>
                {!uploading ? (
                  <>
                    <span className="text-sm font-medium">Drop Your Notes</span>
                    <p className="text-xs text-gray-500">Upload PDF, DOCX or TXT</p>
                  </>
                ) : (
                  <div className="flex flex-col items-center">
                    <div className="inline-flex items-center gap-2">
                      <svg className="animate-spin h-4 w-4 text-gray-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                      </svg>
                      <span className="text-sm font-medium">Uploading...</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Processing may take a minute</p>
                  </div>
                )}
              </button>
            </div>
          </div>

          {/* Hidden file input */}
          <input
            type="file"
            id="file-upload"
            accept=".pdf,.docx,.txt"
            onChange={handleFileUpload}
            ref={fileInputRef}
            disabled={uploading}
            className="hidden"
          />

          {/* Notification toast removed; chat submit now opens DocumentSelector */}

          {/* Uploading overlay */}
          {uploading && (
            <div className="fixed inset-0 z-50 min-h-screen flex items-center justify-center bg-black/40" role="status" aria-live="polite" aria-busy={uploading}>
              <div className="bg-white rounded-lg p-6 flex flex-col items-center">
                {/* Accessible spinner */}
                <svg className="animate-spin h-12 w-12 text-gray-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                </svg>
                <p className="mt-3 text-gray-700">Uploading and processing document...</p>
                <span className="sr-only">Uploading and processing document</span>
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
                    <div className="flex items-center justify-center">
                      <div className="animate-spin h-6 w-6 border-2 border-white/60 border-t-white rounded-full mx-auto" aria-hidden="true" />
                      <span className="sr-only">Starting</span>
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
          <DocumentSelector
            onDocumentSelect={handleDocumentSelect}
            onCancel={handleCancelDocumentSelection}
            startingSession={startingSession}
          />
        )}

        {/* User Profile Popup */}
        {showProfilePopup && (
          <div className="fixed inset-0 z-40 flex items-center justify-center">
            <UserProfilePopup onClose={handleCloseProfilePopup} />
          </div>
        )}

        {/* Fixed bottom chat input bar (mobile) — adapts on md+ to sit after the sidebar and look like a floating input */}
        <div className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-200 p-4 z-40 md:left-72 md:right-6 md:bottom-6 md:top-auto md:w-auto md:bg-transparent md:border-0 md:p-0">
          <form onSubmit={handleChatSubmit} className="flex items-center gap-2 max-w-3xl mx-auto md:bg-white md:rounded-full md:border md:border-gray-200 md:p-3 md:shadow-lg">
            <div className="flex-1 h-11 bg-gray-50 rounded-full border-2 border-gray-200 transition-colors duration-300 flex items-center">
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

      {/* Desktop view removed - mobile view is used for all screen sizes */}
    </>
  );
};

export default Home;