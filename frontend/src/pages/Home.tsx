import React, { useState, useEffect, useRef } from 'react';
import { documentsAPI, tutoringAPI } from '../utils/api';
import { useNavigate, useLocation } from 'react-router-dom';
import DocumentSelector from '../components/DocumentSelector';
import UserProfilePopup from '../components/UserProfilePopup';
import Sidebar from '../components/Sidebar';
import { FileText, Send, Rocket, UserRound, Mic, X } from 'lucide-react';
import MobileDock from '../components/MobileDock';
import UploadPromptModal from '../components/UploadPromptModal';
import logo from '../logo.svg';

// runtime feature detection is used below; avoid global type redeclarations

const Home: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
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
  const [showUploadPromptModal, setShowUploadPromptModal] = useState(false);
  const [duplicateDocument, setDuplicateDocument] = useState<any | null>(null);
  const [preselectDocumentId, setPreselectDocumentId] = useState<string | null>(null);

  useEffect(() => {
    // If another page navigated here with intent to open the upload prompt, handle it.
    try {
      const state: any = (location && (location as any).state) || {};
      if (state.openUploadPrompt) {
        setShowUploadPromptModal(true);
        // Clear the history state so the modal doesn't reopen on back/forward navigation
        if (window.history && typeof window.history.replaceState === 'function') {
          const newState = { ...(window.history.state || {}), ...(state || {}) };
          // remove our flag
          delete newState.openUploadPrompt;
          try { window.history.replaceState(newState, document.title); } catch (e) { /* ignore */ }
        }
      }
    } catch (e) {
      // ignore
    }

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
      // If backend returned 409 Conflict, the document already exists for this user.
      if (error?.response?.status === 409) {
        const existingDoc = error.response?.data?.document;
        // Reset file input
        event.target.value = '';
        // Show a modal offering two choices: upload a different document or use the existing one from library
        setDuplicateDocument(existingDoc || { id: null, filename: 'this document' });
        // store preselect id so we can pass it into DocumentSelector when user chooses library
        setPreselectDocumentId(existingDoc?.id ?? null);
        setUploading(false);
        return;
      }

      alert('Upload failed: ' + (error?.response?.data?.error || error?.message || 'Unknown error'));
      setUploading(false);
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
    // Close selector and show the same uploading/processing overlay used for uploads
    setShowDocumentSelector(false);
    // clear any preselect id now that user made a choice
    setPreselectDocumentId(null);
    setUploading(true);
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
    } finally {
      setUploading(false);
    }
  };

  const handleCancelDocumentSelection = () => {
    setShowDocumentSelector(false);
    // clear any pending preselect so it doesn't persist
    setPreselectDocumentId(null);
  };

  const handleProfileClick = () => {
    setShowProfilePopup(true);
  };

  const handleCloseProfilePopup = () => {
    setShowProfilePopup(false);
  };

  return (
    <>
      {/* Decorative grid background (very back). Fixed so it sits behind the whole app including MobileDock. */}
      <div
        aria-hidden
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 70%), repeating-linear-gradient(0deg, rgba(0,0,0,0.03) 0 1px, transparent 1px 28px), repeating-linear-gradient(90deg, rgba(0,0,0,0.03) 0 1px, transparent 1px 28px)`,
          backgroundSize: '100% 100%, auto, auto',
          opacity: 0.9,
        }}
      />

      {/* Mobile view (used for all screen sizes) */}
      <div className="relative w-full min-h-screen text-gray-900 p-4 pb-24 flex flex-col overflow-hidden">
        <header className="relative z-20 mb-4">
          <div className="flex items-center justify-between">
            <button
              className="md:hidden w-10 h-10 flex items-center justify-center rounded-full shadow-sm text-gray-700 bg-gray-100 hover:bg-gray-50"
              aria-label="Open profile"
              onClick={handleProfileClick}
            >
              <UserRound size={18} strokeWidth={2.5} />
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowDocumentSelector(true)}
                className="md:hidden w-10 h-10 flex items-center justify-center rounded-full shadow-sm text-gray-700 bg-gray-100 hover:bg-gray-50"
                aria-haspopup="dialog"
                aria-label="Open Library"
              >
                <FileText size={18} strokeWidth={2.5} />
              </button>
            </div>
          </div>

          {/* Centered logo: absolutely positioned so it's centered regardless of left/right widths */}
          <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
            <a className="flex items-center gap-3 pointer-events-auto">
              <img src={logo} alt="InzightEd" className="h-5 w-auto mt-1" />
            </a>
          </div>
        </header>

        {/* Sidebar and backdrop (mobile/off-canvas) */}
        {sidebarOpen && (
          <div className="fixed inset-0 bg-black/40 z-30" onClick={() => setSidebarOpen(false)} />
        )}
        {/* Mobile/off-canvas sidebar: ensure it sits above the bottom chat bar (z-40) by using z-50 */}
        {sidebarOpen && (
          <div className="fixed inset-y-0 left-0 z-40">
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onProfileClick={handleProfileClick} />
          </div>
        )}

        {/* Static desktop sidebar (always visible on md+) */}
        <div className="hidden md:block md:flex-shrink-0 md:relative md:z-40">
          <Sidebar isOpen={true} inlineOnDesktop={true} onProfileClick={handleProfileClick} />
        </div>

        <main className="flex-1 flex flex-col items-center justify-center space-y-6 md:ml-72">

            {/* Small notification toast for duplicate-upload / info messages */}
            {notificationMessage && (
              <div className="fixed top-6 left-1/2 transform -translate-x-1/2 z-50">
                <div className="bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-2 rounded shadow">
                  {notificationMessage}
                </div>
              </div>
            )}

          <div className="w-full flex-1 flex flex-col items-center justify-center -mt-20 md:-mt-8">
            <h2 className="text-xl text-center mb-4">Learn more <br /> about yourself</h2>

            <div className="w-full flex justify-center px-2">
              <div className="flex justify-center">
                {/* Boost Me button (styled like upload card) */}
                <button
                  type="button"
                  onClick={() => navigate('/boost')}
                  className="w-40 aspect-square rounded-xl p-4 flex flex-col items-center justify-center space-y-2 bg-gray-100 disabled:opacity-60 disabled:cursor-not-allowed"
                  aria-label="Boost Me"
                  disabled={uploading}
                >
                  <div className="w-12 h-12 flex items-center justify-center bg-blue-500 rounded-lg">
                    <Rocket size={20} className="text-white" />
                  </div>
                  <span className="text-sm font-medium text-gray-900">Boost Me</span>
                  <p className="text-xs text-gray-500">To know more about yourself & crack your exams</p>
                </button>
              </div>
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
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
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
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <DocumentSelector
              onDocumentSelect={handleDocumentSelect}
              onCancel={handleCancelDocumentSelection}
              onUpload={() => fileInputRef.current?.click()}
              // show the modal's "starting" UI when either a session start is in progress
              // or the global "uploading" overlay is active so the UX matches the home page
              startingSession={startingSession || uploading}
              preselectDocumentId={preselectDocumentId ?? undefined}
            />
          </div>
        )}

        {/* User Profile Popup */}
        {showProfilePopup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <UserProfilePopup onClose={handleCloseProfilePopup} />
          </div>
        )}

        <UploadPromptModal
          isOpen={showUploadPromptModal}
          onClose={() => setShowUploadPromptModal(false)}
          onUpload={() => { setShowUploadPromptModal(false); fileInputRef.current?.click(); }}
          onOpenLibrary={() => { setShowUploadPromptModal(false); setShowDocumentSelector(true); }}
          uploading={uploading}
        />

        {/* Duplicate detected modal */}
        {duplicateDocument && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-md bg-white rounded-lg p-6 shadow">
              <h3 className="text-lg font-semibold">Document Already Uploaded</h3>
              <p className="text-sm text-gray-600 mt-2">We found a previously uploaded copy of <strong>{duplicateDocument?.filename}</strong> in your library.</p>
              <div className="mt-4 flex gap-3">
                <button
                  className="flex-1 bg-gray-100 text-gray-800 py-2 rounded-lg"
                  onClick={() => {
                    // Let user upload a different document
                    setDuplicateDocument(null);
                    // open file picker
                    fileInputRef.current?.click();
                  }}
                >
                  Upload different document
                </button>
                <button
                  className="flex-1 bg-blue-600 text-white py-2 rounded-lg"
                  onClick={() => {
                    // Open library with this document preselected
                    setPreselectDocumentId(duplicateDocument?.id ?? null);
                    setShowDocumentSelector(true);
                    setDuplicateDocument(null);
                  }}
                >
                  Use document in library
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Fixed bottom chat input bar (mobile) — adapts on md+ to sit after the sidebar and look like a floating input */}
        <div className="fixed bottom-20 left-0 w-full bg-white px-4 pb-2 z-20 md:left-72 md:right-6 md:bottom-6 md:top-auto md:w-auto md:bg-transparent md:border-0 md:p-0">
          <div className="flex items-center gap-2 max-w-3xl mx-auto md:bg-white md:rounded-full md:border md:border-gray-200 md:p-3 md:shadow-lg">
            <div
              className="flex-1 h-14 bg-gray-100 rounded-full transition-colors duration-300 flex items-center px-3"
              onClick={() => setShowUploadPromptModal(true)}
            >
              <input
                type="text"
                value={chatInput}
                readOnly
                // Keep click to open the upload prompt, but prevent focus so
                // the cursor doesn't appear and mobile keyboards don't open.
                onClick={() => setShowUploadPromptModal(true)}
                onFocus={(e) => e.currentTarget.blur()}
                onMouseDown={(e) => e.preventDefault()}
                onTouchStart={(e) => e.preventDefault()}
                placeholder="Drop your notes to get started..."
                className="flex-1 border-none bg-transparent px-3 text-sm outline-none placeholder-gray-400"
                aria-readonly="true"
              />

              {/* Mic & Send button inside input */}
              <button
                type="button"
                // purely decorative; pointer-events-none so clicks fall through to parent
                className={`ml-2 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${isListening ? 'bg-red-500 animate-pulse' : 'bg-transparent'} opacity-50 pointer-events-none`}
                aria-label="Record voice (disabled)"
                aria-disabled="true"
              >
                <Mic size={16} />
              </button>
              <button
                type="button"
                // decorative send button - non-interactive so parent handles clicks
                className={`ml-2 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-150 bg-blue-600 text-white opacity-50 pointer-events-none`}
                aria-label="Send (disabled)"
                aria-disabled="true"
                title={chatInput ? 'Send (disabled)' : 'Open Library (disabled)'}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile dock navigation */}
      <MobileDock />
    </>
  );
};

export default Home;