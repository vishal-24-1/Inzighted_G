import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { useAuth } from '../utils/AuthContext';
import logo from '../logo.svg';
import { Plus, Search, SquarePen } from 'lucide-react';

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

  if (isOpen && !inlineOnDesktop) {
    return (
      <div className="fixed inset-0 z-50 bg-black bg-opacity-50" onClick={onClose}>
        <aside
          className="fixed top-0 left-0 h-full w-72 max-w-full bg-white shadow-lg z-60 transform transition-transform duration-300 ease-in-out translate-x-0"
          aria-hidden={false}
          aria-label="Sidebar navigation"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-start px-4 py-3 md:py-4 border-b border-gray-100">
              <div>
                <img src={logo} alt="InzightEd" className="h-6 w-auto" />
              </div>
            </div>

            {/* Top new chat removed; button will be sticky at bottom */}

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

            {/* New chat button (sticky bottom) */}
            <div className="mt-auto border-t px-3 py-3">
              <button
                onClick={() => {
                  navigate('/', { state: { openUploadPrompt: true } });
                  onClose && onClose();
                }}
                aria-label="New chat"
                className="w-full flex items-center gap-2 px-3 h-10 rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:outline-none justify-center"
              >
                <Plus className="h-5 w-5" />
                <span className="text-base font-medium">New Test</span>
              </button>
            </div>
          </div>
        </aside>
      </div>
    );
  } else {
    return (
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
          <div className="flex items-center justify-start px-4 py-3 md:py-4 border-b border-gray-100">
            <div>
              <img src={logo} alt="InzightEd" className="h-6 w-auto" />
            </div>
          </div>

          {/* Top new chat removed; button will be sticky at bottom */}

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

          {/* New chat button (sticky bottom) */}
          <div className="mt-auto border-t px-3 py-3">
            <button
              onClick={() => {
                navigate('/');
                onClose && onClose();
              }}
              aria-label="New chat"
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 focus:outline-none"
            >
              <Plus className="h-5 w-5" />
              <span className="text-base font-medium">New chat</span>
            </button>
          </div>
        </div>
      </aside>
    );
  }
};

export default Sidebar;
