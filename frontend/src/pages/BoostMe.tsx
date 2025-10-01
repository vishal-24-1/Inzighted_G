import React, { useState, useEffect } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useNavigate } from 'react-router-dom';
import { insightsAPI } from '../utils/api';
import './BoostMe.css';

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
  strength: string;
  weakness: string;
  opportunity: string;
  threat: string;
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

  const loadInsights = async (sessionId: string) => {
    // Clear previous insights immediately so header falls back to selected session
    setInsights(null);
    setLoading(true);
    try {
      const response = await insightsAPI.getSessionInsights(sessionId);
      setInsights(response.data);
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
    <div className="boost-container">
      <header className="boost-header">
        <div className="header-content">
          <div className="header-left">
            <div className="back-button" onClick={handleGoHome} title="Go to Home">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 12H5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M12 19L5 12L12 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h1>Performance Insights</h1>
          </div>
          <div className="user-info">
            <span>Welcome, {user?.name}</span>
          </div>
        </div>
      </header>

      <main className="boost-main">
        {/* Session Selection */}
        <div className="session-selection">
          <h2>Select a Session</h2>
          <div className="sessions-list">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`session-card ${selectedSession?.id === session.id ? 'selected' : ''}`}
                onClick={() => handleSessionSelect(session)}
              >
                <div className="session-info">
                  <h3>{session.document_name}</h3>
                  <p className="session-date">{formatDate(session.updated_at)}</p>
                  <p className="session-stats">{session.message_count} messages</p>
                </div>
                {selectedSession?.id === session.id && (
                  <div className="selected-indicator">✓</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Document Name Display */}
        {selectedSession && (
          <div className="selected-document">
            {/* Prefer the selected session's document name so header updates immediately on selection */}
            <h2>Insights for: {selectedSession.document_name || insights?.document_name}</h2>
            {insights && (
              <p className="qa-count">{insights.total_qa_pairs} Q&A pairs analyzed</p>
            )}
          </div>
        )}

        {/* SWOT Cards */}
        {loading ? (
          <div className="loading-insights">
            <div className="loading-spinner"></div>
            <p>Analyzing your performance...</p>
          </div>
        ) : insights ? (
          <div className="swot-container">
            <div className="swot-cards-wrapper">
              <div 
                className="swot-cards"
                style={{ transform: `translateX(-${currentCardIndex * 25}%)` }}
                onTouchStart={onTouchStart}
                onTouchMove={onTouchMove}
                onTouchEnd={onTouchEnd}
              >
                {swotCards.map((card, index) => (
                  <div
                    key={index}
                    className="swot-card"
                    style={{ 
                      borderLeftColor: card.color,
                      boxShadow: `0 4px 15px ${card.color}20`
                    }}
                  >
                    <div className="card-header">
                      <span className="card-icon">{card.icon}</span>
                      <h3 style={{ color: card.color }}>{card.type}</h3>
                    </div>
                    <div className="card-content">
                      <p>{card.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Card Indicators */}
            <div className="card-indicators">
              {swotCards.map((_, index) => (
                <button
                  key={index}
                  className={`indicator ${currentCardIndex === index ? 'active' : ''}`}
                  onClick={() => setCurrentCardIndex(index)}
                  aria-label={`View ${swotCards[index].type} card`}
                />
              ))}
            </div>

            {/* Swipe Instruction */}
            <div className="swipe-instruction">
              <p>← Swipe to explore insights →</p>
            </div>
          </div>
        ) : selectedSession ? (
          <div className="no-insights">
            <h3>No insights available</h3>
            <p>This session doesn't have enough data for analysis.</p>
          </div>
        ) : (
          <div className="no-sessions">
            <h3>No sessions found</h3>
            <p>Complete some tutoring sessions to see your performance insights.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default BoostMe;