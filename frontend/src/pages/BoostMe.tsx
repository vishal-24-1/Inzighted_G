import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import { Target, CheckCircle2, TrendingUp, Award, Plus, TextAlignStart, Sparkles, Info } from 'lucide-react';
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
  focus_zone_reasons?: string[];
  steady_zone_reasons?: string[];
  edge_zone_reasons?: string[];
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
  const [activeInfoPopover, setActiveInfoPopover] = useState<string | null>(null);
  const [showFullNameTooltip, setShowFullNameTooltip] = useState(false);


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
        focus_zone_reasons: parseZoneField(raw.insights?.focus_zone_reasons ?? []),
        steady_zone_reasons: parseZoneField(raw.insights?.steady_zone_reasons ?? []),
        edge_zone_reasons: parseZoneField(raw.insights?.edge_zone_reasons ?? []),
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
  const CircleProgress: React.FC<{ value: number; size?: number; strokeWidth?: number; color?: string; showPercent?: boolean }> = ({ value, size = 84, strokeWidth = 8, color = '#10B981', showPercent = true }) => {
    const capped = Math.max(0, Math.min(100, Number(value) || 0));
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - capped / 100);

    const textSize = Math.max(12, Math.floor(size / 5));

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
            style={{ transition: 'stroke-dashoffset 900ms cubic-bezier(.2,.9,.3,1)', filter: 'drop-shadow(0 4px 10px rgba(6,182,212,0.06))' }}
          />
          <text x="0" y="4" textAnchor="middle" fontSize={textSize} fontWeight={600} fill="#0F172A">
            {showPercent ? `${capped.toFixed(0)}%` : `${capped.toFixed(0)}`}
          </text>
        </g>
      </svg>
    );
  };

  // Simple static circle used to display numeric stats (e.g. XP) without a progress ring
  const StatCircle: React.FC<{ label?: React.ReactNode; size?: number; borderColor?: string; value?: number | string }> = ({ label, size = 84, borderColor = '#E6E6E6', value }) => {
    const fontSize = Math.max(12, Math.floor(size / 5.5));
    const ringSize = size;
    const innerSize = Math.max(44, Math.floor(size - 14));

    return (
      <div style={{ width: ringSize, height: ringSize }} className="flex items-center justify-center">
        {/* outer gradient ring */}
        <div
          className="rounded-full flex items-center justify-center transition-transform transform hover:scale-105"
          style={{
            width: ringSize,
            height: ringSize,
            padding: 6,
            background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(236,72,153,0.10))',
            borderRadius: 9999
          }}
        >
          <div style={{ width: innerSize, height: innerSize, borderRadius: 9999, background: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 6px 14px rgba(15,23,42,0.04)' }}>
            <div style={{ fontSize }} className="font-semibold text-gray-900">{value ?? label}</div>
          </div>
        </div>
      </div>
    );
  };



  const boostMeCards = insights ? [
    {
      type: 'Focus Zone',
      description: 'Areas to improve',
      content: insights.insights.focus_zone,
      reasons: insights.insights.focus_zone_reasons,
      color: '#dc3545',
      icon: <Target size={20} className="text-white" />
    },
    {
      type: 'Steady Zone',
      description: 'Strong areas',
      content: insights.insights.steady_zone,
      reasons: insights.insights.steady_zone_reasons,
      color: '#28a745',
      icon: <CheckCircle2 size={20} className="text-white" />
    },
    {
      type: 'Edge Zone',
      description: 'Growth potential',
      content: insights.insights.edge_zone,
      reasons: insights.insights.edge_zone_reasons,
      color: '#007bff',
      icon: <TrendingUp size={20} className="text-white" />
    }
  ] : [];


  // Convert hex color to rgba string (supports 3- or 6-digit hex). Falls back to a neutral gray.
  const hexToRgba = (hex?: string, alpha = 1) => {
    let h = (hex || '#e5e7eb').replace('#', '');
    if (h.length === 3) {
      h = h.split('').map(ch => ch + ch).join('');
    }
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  // Small helper to turn accuracy into a short human label
  const accuracyLabel = (value?: number) => {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    if (v >= 85) return 'Excellent';
    if (v >= 65) return 'Good';
    if (v >= 40) return 'Getting there';
    return 'Needs work';
  };

  return (
    <div className="w-full min-h-screen bg-white text-gray-900 px-2 pt-16 pb-24 flex flex-col overflow-x-hidden" onTouchStart={() => setShowFullNameTooltip(false)}>
      <header className="fixed top-0 w-full flex items-center justify-between mb-4 z-[45] bg-white px-2 py-3">
        <button
          className={`md:hidden w-10 h-10 flex items-center justify-center rounded-full border text-gray-700 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300 ${sidebarOpen ? '' : 'z-[55]'}`}
          aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          <TextAlignStart size={18} />
        </button>

        <div className="flex-1 text-center -ml-8 relative">
          {/** Show truncated session/document name in header */}
          {(() => {
            const raw = selectedSession?.document_name || insights?.document_name || selectedSession?.title || 'Boost Me';
            const max = 30;
            const txt = String(raw);
            const truncated = txt.length > max ? txt.slice(0, max - 3) + '...' : txt;
            return (
              <>
                <h1
                  className="text-md font-semibold"
                  title={raw}
                  onTouchStart={(e) => {
                    e.stopPropagation();
                    setShowFullNameTooltip(true);
                  }}
                  onTouchEnd={(e) => {
                    e.stopPropagation();
                    // Keep it visible until touch elsewhere
                  }}
                >
                  {truncated}
                </h1>
                {showFullNameTooltip && txt.length > max && (
                  <div className="absolute top-full mt-1 left-1/2 transform -translate-x-1/2 bg-black text-white text-xs px-2 py-1 rounded shadow-lg z-50 whitespace-nowrap">
                    {raw}
                  </div>
                )}
              </>
            );
          })()}
        </div>
      </header>

      {/* Sidebar and backdrop */}
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

      {/* User Profile Popup (ensure it appears above the sidebar/backdrop) */}
      {showProfilePopup && (
        <div className="fixed inset-0 z-40 flex items-center justify-center">
          <UserProfilePopup onClose={() => setShowProfilePopup(false)} />
        </div>
      )}

      <main className="w-full px-3 mx-auto">
        {/* Two-stat compact layout — enhanced, filled and mobile-first */}
        {insights && (
          <div className="w-full mt-4 mb-6">
            <div className="w-full rounded-2xl bg-gradient-to-br from-white to-slate-50 p-3 shadow-md border border-gray-100">
              <div className="flex items-center justify-between gap-3">
                {/* Accuracy column */}
                <div className="flex-1 flex flex-col items-center text-center">
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full -z-10" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.6)' }} />
                    <div className="rounded-full p-1 bg-white">
                      <CircleProgress value={insights.insights.accuracy ?? 0} size={88} strokeWidth={6} color="#06b6d4" />
                    </div>
                  </div>
                  <div className="mt-2 text-sm font-semibold text-gray-800">Accuracy</div>
                </div>

                {/* vertical divider for visual weight on larger phones */}
                <div className="hidden sm:block w-px h-16 bg-gray-200 mx-2" />

                {/* XP column */}
                <div className="flex-1 flex flex-col items-center text-center">
                  <div className="relative">
                    <div className="absolute -inset-1 rounded-full -z-10" style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.06), rgba(236,72,153,0.04))' }} />
                    <div className="rounded-full p-1 bg-white">
                      <StatCircle size={88} borderColor="#E6E6E6" value={insights.insights.xp_points ?? 0} />
                    </div>
                  </div>
                  <div className="mt-2 text-sm font-semibold text-gray-800 flex items-center gap-2">
                    <span>XP</span>
                  </div>
                </div>
              </div>

              {/* subtle footer text */}
              <div className="mt-3 text-center text-xs text-gray-400">Note: Accuracy and the XP shown here are for each test</div>
            </div>
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
            {/* Zone Cards (stacked vertically) */}
            <div className="w-full space-y-4 mb-16">
              {boostMeCards.map((card, index) => (
                <div key={index} className="rounded-2xl shadow-md p-2 relative" style={{ backgroundImage: `linear-gradient(135deg, ${hexToRgba(card.color, 0.18)}, ${hexToRgba(card.color, 0.36)})` }}>
                  <div className="flex items-center justify-between mb-2 pl-2 pt-2">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-800">{card.type}</h3>
                      <p className="text-xs text-gray-500">{card.description}</p>
                    </div>
                    {/* (Info moved) */}
                  </div>

                  {/* White content area (make relative so popover/link can be positioned inside) */}
                  <div className="text-sm text-gray-700 text-left bg-white rounded-lg px-2 pt-4 pb-6 relative">
                    {Array.isArray(card.content) && card.content.length > 0 ? (
                      <ul className="list-disc pl-5 space-y-2">
                        {card.content.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-gray-500 italic">No insights available</p>
                    )}

                    {/* Learn why link placed at the bottom-right inside the white content area */}
                    {card.reasons && card.reasons.length > 0 && (
                      <div className="absolute bottom-1 right-3">
                        <button
                          onClick={() => setActiveInfoPopover(activeInfoPopover === card.type ? null : card.type)}
                          className="learn-why-link text-xs text-gray-500 underline decoration-dashed decoration-1 decoration-gray-400 underline-offset-2 hover:decoration-gray-500 focus:outline-none"
                          aria-label={`Learn why for ${card.type}`}
                        >
                          Learn why
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

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

      {/* Modal for reasons */}
      {activeInfoPopover && (() => {
        const card = boostMeCards.find(c => c.type === activeInfoPopover);
        if (!card || !card.reasons || card.reasons.length === 0) return null;
        return (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setActiveInfoPopover(null)}>
            <div className="info-popover bg-white rounded-2xl shadow-xl border border-gray-200 p-4 w-full mx-4 animate-fadeIn max-h-[90vh] overflow-y-auto" style={{ maxWidth: 'calc(100vw - 2rem)' }} onClick={(e) => e.stopPropagation()}>
              <div className="flex items-start justify-between mb-2">
                <h4 className="text-md font-semibold text-gray-800">Why this insight?</h4>
                <button
                  onClick={() => setActiveInfoPopover(null)}
                  className="text-gray-400 hover:text-gray-600 focus:outline-none"
                  aria-label="Close"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <ul className="space-y-2 text-sm text-gray-600">
                {card.reasons.map((reason, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        );
      })()}

      {/* Mobile dock navigation */}
      {/* Floating plus button above the mobile dock (mobile-only) */}
      <div className="md:hidden fixed right-6 bottom-24 z-40">
        <button
          onClick={() => navigate('/', { state: { openUploadPrompt: true } })}
          aria-label="New test"
          title="New test"
          className="w-14 h-14 rounded-full bg-blue-600 text-white flex items-center justify-center text-center shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
        >
          <Plus size={32} strokeWidth={4} aria-hidden="true" />
        </button>
      </div>
      <MobileDock />
    </div>
  );
};

export default BoostMe;