// Core Types for Sequential Narrative AI Recommendation System

export interface Content {
  id: string;
  title: string;
  type: 'movie' | 'series' | 'documentary' | 'video';
  genre: string[];
  year: number;
  rating: number;
  duration: string;
  posterUrl: string;
  backdropUrl: string;
  description: string;
  cast: string[];
  director: string;
  themes: string[];
  mood: ContentMood[];
  standoutScenes: string[];
  funFacts: string[];
  trailerUrl?: string;
  streamingUrl?: string;
  provider?: string;
}

export type ContentMood = 
  | 'thrilling' 
  | 'heartwarming' 
  | 'thought-provoking' 
  | 'relaxing' 
  | 'exciting' 
  | 'dark' 
  | 'uplifting' 
  | 'mysterious' 
  | 'romantic' 
  | 'comedic'
  | 'intense'
  | 'escapist'
  | 'cozy';

export interface UserProfile {
  id: string;
  viewingHistory: ViewingRecord[];
  preferences: UserPreferences;
  decisionState: DecisionState;
  contextualSignals: ContextualSignals;
}

export interface ViewingRecord {
  contentId: string;
  watchedAt: Date;
  completionRate: number;
  rewatched: boolean;
  rating?: number;
  engagementScore: number;
}

export interface UserPreferences {
  favoriteGenres: string[];
  dislikedGenres: string[];
  preferredMoods: ContentMood[];
  preferredDuration: 'short' | 'medium' | 'long';
  maturityRating: 'G' | 'PG' | 'PG-13' | 'R';
}

export interface DecisionState {
  // Decision state vector for reducing choice deferral
  stressLevel: number; // 0-1, derived from browsing patterns
  scrollVelocity: number; // How fast user is scrolling
  dwellTime: number; // Time spent on current view
  focusChanges: number; // Number of back-and-forth navigations
  searchRewrites: number; // How many times search was modified
  confidenceScore: number; // System's confidence in recommendations
}

// Enhanced decision state with AI-powered fields
export interface EnhancedDecisionState extends DecisionState {
  // Multi-head encoder outputs
  commitProbability: number; // P(commit|x) - likelihood user will select
  hesitationScore: number; // η(x) - explicit ambivalence measure
  hazardRate: number; // h(t|x) - instantaneous commit probability
  survivalProbability: number; // S(t) - probability user hasn't committed
  epistemicUncertainty: number; // σ(x) - model uncertainty
  
  // Temporal context
  timeInSession: number; // Seconds since session start
  sessionStartTimestamp: number; // Unix timestamp
  
  // Derived metrics
  optimalSetSize: number; // Cognitive load aware recommendation count
  shouldReduceChoices: boolean; // Flag when hesitation is high
  predictedTimeToCommit: number; // Expected seconds until commit
}

// Telemetry event for real-time behavioral tracking
export interface TelemetryEvent {
  userId: string;
  timestamp: number; // Unix ms
  eventType: 'scroll' | 'dwell' | 'focus' | 'skip' | 'replay' | 'micro_pause';
  value: number;
  contentId?: string;
  metadata?: Record<string, unknown>;
}

// Batch of telemetry events for WebSocket transmission
export interface TelemetryBatch {
  userId: string;
  sessionId: string;
  events: TelemetryEvent[];
  windowStart: number;
  windowEnd: number;
}

export interface ContextualSignals {
  timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
  dayOfWeek: string;
  device: 'mobile' | 'tablet' | 'desktop' | 'tv';
  sessionDuration: number;
  previousSessions: number;
}

export interface Recommendation {
  content: Content;
  matchScore: number; // 0-100
  reasoning: string;
  microPitch: MicroPitch;
  sequencePosition: number;
  diversityContribution: number;
}

export interface MicroPitch {
  script: string; // 7-10 second narration script
  headline: string;
  hook: string;
  personalizedReason: string;
  standoutMoment: string;
  funFact: string;
  callToAction: string;
}

export interface NLPIntent {
  action: 'recommend' | 'search' | 'explore' | 'continue';
  context: string;
  preferences: string[];
  mood?: ContentMood;
  urgency: 'relaxed' | 'normal' | 'immediate';
  constraints?: string[];
}

export interface ReelState {
  recommendations: Recommendation[];
  currentIndex: number;
  isPlaying: boolean;
  autoAdvance: boolean;
  audioEnabled: boolean;
  interactionHistory: ReelInteraction[];
}

export interface ReelInteraction {
  contentId: string;
  action: 'view' | 'skip' | 'select' | 'dismiss' | 'replay';
  timestamp: Date;
  viewDuration: number;
}

export interface RecommendationRequest {
  query?: string;
  userProfile: UserProfile;
  constraints?: {
    maxResults?: number;
    excludeContentIds?: string[];
    forceGenres?: string[];
  };
}

export interface RecommendationResponse {
  recommendations: Recommendation[];
  processingTime: number;
  confidence: number;
  diversityScore: number;
  decisionSupportScore: number; // How well this reduces decision stress
}
