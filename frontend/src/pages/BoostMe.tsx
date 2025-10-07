import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { Menu, Target, CheckCircle2, TrendingUp, Award, Plus } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import UserProfilePopup from '../components/UserProfilePopup';
import MobileDock from '../components/MobileDock';

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
  // new BoostMe fields (may come nested under `insights` or as top-level `zone_performance` / `performance`)
  focus_zone?: string[];
  steady_zone?: string[];
  edge_zone?: string[];
  xp_points?: number;
  accuracy?: number;
  // support alternate shapes
  zone_performance?: {
    focus?: any;
    steady?: any;
    edge?: any;
  };
  performance?: {
    accuracy?: number;
    xp?: number;
    xp_points?: number;
  };
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
  const [showProfilePopup, setShowProfilePopup] = useState(false);


  useEffect(() => {
    // If URL has a session query param, we'll auto-select that session after loading
    loadSessions();
  }, []);

  const handleGoHome = () => {
    navigate('/');
  };

  const loadSessions = async () => {
    try {
      const response = await insightsAPI.getUserSessions();
      // Show all sessions returned by the API (don't hide sessions with low message_count)
      // This ensures multiple uploads with the same document filename are visible as separate sessions.
      const sessionsData = response.data as Session[];
      setSessions(sessionsData);

      // If URL contains a session id, try to select that one. Otherwise auto-select the most recent.
      const params = new URLSearchParams(window.location.search);
      const sessionParam = params.get('session');

      if (sessionParam) {
        const matched = sessionsData.find(s => s.id === sessionParam);
        if (matched) {
          setSelectedSession(matched);
          loadInsights(matched.id);
          return;
        }
      }

      if (sessionsData.length > 0) {
        setSelectedSession(sessionsData[0]);
        loadInsights(sessionsData[0].id);
      }
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  // Parse zone fields which should arrive as arrays
  const parseZoneField = (value: any): string[] => {
    if (!value) return [];
    if (Array.isArray(value)) return value;
    if (typeof value === 'string') {
      // Try to parse if it's a stringified array
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed;
      } catch (e) {
        // Return as single-item array if parsing fails
        return [value];
      }
    }
    return [];
  };

  const loadInsights = async (sessionId: string) => {
    // Clear previous insights immediately so header falls back to selected session
    setInsights(null);
    setLoading(true);
    try {
      const response = await insightsAPI.getSessionInsights(sessionId);

      // Normalize insight fields to our UI-friendly `insights` shape.
      const raw = response.data as any;

      // Prefer new top-level shape: { zone_performance, performance }
      const zonePerf = (raw.zone_performance || raw.insights?.zone_performance) as any;
      const perf = (raw.performance || raw.insights?.performance) as any;

      // If server returned zone_performance/performance, use those; otherwise fall back to legacy `insights` shape
      const parsedInsights: Insights = {
        focus_zone: parseZoneField(zonePerf?.focus ?? raw.insights?.focus_zone ?? raw.insights?.focus),
        steady_zone: parseZoneField(zonePerf?.steady ?? raw.insights?.steady_zone ?? raw.insights?.steady),
        edge_zone: parseZoneField(zonePerf?.edge ?? raw.insights?.edge_zone ?? raw.insights?.edge),
        xp_points: perf?.xp ?? perf?.xp_points ?? raw.insights?.xp_points ?? raw.insights?.xp ?? 0,
        accuracy: perf?.accuracy ?? raw.insights?.accuracy ?? 0,
        // keep copies of raw shapes in case other code expects them
        zone_performance: zonePerf,
        performance: perf,
      };

      // Backwards-compatibility: if only legacy SWOT exists, map it into our zones so UI isn't empty
      // Check multiple legacy key variants to be resilient to different payload shapes
      const legacySwot = raw.swot_analysis || raw.legacy_swot || raw.swot || raw.insights?.swot_analysis || raw.insights?.swot || raw.insights?.legacy_swot;
      if (legacySwot) {
        // Map: strength -> steady, weakness -> focus, opportunity -> edge, threat -> (append to edge)
        parsedInsights.steady_zone = parseZoneField(legacySwot.strength ?? legacySwot.strengths ?? parsedInsights.steady_zone);
        parsedInsights.focus_zone = parseZoneField(legacySwot.weakness ?? legacySwot.weaknesses ?? parsedInsights.focus_zone);
        parsedInsights.edge_zone = parseZoneField(legacySwot.opportunity ?? legacySwot.opportunities ?? parsedInsights.edge_zone);
        // If there's a 'threat', append it to edge_zone for visibility
        const threat = legacySwot.threat || legacySwot.threats;
        if (threat) {
          const existing = Array.isArray(parsedInsights.edge_zone) ? parsedInsights.edge_zone : parseZoneField(parsedInsights.edge_zone);
          parsedInsights.edge_zone = [...existing, ...parseZoneField(threat)];
        }
      }

      const parsed: any = {
        ...raw,
        insights: parsedInsights,
      };

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

  // Simple circular progress component (value: 0-100)
  const CircleProgress: React.FC<{ value: number; size?: number; strokeWidth?: number; color?: string }> = ({ value, size = 84, strokeWidth = 8, color = '#10B981' }) => {
    const capped = Math.max(0, Math.min(100, Number(value) || 0));
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - capped / 100);

    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <g transform={`translate(${size / 2}, ${size / 2})`}>
          <circle
            r={radius}
            fill="none"
            stroke="#EEF2F7"
            strokeWidth={strokeWidth}
          />
          <circle
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={offset}
            transform="rotate(-90)"
          />
          <text x="0" y="4" textAnchor="middle" fontSize={14} fontWeight={600} fill="#0F172A">
            {capped.toFixed(0)}%
          </text>
        </g>
      </svg>
    );
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

    if (isLeftSwipe && currentCardIndex < cardCount - 1) {
      setCurrentCardIndex(currentCardIndex + 1);
    }
    if (isRightSwipe && currentCardIndex > 0) {
      setCurrentCardIndex(currentCardIndex - 1);
    }
  };



  const boostMeCards = insights ? [
    {
      type: 'Focus Zone',
      description: '🎯 Areas to improve',
      content: insights.insights.focus_zone,
      color: '#dc3545',
      icon: <Target size={20} className="text-white" />
    },
    {
      type: 'Steady Zone',
      description: '✅ Strong areas',
      content: insights.insights.steady_zone,
      color: '#28a745',
      icon: <CheckCircle2 size={20} className="text-white" />
    },
    {
      type: 'Edge Zone',
      description: '⚡ Growth potential',
      content: insights.insights.edge_zone,
      color: '#007bff',
      icon: <TrendingUp size={20} className="text-white" />
    }
  ] : [];

  // Guard to avoid division by zero when computing carousel widths
  const cardCount = Math.max(boostMeCards.length, 1);

  return (
    <div className="w-full min-h-screen bg-white text-gray-900 p-4 pb-24 flex flex-col overflow-x-hidden">
      <header className="w-full max-w-md flex items-center justify-between mb-4 md:ml-64 md:max-w-none md:border-b md:border-gray-200 md:pb-3">
        <button
          className="md:hidden w-10 h-10 flex items-center justify-center bg-gray-100 rounded-full shadow-sm text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
          aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          <Menu size={18} />
        </button>

        <div className="flex-1 text-center md:ml-8 md:text-left">
          {/** Show truncated session/document name in header */}
          {(() => {
            const raw = selectedSession?.document_name || insights?.document_name || selectedSession?.title || 'Boost Me';
            const max = 30;
            const txt = String(raw);
            const truncated = txt.length > max ? txt.slice(0, max - 3) + '...' : txt;
            return <h1 className="text-sm md:text-lg font-semibold">{truncated}</h1>;
          })()}
        </div>

        <button
          className="px-3 py-2 flex items-center justify-center bg-gray-100 rounded-full shadow-sm text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
          aria-label="New test"
          title="New test"
          onClick={() => navigate('/')}
        >
          <Plus size={16} className="mr-1" /> New test
        </button>
      </header>

      {/* Sidebar and backdrop */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-30" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onProfileClick={() => setShowProfilePopup(true)}
        sessions={sessions.map(s => ({ id: s.id, document_name: s.document_name, updated_at: s.updated_at, message_count: s.message_count }))}
        selectedSessionId={selectedSession?.id ?? null}
        onSessionSelect={(sessionId: string) => {
          const session = sessions.find(s => s.id === sessionId);
          if (session) handleSessionSelect(session);
          setSidebarOpen(false);
        }}
      />

      {/* Static desktop sidebar (visible on md+) */}
      <div className="hidden md:block md:flex-shrink-0">
        <Sidebar
          isOpen={true}
          inlineOnDesktop={true}
          onClose={() => { }}
          onProfileClick={() => setShowProfilePopup(true)}
          sessions={sessions.map(s => ({ id: s.id, document_name: s.document_name, updated_at: s.updated_at, message_count: s.message_count }))}
          selectedSessionId={selectedSession?.id ?? null}
          onSessionSelect={(sessionId: string) => {
            const session = sessions.find(s => s.id === sessionId);
            if (session) handleSessionSelect(session);
          }}
        />
      </div>

      {/* User Profile Popup (ensure it appears above the sidebar/backdrop) */}
      {showProfilePopup && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <UserProfilePopup onClose={() => setShowProfilePopup(false)} />
        </div>
      )}

      <main className="w-full max-w-md px-3 md:ml-72 mx-auto md:mx-0">
        {selectedSession && (
          <div className="mt-3">
            {/* Center the circle, but left-align the title/subtitle */}
            {insights ? (
              <>
                <div className="text-left">
                  <h2 className="text-base font-semibold">AI Generated Tips</h2>
                  <p className="text-xs text-gray-500">{insights.total_qa_pairs} Q&A pairs analyzed</p>
                </div>
              </>
            ) : (
              <h2 className="text-base font-semibold">AI Generated Tips</h2>
            )}
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
            {/* Zone Cards Carousel */}
            <div className="overflow-hidden w-full">
              <div
                className="flex transition-transform duration-300"
                style={{ width: `${cardCount * 100}%`, transform: `translateX(-${currentCardIndex * (100 / cardCount)}%)` }}
                onTouchStart={onTouchStart}
                onTouchMove={onTouchMove}
                onTouchEnd={onTouchEnd}
              >
                {boostMeCards.map((card, index) => (
                  <div key={index} className="py-4" style={{ width: `${100 / cardCount}%` }}>
                    <div className="bg-white rounded-lg p-4 h-full shadow-sm" style={{ border: `0.02rem solid ${card.color}` }}>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-full" style={{ background: card.color }}>
                          {card.icon}
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold" style={{ color: card.color }}>{card.type}</h3>
                          <p className="text-xs text-gray-500">{card.description}</p>
                        </div>
                      </div>
                      <div className="text-sm text-gray-700 text-left">
                        {Array.isArray(card.content) && card.content.length > 0 ? (
                          <ul className="list-disc pl-5 space-y-2">
                            {card.content.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-gray-500 italic">No insights available</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Card Indicators */}
            <div className="flex items-center justify-center gap-2 mt-2">
              {boostMeCards.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentCardIndex(index)}
                  className={`h-2.5 ${currentCardIndex === index ? 'w-10 bg-blue-500' : 'w-2.5 bg-gray-200'} rounded-full transition-all`}
                  aria-label={`View ${boostMeCards[index].type} card`}
                />
              ))}
            </div>

            <div className="text-xs text-gray-500 mt-3 text-center">← Swipe to explore insights →</div>

            {/* Accuracy circle with XP badge overlayed (moved XP into the circle) */}
            {insights && (
              <>
                <div className="mt-4 mb-2 text-left">
                  <h3 className="font-bold">Accuracy & XP Points</h3>
                </div>
                <div className="flex justify-center my-4 bg-gray-50 border rounded-xl p-4 relative">
                  {/* XP badge placed at the top-right of the circle container (not over the circle) */}
                  <div
                    className="absolute right-3 top-3"
                    aria-hidden={false}
                    title={`${insights.insights.xp_points ?? 0} XP points`}
                  >
                    <div className="bg-blue-500 text-white text-xs font-semibold rounded-full px-2 py-1 shadow-md flex items-center gap-1">
                      <Award size={14} className="text-white" />
                      <span>{insights.insights.xp_points ?? 0} XP</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center w-full">
                    {/* Circle centered inside the container */}
                    <CircleProgress value={insights.insights.accuracy ?? 0} size={92} strokeWidth={10} color="#10B981" />
                  </div>
                </div>
                {/* Brief explanation below the circle */}
                <div className="text-center text-sm text-gray-600 mt-2 px-4">
                  <p className="mt-1 text-xs text-gray-500">Tip: Start with Focus Zone to improve fastest.</p>
                </div>
              </>
            )}

            {/* XP now shown as a badge overlaying the accuracy circle above. The separate XP card was removed. */}
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
      </main>
      {/* Mobile dock navigation */}
      <MobileDock />
    </div>
  );
};

export default BoostMe;