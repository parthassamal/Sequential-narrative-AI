/**
 * useTelemetry Hook
 * 
 * Real-time behavioral signal collection for AI-powered decision state encoding.
 * Tracks:
 * - Scroll velocity (px/s)
 * - Dwell time per card (ms)
 * - Focus changes (back-and-forth count)
 * - Micro-pause ratios
 * - Skip velocity
 * 
 * Sends telemetry to backend via WebSocket or polling for continuous
 * decision state updates.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { TelemetryEvent, TelemetryBatch, EnhancedDecisionState } from '../types';

interface TelemetryConfig {
  userId: string;
  sessionId: string;
  backendUrl?: string;
  batchIntervalMs?: number; // How often to send batches
  useWebSocket?: boolean;
}

interface TelemetryState {
  isConnected: boolean;
  eventCount: number;
  lastBatchSent: number | null;
  enhancedState: EnhancedDecisionState | null;
}

interface UseTelemetryReturn {
  // Track specific events
  trackScroll: (velocity: number) => void;
  trackDwell: (contentId: string, durationMs: number) => void;
  trackFocusChange: () => void;
  trackSkip: (contentId: string) => void;
  trackReplay: (contentId: string) => void;
  trackMicroPause: (ratio: number) => void;
  
  // State
  state: TelemetryState;
  
  // Control
  flush: () => Promise<void>;
  reset: () => void;
  
  // Enhanced decision state from backend
  enhancedDecisionState: EnhancedDecisionState | null;
}

const DEFAULT_CONFIG: Partial<TelemetryConfig> = {
  backendUrl: 'http://localhost:8888',
  batchIntervalMs: 2000, // Send every 2 seconds
  useWebSocket: true,
};

export function useTelemetry(config: TelemetryConfig): UseTelemetryReturn {
  const fullConfig = { ...DEFAULT_CONFIG, ...config };
  
  // Event buffer
  const eventBuffer = useRef<TelemetryEvent[]>([]);
  
  // WebSocket connection
  const wsRef = useRef<WebSocket | null>(null);
  
  // State
  const [state, setState] = useState<TelemetryState>({
    isConnected: false,
    eventCount: 0,
    lastBatchSent: null,
    enhancedState: null,
  });
  
  // Session tracking
  const sessionStartRef = useRef<number>(Date.now());
  const focusChangeCountRef = useRef<number>(0);
  
  // Create telemetry event
  const createEvent = useCallback((
    eventType: TelemetryEvent['eventType'],
    value: number,
    contentId?: string,
    metadata?: Record<string, unknown>
  ): TelemetryEvent => {
    return {
      userId: fullConfig.userId,
      timestamp: Date.now(),
      eventType,
      value,
      contentId,
      metadata,
    };
  }, [fullConfig.userId]);
  
  // Add event to buffer
  const addEvent = useCallback((event: TelemetryEvent) => {
    eventBuffer.current.push(event);
    setState(prev => ({
      ...prev,
      eventCount: prev.eventCount + 1,
    }));
  }, []);
  
  // Track scroll velocity
  const trackScroll = useCallback((velocity: number) => {
    addEvent(createEvent('scroll', velocity, undefined, {
      normalized: Math.min(velocity / 1000, 1),
    }));
  }, [addEvent, createEvent]);
  
  // Track dwell time on content
  const trackDwell = useCallback((contentId: string, durationMs: number) => {
    addEvent(createEvent('dwell', durationMs, contentId, {
      normalizedDuration: Math.min(durationMs / 30000, 1),
    }));
  }, [addEvent, createEvent]);
  
  // Track focus change (back-and-forth navigation)
  const trackFocusChange = useCallback(() => {
    focusChangeCountRef.current += 1;
    addEvent(createEvent('focus', focusChangeCountRef.current, undefined, {
      sessionTotal: focusChangeCountRef.current,
    }));
  }, [addEvent, createEvent]);
  
  // Track skip action
  const trackSkip = useCallback((contentId: string) => {
    addEvent(createEvent('skip', 1, contentId));
  }, [addEvent, createEvent]);
  
  // Track replay action
  const trackReplay = useCallback((contentId: string) => {
    addEvent(createEvent('replay', 1, contentId));
  }, [addEvent, createEvent]);
  
  // Track micro-pause ratio
  const trackMicroPause = useCallback((ratio: number) => {
    addEvent(createEvent('micro_pause', ratio, undefined, {
      description: ratio > 0.5 ? 'significant_pause' : 'brief_pause',
    }));
  }, [addEvent, createEvent]);
  
  // Create batch for transmission
  const createBatch = useCallback((): TelemetryBatch | null => {
    if (eventBuffer.current.length === 0) return null;
    
    const events = [...eventBuffer.current];
    const windowStart = events[0]?.timestamp || Date.now();
    const windowEnd = events[events.length - 1]?.timestamp || Date.now();
    
    return {
      userId: fullConfig.userId,
      sessionId: fullConfig.sessionId,
      events,
      windowStart,
      windowEnd,
    };
  }, [fullConfig.userId, fullConfig.sessionId]);
  
  // Convert batch to snake_case for backend
  const toSnakeCaseBatch = useCallback((batch: TelemetryBatch) => {
    return {
      user_id: batch.userId,
      session_id: batch.sessionId,
      events: batch.events.map(e => ({
        user_id: e.userId,
        timestamp: e.timestamp,
        event_type: e.eventType,
        value: e.value,
        content_id: e.contentId,
        metadata: e.metadata,
      })),
      window_start: batch.windowStart,
      window_end: batch.windowEnd,
    };
  }, []);

  // Send batch via HTTP (fallback)
  const sendBatchHTTP = useCallback(async (batch: TelemetryBatch): Promise<void> => {
    try {
      const response = await fetch(`${fullConfig.backendUrl}/api/telemetry/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(toSnakeCaseBatch(batch)),
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.enhanced_state) {
          setState(prev => ({
            ...prev,
            enhancedState: transformEnhancedState(data.enhanced_state),
          }));
        }
      }
    } catch (error) {
      // Silently fail - telemetry is non-critical
    }
  }, [fullConfig.backendUrl, toSnakeCaseBatch]);
  
  // Send batch via WebSocket
  const sendBatchWS = useCallback((batch: TelemetryBatch): void => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(toSnakeCaseBatch(batch)));
    }
  }, [toSnakeCaseBatch]);
  
  // Flush buffer
  const flush = useCallback(async () => {
    const batch = createBatch();
    if (!batch) return;
    
    // Clear buffer
    eventBuffer.current = [];
    
    // Send
    if (fullConfig.useWebSocket && wsRef.current?.readyState === WebSocket.OPEN) {
      sendBatchWS(batch);
    } else {
      await sendBatchHTTP(batch);
    }
    
    setState(prev => ({
      ...prev,
      lastBatchSent: Date.now(),
    }));
  }, [createBatch, fullConfig.useWebSocket, sendBatchWS, sendBatchHTTP]);
  
  // Reset telemetry
  const reset = useCallback(() => {
    eventBuffer.current = [];
    focusChangeCountRef.current = 0;
    sessionStartRef.current = Date.now();
    setState({
      isConnected: wsRef.current?.readyState === WebSocket.OPEN,
      eventCount: 0,
      lastBatchSent: null,
      enhancedState: null,
    });
  }, []);
  
  // Setup WebSocket connection
  useEffect(() => {
    if (!fullConfig.useWebSocket) return;
    
    // WebSocket endpoint is at /ws/telemetry/{user_id}
    const wsUrl = `${fullConfig.backendUrl?.replace('http', 'ws')}/ws/telemetry/${fullConfig.userId}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        // WebSocket connected - no need to log
        setState(prev => ({ ...prev, isConnected: true }));
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.enhanced_state) {
            setState(prev => ({
              ...prev,
              enhancedState: transformEnhancedState(data.enhanced_state),
            }));
          }
        } catch {
          // Silently handle parse errors
        }
      };
      
      ws.onclose = () => {
        setState(prev => ({ ...prev, isConnected: false }));
      };
      
      ws.onerror = () => {
        // WebSocket errors are non-critical - fallback to HTTP
      };
      
      wsRef.current = ws;
      
      return () => {
        ws.close();
      };
    } catch {
      // Failed to create WebSocket - will use HTTP fallback
    }
  }, [fullConfig.useWebSocket, fullConfig.backendUrl, fullConfig.userId]);
  
  // Periodic batch sending
  useEffect(() => {
    const interval = setInterval(() => {
      if (eventBuffer.current.length > 0) {
        flush();
      }
    }, fullConfig.batchIntervalMs);
    
    return () => clearInterval(interval);
  }, [flush, fullConfig.batchIntervalMs]);
  
  return {
    trackScroll,
    trackDwell,
    trackFocusChange,
    trackSkip,
    trackReplay,
    trackMicroPause,
    state,
    flush,
    reset,
    enhancedDecisionState: state.enhancedState,
  };
}

// Transform backend snake_case to frontend camelCase
function transformEnhancedState(backendState: Record<string, unknown>): EnhancedDecisionState {
  return {
    stressLevel: (backendState.stress_level as number) ?? 0.3,
    scrollVelocity: (backendState.scroll_velocity as number) ?? 0,
    dwellTime: (backendState.dwell_time as number) ?? 0,
    focusChanges: (backendState.focus_changes as number) ?? 0,
    searchRewrites: (backendState.search_rewrites as number) ?? 0,
    confidenceScore: (backendState.confidence_score as number) ?? 0.7,
    
    // Multi-head outputs
    commitProbability: (backendState.commit_probability as number) ?? 0.5,
    hesitationScore: (backendState.hesitation_score as number) ?? 0.3,
    hazardRate: (backendState.hazard_rate as number) ?? 0.1,
    survivalProbability: (backendState.survival_probability as number) ?? 0.9,
    epistemicUncertainty: (backendState.epistemic_uncertainty as number) ?? 0.2,
    
    // Temporal
    timeInSession: (backendState.time_in_session as number) ?? 0,
    sessionStartTimestamp: (backendState.session_start_timestamp as number) ?? Date.now(),
    
    // Derived
    optimalSetSize: (backendState.optimal_set_size as number) ?? 4,
    shouldReduceChoices: (backendState.should_reduce_choices as boolean) ?? false,
    predictedTimeToCommit: (backendState.predicted_time_to_commit as number) ?? 30,
  };
}

// Hook for scroll velocity tracking
export function useScrollVelocity(
  onVelocity: (velocity: number) => void,
  throttleMs: number = 100
) {
  const lastScrollRef = useRef<{ position: number; time: number } | null>(null);
  const throttleRef = useRef<number>(0);
  
  useEffect(() => {
    const handleScroll = () => {
      const now = Date.now();
      
      // Throttle
      if (now - throttleRef.current < throttleMs) return;
      throttleRef.current = now;
      
      const currentPosition = window.scrollY;
      
      if (lastScrollRef.current) {
        const deltaPosition = Math.abs(currentPosition - lastScrollRef.current.position);
        const deltaTime = (now - lastScrollRef.current.time) / 1000; // Convert to seconds
        
        if (deltaTime > 0) {
          const velocity = deltaPosition / deltaTime; // px/s
          onVelocity(velocity);
        }
      }
      
      lastScrollRef.current = { position: currentPosition, time: now };
    };
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [onVelocity, throttleMs]);
}

// Hook for dwell time tracking
export function useDwellTime(
  contentId: string | null,
  onDwell: (contentId: string, durationMs: number) => void
) {
  const startTimeRef = useRef<number | null>(null);
  const lastContentRef = useRef<string | null>(null);
  
  useEffect(() => {
    // Content changed
    if (contentId !== lastContentRef.current) {
      // Report dwell time for previous content
      if (lastContentRef.current && startTimeRef.current) {
        const duration = Date.now() - startTimeRef.current;
        onDwell(lastContentRef.current, duration);
      }
      
      // Start tracking new content
      lastContentRef.current = contentId;
      startTimeRef.current = contentId ? Date.now() : null;
    }
  }, [contentId, onDwell]);
  
  // Report on unmount
  useEffect(() => {
    return () => {
      if (lastContentRef.current && startTimeRef.current) {
        const duration = Date.now() - startTimeRef.current;
        onDwell(lastContentRef.current, duration);
      }
    };
  }, [onDwell]);
}

// Hook for focus/visibility tracking
export function useFocusTracking(
  onFocusChange: () => void
) {
  const wasVisibleRef = useRef<boolean>(true);
  
  useEffect(() => {
    const handleVisibilityChange = () => {
      const isVisible = document.visibilityState === 'visible';
      
      // Only track when coming back into focus (indicates tab switching)
      if (isVisible && !wasVisibleRef.current) {
        onFocusChange();
      }
      
      wasVisibleRef.current = isVisible;
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [onFocusChange]);
}
