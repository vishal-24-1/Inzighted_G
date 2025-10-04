import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { Menu, Home as HomeIcon } from 'lucide-react';
import Sidebar from '../components/Sidebar';

interface Session {
  id: string;
  title: string;
  document_name: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count: number;
}

interface Insights {
  strength: string | string[];
  weakness: string | string[];
  opportunity: string | string[];
  threat: string | string[];
}

interface SessionInsights {
  session_id: string;
  document_name: string;
  session_title: string;
  total_qa_pairs: number;
  insights: Insights;
}

const BoostMe: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [insights, setInsights] = useState<SessionInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const handleGoHome = () => {
    navigate('/');
  };

  const loadSessions = async () => {
    try {
      const response = await insightsAPI.getUserSessions();
      const sessionsData = response.data.filter((session: Session) => session.message_count > 1);
      setSessions(sessionsData);
      
      // Auto-select the most recent session
      if (sessionsData.length > 0) {
        setSelectedSession(sessionsData[0]);
        loadInsights(sessionsData[0].id);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  // Parse SWOT fields which may arrive as stringified Python lists like "['a','b']"
  const parseSwotField = (value: any): string | string[] => {
    if (!value && value !== 0) return '';
    if (Array.isArray(value)) return value;
    if (typeof value !== 'string') return String(value);

    const s = value.trim();

    // If looks like a list (starts with [ and ends with ]) try to parse
    if (s.startsWith('[') && s.endsWith(']')) {
      // Try valid JSON first (in case backend returned JSON)
      try {
        return JSON.parse(s);
      } catch (e) {
        // Convert Python-style single quotes to double quotes and try again
        try {
          const jsonLike = s.replace(/'/g, '"');
          return JSON.parse(jsonLike);
        } catch (_) {
          // Fallback: split on commas and strip quotes
          const inner = s.slice(1, -1);
          const parts = inner.split(/\s*,\s*/).map(p => p.replace(/^['"]|['"]$/g, '').trim()).filter(Boolean);
          return parts;
        }
      }
    }

    return s;
  };

  const loadInsights = async (sessionId: string) => {
    // Clear previous insights immediately so header falls back to selected session
    setInsights(null);
    setLoading(true);
    try {
      const response = await insightsAPI.getSessionInsights(sessionId);

      // Normalize insight fields so the UI can render arrays cleanly
      const data = response.data as SessionInsights;
      const parsed = {
        ...data,
        insights: {
          strength: parseSwotField(data.insights?.strength),
          weakness: parseSwotField(data.insights?.weakness),
          opportunity: parseSwotField(data.insights?.opportunity),
          threat: parseSwotField(data.insights?.threat),
        },
      } as SessionInsights;

      setInsights(parsed);
      setCurrentCardIndex(0); // Reset to first card
    } catch (error) {
      console.error('Failed to load insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSessionSelect = (session: Session) => {
    setSelectedSession(session);
    loadInsights(session.id);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Touch/swipe handling
  const minSwipeDistance = 50;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && currentCardIndex < 3) {
      setCurrentCardIndex(currentCardIndex + 1);
    }
    if (isRightSwipe && currentCardIndex > 0) {
      setCurrentCardIndex(currentCardIndex - 1);
    }
  };

  const swotCards = insights ? [
    {
      type: 'Strength',
      content: insights.insights.strength,
      color: '#28a745',
      icon: '💪'
    },
    {
      type: 'Weakness',
      content: insights.insights.weakness,
      color: '#dc3545',
      icon: '⚠️'
    },
    {
      type: 'Opportunity',
      content: insights.insights.opportunity,
      color: '#007bff',
      icon: '🚀'
    },
    {
      type: 'Threat',
      content: insights.insights.threat,
      color: '#fd7e14',
      icon: '⚡'
    }
  ] : [];

  return (
    <div className="min-h-screen bg-white text-gray-900 p-4">
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
          aria-label="Home"
          onClick={() => navigate('/')}
        >
          <HomeIcon size={16} className="text-blue-600" />
          <span className="text-sm font-medium">Home</span>
        </button>
      </header>

      {/* Sidebar and backdrop */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} onProfileClick={() => {}} />

      <main className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Session Selection */}
        <div className="md:col-span-1">
          <h2 className="text-sm font-medium mb-2">Select a Session</h2>
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleSessionSelect(session)}
                className={`w-full text-left p-3 rounded-lg border ${selectedSession?.id === session.id ? 'border-blue-500 bg-blue-50' : 'border-gray-100 bg-white'} hover:shadow-sm flex items-center justify-between`}
              >
                <div>
                  <div className="text-sm font-medium text-gray-900">{session.document_name}</div>
                  <div className="text-xs text-gray-500">{formatDate(session.updated_at)} · {session.message_count} messages</div>
                </div>
                {selectedSession?.id === session.id && (
                  <div className="text-blue-600 font-bold">✓</div>
                )}
              </button>
            ))}
            {sessions.length === 0 && (
              <div className="text-sm text-gray-500">No sessions found.</div>
            )}
          </div>
        </div>

        {/* Main insights area */}
        <div className="md:col-span-2">
          {selectedSession && (
            <div className="mb-3">
              <h2 className="text-base font-semibold">Insights for: {selectedSession.document_name || insights?.document_name}</h2>
              {insights && <p className="text-xs text-gray-500">{insights.total_qa_pairs} Q&A pairs analyzed</p>}
            </div>
          )}

          {/* Loading */}
          {loading ? (
            <div className="flex flex-col items-center justify-center py-10">
              <div className="h-10 w-10 border-4 border-blue-100 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm text-gray-600 mt-3">Analyzing your performance...</p>
            </div>
          ) : insights ? (
            <div>
              <div className="overflow-hidden">
                <div
                  className="flex w-[400%] transition-transform duration-300"
                  style={{ transform: `translateX(-${currentCardIndex * 25}%)` }}
                  onTouchStart={onTouchStart}
                  onTouchMove={onTouchMove}
                  onTouchEnd={onTouchEnd}
                >
                  {swotCards.map((card, index) => (
                    <div key={index} className="w-1/4 p-4">
                      <div className="bg-white rounded-lg p-4 h-full shadow-sm" style={{ borderLeft: `6px solid ${card.color}`, boxShadow: `0 8px 24px ${card.color}22` }}>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="text-2xl">{card.icon}</div>
                          <h3 className="text-lg font-semibold" style={{ color: card.color }}>{card.type}</h3>
                        </div>
                        <div className="text-sm text-gray-700">
                          {Array.isArray(card.content) ? (
                            <ul className="list-disc pl-5 space-y-1">
                              {card.content.map((item, idx) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p>{card.content}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Card Indicators */}
              <div className="flex items-center gap-2 mt-4">
                {swotCards.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentCardIndex(index)}
                    className={`h-2.5 w-8 rounded-full ${currentCardIndex === index ? 'bg-blue-600' : 'bg-gray-200'}`}
                    aria-label={`View ${swotCards[index].type} card`}
                  />
                ))}
              </div>

              <div className="text-xs text-gray-500 mt-3">← Swipe to explore insights →</div>
            </div>
          ) : selectedSession ? (
            <div className="text-center py-8">
              <h3 className="text-sm font-medium">No insights available</h3>
              <p className="text-xs text-gray-500">This session doesn't have enough data for analysis.</p>
            </div>
          ) : (
            <div className="text-center py-8">
              <h3 className="text-sm font-medium">No sessions found</h3>
              <p className="text-xs text-gray-500">Complete some tutoring sessions to see your performance insights.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default BoostMe;