import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { useAuth } from '../utils/AuthContext';
import logo from '../logo.svg';
import { X, Search, SquarePen } from 'lucide-react';

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
  // When true, render the sidebar inline (static) on md+ screens instead of off-canvas
  inlineOnDesktop?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen = true, onClose, onProfileClick, sessions, selectedSessionId = null, onSessionSelect, inlineOnDesktop = false }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [internalSessions, setInternalSessions] = useState<DocSession[]>(sessions ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

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
    // Off-canvas sidebar (becomes fixed full-height on md+ when inlineOnDesktop is true)
    <aside
      className={
        inlineOnDesktop
          ? `fixed top-0 left-0 h-full w-72 max-w-full bg-white md:bg-gray-50 shadow-lg z-40 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:fixed md:top-0 md:left-0 md:h-screen md:w-72 md:translate-x-0 md:transform-none md:shadow-none md:z-auto`
          : `fixed top-0 left-0 h-full w-72 max-w-full bg-white md:bg-gray-50 shadow-lg z-40 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`
      }
      aria-hidden={!isOpen}
      aria-label="Sidebar navigation"
    >
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 md:py-4 border-b border-gray-100">
          <div>
            <img src={logo} alt="InzightEd" className="h-6 w-auto" />
          </div>
          <button
            onClick={onClose}
            aria-label="Close sidebar"
            className="md:hidden w-9 h-9 flex items-center justify-center rounded-full bg-white text-gray-600 border border-gray-100 shadow-sm hover:bg-gray-50 focus:outline-none"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* New chat button */}
        <div className="px-2 pt-3">
          <button
            onClick={() => {
              navigate('/');
              onClose && onClose();
            }}
            aria-label="New chat"
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:outline-none"
          >
            <SquarePen className="h-5 w-5" />
            <span className="text-base font-medium">New chat</span>
          </button>
        </div>

        {/* Search + Session list */}
        <div className="px-2 py-3">
          <div className="relative">
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-gray-400" aria-hidden />
            </div>
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sessions..."
              aria-label="Search sessions"
              className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-200 bg-gray-50 placeholder-gray-400 focus:outline-none"
            />
          </div>
        </div>

        <div className="px-2 pb-3 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 220px)' }}>
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

            {/** Filter sessions by search query (case-insensitive) */}
            {(() => {
              const q = searchQuery.trim().toLowerCase();
              const filtered = q ? internalSessions.filter((s) => s.document_name.toLowerCase().includes(q)) : internalSessions;

              if (!loading && filtered.length === 0 && internalSessions.length > 0 && !error) {
                return <div className="text-xs text-gray-400">No matching sessions</div>;
              }

              return filtered.map((s) => (
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
                  className={`w-full text-left px-3 py-2 rounded-md ${selectedSessionId === s.id ? 'bg-gray-100' : 'bg-transparent'} hover:bg-gray-100 flex items-center justify-between overflow-hidden focus:outline-none focus:ring-0`}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{s.document_name}</div>
                  </div>
                  {selectedSessionId === s.id && (
                    <div className="text-blue-600 font-bold"></div>
                  )}
                </button>
              ));
            })()}
          </div>
        </div>

        {/* spacer to push footer to bottom */}
        <div className="flex-1 border-t" />

        <div className="px-3 py-3">
          <button
            onClick={() => {
              onProfileClick && onProfileClick();
              onClose && onClose();
            }}
            className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-gray-100 focus:outline-none"
          >
            <div className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center text-lg font-semibold text-white">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="flex-1 flex flex-col justify-center items-start min-w-0">
              <div className="text-sm font-medium text-gray-900 truncate">{user?.name || 'User'}</div>
              <span className="text-xs text-gray-500">View profile</span>
            </div>
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
