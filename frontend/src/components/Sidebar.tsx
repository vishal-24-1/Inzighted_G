import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { useAuth } from '../utils/AuthContext';
import logo from '../logo.svg';
import { X } from 'lucide-react';

interface DocSession {
  id: string;
  document_name: string;
  updated_at: string;
  message_count: number;
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  onProfileClick?: () => void;
  // Sessions and selection handlers (optional)
  sessions?: DocSession[];
  selectedSessionId?: string | null;
  onSessionSelect?: (sessionId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen = true, onClose, onProfileClick, sessions, selectedSessionId = null, onSessionSelect }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [internalSessions, setInternalSessions] = useState<DocSession[]>(sessions ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If sessions prop was explicitly provided (even an empty array), use it and don't fetch.
    // Only fetch when sessions is undefined (not supplied by the parent).
    if (sessions !== undefined) {
      setInternalSessions(sessions);
      return;
    }

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await insightsAPI.getUserSessions();
        setInternalSessions(res.data || []);
      } catch (e: any) {
        console.error('Failed to load sessions in Sidebar:', e);
        // Try to extract a useful message from axios error
        let msg = 'Failed to load sessions';
        if (e?.response) {
          // Server responded with a status code outside 2xx
          msg = e.response?.data?.error || e.response?.data?.detail || JSON.stringify(e.response.data) || `Server error ${e.response.status}`;
          if (e.response.status === 401) {
            // Unauthorized - redirect to login
            window.location.href = '/login';
            return;
          }
        } else if (e?.request) {
          msg = 'No response from server. Please check your network connection.';
        } else if (e?.message) {
          msg = e.message;
        }
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [sessions?.length]);

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  return (
    // Off-canvas sidebar
    <aside
      className={`fixed top-0 left-0 h-full w-72 max-w-full bg-white shadow-lg z-40 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}
      aria-hidden={!isOpen}
      aria-label="Sidebar navigation"
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div>
            <img src={logo} alt="InzightEd" className="h-6 w-auto" />
          </div>
          <button
            onClick={onClose}
            aria-label="Close sidebar"
            className="w-9 h-9 flex items-center justify-center rounded-full bg-white text-gray-600 border border-gray-100 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Session list */}
        <div className="px-2 py-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 180px)' }}>
          <div className="space-y-2">
            {loading && (
              <div className="text-xs text-gray-400">Loading sessions...</div>
            )}
            {!loading && internalSessions.length === 0 && !error && (
              <div className="text-xs text-gray-400">No sessions yet</div>
            )}
            {!loading && error && (
              <div className="space-y-2">
                <div className="text-xs text-red-400">{error}</div>
                <div>
                  <button
                    onClick={() => {
                      // Retry loading sessions
                      setError(null);
                      setLoading(true);
                      insightsAPI.getUserSessions()
                        .then((res) => setInternalSessions(res.data || []))
                        .catch((e: any) => {
                          console.error('Retry failed:', e);
                          const msg = e?.response?.data?.error || e?.message || 'Retry failed';
                          setError(msg);
                        })
                        .finally(() => setLoading(false));
                    }}
                    className="text-xs text-blue-600 underline"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}
            {internalSessions.map((s) => (
              <button
                key={s.id}
                onClick={() => {
                  if (onSessionSelect) {
                    onSessionSelect(s.id);
                    if (onClose) onClose();
                  } else {
                    // Navigate to Boost page and include session id in query params
                    navigate(`/boost?session=${s.id}`);
                    if (onClose) onClose();
                  }
                }}
                className={`w-full text-left p-3 rounded-lg border ${selectedSessionId === s.id ? 'border-blue-500 bg-blue-50' : 'border-gray-100 bg-white'} hover:shadow-sm flex items-center justify-between overflow-hidden`}
              >
                <div className="min-w-0">
                  <div className="text-base font-medium text-gray-900 truncate">{s.document_name}</div>
                </div>
                {selectedSessionId === s.id && (
                  <div className="text-blue-600 font-bold"></div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* spacer to push footer to bottom */}
        <div className="flex-1" />

        <div className="px-4 py-4">
          <button
            onClick={() => {
              onProfileClick && onProfileClick();
              onClose && onClose();
            }}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-gray-50"
          >
            <div className="w-11 h-11 rounded-full bg-blue-500 flex items-center justify-center text-2xl font-bold text-white pt-1">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="flex-1 flex flex-col justify-center items-start">
              <div className="text-lg font-semibold text-gray-900">{user?.name || 'User'}</div>
              <span className="text-xs text-gray-500 w-max">View profile</span>
            </div>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
