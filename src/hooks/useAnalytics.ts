/**
 * Analytics Hook
 * Tracks decision metrics and user behavior for recommendation optimization
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export interface DecisionMetrics {
  sessionId: string;
  querySubmittedAt: string;
  recommendationsShownAt: string | null;
  decisionMadeAt: string | null;
  decisionTimeMs: number | null;
  recommendationsCount: number;
  viewedCards: number;
  skippedCards: number;
  selectedContentId: string | null;
  abandoned: boolean;
  scrollVelocity: number[];
  dwellTimes: number[];
  backtrackCount: number;
}

export interface AggregatedMetrics {
  totalSessions: number;
  avgDecisionTimeMs: number;
  completionRate: number;
  abandonmentRate: number;
  avgViewedCards: number;
  avgRecommendationsCount: number;
  mostSelectedGenres: { genre: string; count: number }[];
  hourlyDistribution: { hour: number; count: number }[];
}

const METRICS_KEY = 'vibe_ai_metrics';
const MAX_STORED_SESSIONS = 100;

export function useAnalytics() {
  const [currentSession, setCurrentSession] = useState<DecisionMetrics | null>(null);
  const [aggregatedMetrics, setAggregatedMetrics] = useState<AggregatedMetrics | null>(null);
  const sessionStartRef = useRef<number | null>(null);
  const scrollVelocitiesRef = useRef<number[]>([]);
  const dwellTimesRef = useRef<number[]>([]);
  const cardViewStartRef = useRef<number | null>(null);

  // Load aggregated metrics on mount
  useEffect(() => {
    loadAggregatedMetrics();
  }, []);

  const loadAggregatedMetrics = () => {
    try {
      const stored = localStorage.getItem(METRICS_KEY);
      if (stored) {
        const sessions: DecisionMetrics[] = JSON.parse(stored);
        
        // Deduplicate sessions by sessionId (keep first occurrence)
        const seen = new Set<string>();
        const dedupedSessions = sessions.filter(s => {
          if (seen.has(s.sessionId)) return false;
          seen.add(s.sessionId);
          return true;
        });
        
        // Save deduped sessions back if we removed any
        if (dedupedSessions.length !== sessions.length) {
          localStorage.setItem(METRICS_KEY, JSON.stringify(dedupedSessions));
          console.log(`🧹 Cleaned ${sessions.length - dedupedSessions.length} duplicate sessions`);
        }
        
        const aggregated = calculateAggregatedMetrics(dedupedSessions);
        setAggregatedMetrics(aggregated);
      }
    } catch (error) {
      console.error('Error loading metrics:', error);
    }
  };

  const calculateAggregatedMetrics = (sessions: DecisionMetrics[]): AggregatedMetrics => {
    if (sessions.length === 0) {
      return {
        totalSessions: 0,
        avgDecisionTimeMs: 0,
        completionRate: 0,
        abandonmentRate: 0,
        avgViewedCards: 0,
        avgRecommendationsCount: 0,
        mostSelectedGenres: [],
        hourlyDistribution: [],
      };
    }

    const completedSessions = sessions.filter(s => s.selectedContentId && !s.abandoned);
    const abandonedSessions = sessions.filter(s => s.abandoned);
    const sessionsWithDecision = sessions.filter(s => s.decisionTimeMs !== null);

    const avgDecisionTime = sessionsWithDecision.length > 0
      ? sessionsWithDecision.reduce((sum, s) => sum + (s.decisionTimeMs || 0), 0) / sessionsWithDecision.length
      : 0;

    const avgViewedCards = sessions.reduce((sum, s) => sum + s.viewedCards, 0) / sessions.length;
    const avgRecommendations = sessions.reduce((sum, s) => sum + s.recommendationsCount, 0) / sessions.length;

    // Hourly distribution
    const hourCounts: Record<number, number> = {};
    sessions.forEach(s => {
      const hour = new Date(s.querySubmittedAt).getHours();
      hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    });
    const hourlyDistribution = Object.entries(hourCounts)
      .map(([hour, count]) => ({ hour: parseInt(hour), count }))
      .sort((a, b) => a.hour - b.hour);

    return {
      totalSessions: sessions.length,
      avgDecisionTimeMs: Math.round(avgDecisionTime),
      completionRate: Math.round((completedSessions.length / sessions.length) * 100),
      abandonmentRate: Math.round((abandonedSessions.length / sessions.length) * 100),
      avgViewedCards: Math.round(avgViewedCards * 10) / 10,
      avgRecommendationsCount: Math.round(avgRecommendations * 10) / 10,
      mostSelectedGenres: [], // Would need genre data to calculate
      hourlyDistribution,
    };
  };

  // Start a new analytics session
  const startSession = useCallback(() => {
    const now = Date.now();
    sessionStartRef.current = now;
    scrollVelocitiesRef.current = [];
    dwellTimesRef.current = [];
    
    const session: DecisionMetrics = {
      sessionId: `session_${now}`,
      querySubmittedAt: new Date().toISOString(),
      recommendationsShownAt: null,
      decisionMadeAt: null,
      decisionTimeMs: null,
      recommendationsCount: 0,
      viewedCards: 0,
      skippedCards: 0,
      selectedContentId: null,
      abandoned: false,
      scrollVelocity: [],
      dwellTimes: [],
      backtrackCount: 0,
    };
    
    setCurrentSession(session);
    return session.sessionId;
  }, []);

  // Record when recommendations are shown
  const recordRecommendationsShown = useCallback((count: number) => {
    setCurrentSession(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        recommendationsShownAt: new Date().toISOString(),
        recommendationsCount: count,
      };
    });
  }, []);

  // Record card view start (for dwell time)
  const recordCardViewStart = useCallback(() => {
    cardViewStartRef.current = Date.now();
  }, []);

  // Record card view end (calculate dwell time)
  const recordCardViewEnd = useCallback(() => {
    if (cardViewStartRef.current) {
      const dwellTime = Date.now() - cardViewStartRef.current;
      dwellTimesRef.current.push(dwellTime);
      
      setCurrentSession(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          viewedCards: prev.viewedCards + 1,
          dwellTimes: [...dwellTimesRef.current],
        };
      });
    }
  }, []);

  // Record skip
  const recordSkip = useCallback(() => {
    setCurrentSession(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        skippedCards: prev.skippedCards + 1,
      };
    });
  }, []);

  // Record backtrack (going to previous card)
  const recordBacktrack = useCallback(() => {
    setCurrentSession(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        backtrackCount: prev.backtrackCount + 1,
      };
    });
  }, []);

  // Record scroll velocity
  const recordScrollVelocity = useCallback((velocity: number) => {
    scrollVelocitiesRef.current.push(velocity);
    setCurrentSession(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        scrollVelocity: [...scrollVelocitiesRef.current],
      };
    });
  }, []);

  // Record content selection (decision made)
  const recordSelection = useCallback((contentId: string) => {
    const now = Date.now();
    const decisionTime = sessionStartRef.current ? now - sessionStartRef.current : null;
    
    setCurrentSession(prev => {
      if (!prev) {
        // Create session on the fly if none exists
        const newSession: DecisionMetrics = {
          sessionId: `session_${now}`,
          querySubmittedAt: new Date().toISOString(),
          recommendationsShownAt: new Date().toISOString(),
          decisionMadeAt: new Date().toISOString(),
          decisionTimeMs: decisionTime || 10000,
          recommendationsCount: 3,
          viewedCards: 1,
          skippedCards: 0,
          selectedContentId: contentId,
          abandoned: false,
          scrollVelocity: [],
          dwellTimes: [],
          backtrackCount: 0,
        };
        saveSession(newSession);
        return newSession;
      }
      
      const completedSession: DecisionMetrics = {
        ...prev,
        decisionMadeAt: new Date().toISOString(),
        decisionTimeMs: decisionTime,
        selectedContentId: contentId,
        abandoned: false,
      };
      
      // Save to localStorage
      saveSession(completedSession);
      
      return completedSession;
    });
  }, []);

  // Record abandonment (closed without selection)
  const recordAbandonment = useCallback(() => {
    const now = Date.now();
    
    setCurrentSession(prev => {
      if (!prev) {
        // Create session on the fly if none exists
        const newSession: DecisionMetrics = {
          sessionId: `session_${now}`,
          querySubmittedAt: new Date().toISOString(),
          recommendationsShownAt: new Date().toISOString(),
          decisionMadeAt: null,
          decisionTimeMs: null,
          recommendationsCount: 3,
          viewedCards: 1,
          skippedCards: 0,
          selectedContentId: null,
          abandoned: true,
          scrollVelocity: [],
          dwellTimes: [],
          backtrackCount: 0,
        };
        saveSession(newSession);
        return newSession;
      }
      
      const abandonedSession: DecisionMetrics = {
        ...prev,
        abandoned: true,
      };
      
      // Save to localStorage
      saveSession(abandonedSession);
      
      return abandonedSession;
    });
  }, []);

  // Save session to localStorage AND send to backend
  const saveSession = (session: DecisionMetrics) => {
    try {
      const stored = localStorage.getItem(METRICS_KEY);
      const sessions: DecisionMetrics[] = stored ? JSON.parse(stored) : [];
      
      // Check if session already exists (prevent duplicates)
      const existingIndex = sessions.findIndex(s => s.sessionId === session.sessionId);
      let updatedSessions: DecisionMetrics[];
      
      if (existingIndex >= 0) {
        // Update existing session instead of adding duplicate
        updatedSessions = [...sessions];
        updatedSessions[existingIndex] = session;
      } else {
        // Add new session and keep only last N
        updatedSessions = [session, ...sessions].slice(0, MAX_STORED_SESSIONS);
      }
      localStorage.setItem(METRICS_KEY, JSON.stringify(updatedSessions));
      console.log('💾 Saved to localStorage, total sessions:', updatedSessions.length);
      
      // Update aggregated metrics
      const aggregated = calculateAggregatedMetrics(updatedSessions);
      setAggregatedMetrics(aggregated);
      
      // Send to backend for advanced metrics
      sendSessionToBackend(session);
    } catch (error) {
      console.error('Error saving session:', error);
    }
  };
  
  // Send session data to backend metrics service
  const sendSessionToBackend = async (session: DecisionMetrics) => {
    const payload = {
      session_id: session.sessionId,
      user_id: 'user-' + Date.now(),
      committed: !!session.selectedContentId && !session.abandoned,
      commit_at_nru: session.viewedCards || 1,
      time_to_commit_ms: session.decisionTimeMs,
      total_browse_time_ms: session.decisionTimeMs || 30000,
      initial_stress: 0.5,
      final_stress: session.abandoned ? 0.7 : 0.3,
      genres_shown: [],
      cards_viewed: session.viewedCards
    };
    
    try {
      const response = await fetch('http://localhost:8888/api/metrics/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        await response.json();
      }
    } catch (error) {
      console.warn('Analytics recording failed:', error);
    }
  };

  // Get all stored sessions
  const getSessions = useCallback((): DecisionMetrics[] => {
    try {
      const stored = localStorage.getItem(METRICS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }, []);

  // Clear all metrics
  const clearMetrics = useCallback(() => {
    localStorage.removeItem(METRICS_KEY);
    setAggregatedMetrics(null);
  }, []);

  return {
    currentSession,
    aggregatedMetrics,
    startSession,
    recordRecommendationsShown,
    recordCardViewStart,
    recordCardViewEnd,
    recordSkip,
    recordBacktrack,
    recordScrollVelocity,
    recordSelection,
    recordAbandonment,
    getSessions,
    clearMetrics,
  };
}
