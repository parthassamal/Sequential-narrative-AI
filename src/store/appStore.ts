import { create } from 'zustand';
import { 
  UserProfile, 
  ReelState, 
  Recommendation,
  ReelInteraction,
  DecisionState,
  ContextualSignals
} from '../types';

interface AppState {
  // User State
  userProfile: UserProfile;
  updateUserProfile: (updates: Partial<UserProfile>) => void;
  updateDecisionState: (updates: Partial<DecisionState>) => void;
  
  // Reel State
  reelState: ReelState;
  setRecommendations: (recommendations: Recommendation[]) => void;
  setCurrentIndex: (index: number) => void;
  nextRecommendation: () => void;
  previousRecommendation: () => void;
  togglePlayback: () => void;
  toggleAutoAdvance: () => void;
  toggleAudio: () => void;
  addInteraction: (interaction: ReelInteraction) => void;
  
  // UI State
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  showReel: boolean;
  setShowReel: (show: boolean) => void;
  currentQuery: string;
  setCurrentQuery: (query: string) => void;
  
  // Decision Support
  updateStressIndicators: (scrollVelocity: number, dwellTime: number, focusChanges: number) => void;
}

const getTimeOfDay = (): ContextualSignals['timeOfDay'] => {
  const hour = new Date().getHours();
  if (hour >= 5 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 21) return 'evening';
  return 'night';
};

const getDayOfWeek = (): string => {
  return new Date().toLocaleDateString('en-US', { weekday: 'long' });
};

// Default user profile for demo
const defaultUserProfile: UserProfile = {
  id: 'demo-user',
  viewingHistory: [
    {
      contentId: '1',
      watchedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      completionRate: 1,
      rewatched: false,
      rating: 5,
      engagementScore: 0.95
    },
    {
      contentId: '4',
      watchedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      completionRate: 0.8,
      rewatched: true,
      rating: 4,
      engagementScore: 0.85
    }
  ],
  preferences: {
    favoriteGenres: ['Sci-Fi', 'Thriller', 'Drama', 'Documentary'],
    dislikedGenres: [],
    preferredMoods: ['thrilling', 'thought-provoking', 'mysterious'],
    preferredDuration: 'medium',
    maturityRating: 'R'
  },
  decisionState: {
    stressLevel: 0.3,
    scrollVelocity: 0,
    dwellTime: 0,
    focusChanges: 0,
    searchRewrites: 0,
    confidenceScore: 0.7
  },
  contextualSignals: {
    timeOfDay: getTimeOfDay(),
    dayOfWeek: getDayOfWeek(),
    device: 'desktop',
    sessionDuration: 0,
    previousSessions: 12
  }
};

const defaultReelState: ReelState = {
  recommendations: [],
  currentIndex: 0,
  isPlaying: false,
  autoAdvance: true,
  audioEnabled: true,
  interactionHistory: []
};

export const useAppStore = create<AppState>((set, get) => ({
  // User State
  userProfile: defaultUserProfile,
  
  updateUserProfile: (updates) => set((state) => ({
    userProfile: { ...state.userProfile, ...updates }
  })),
  
  updateDecisionState: (updates) => set((state) => ({
    userProfile: {
      ...state.userProfile,
      decisionState: { ...state.userProfile.decisionState, ...updates }
    }
  })),
  
  // Reel State
  reelState: defaultReelState,
  
  setRecommendations: (recommendations) => set((state) => ({
    reelState: { 
      ...state.reelState, 
      recommendations, 
      currentIndex: 0,
      isPlaying: true 
    }
  })),
  
  setCurrentIndex: (index) => set((state) => ({
    reelState: { ...state.reelState, currentIndex: index }
  })),
  
  nextRecommendation: () => set((state) => {
    const nextIndex = Math.min(
      state.reelState.currentIndex + 1,
      state.reelState.recommendations.length - 1
    );
    return {
      reelState: { ...state.reelState, currentIndex: nextIndex }
    };
  }),
  
  previousRecommendation: () => set((state) => {
    const prevIndex = Math.max(state.reelState.currentIndex - 1, 0);
    return {
      reelState: { ...state.reelState, currentIndex: prevIndex }
    };
  }),
  
  togglePlayback: () => set((state) => ({
    reelState: { ...state.reelState, isPlaying: !state.reelState.isPlaying }
  })),
  
  toggleAutoAdvance: () => set((state) => ({
    reelState: { ...state.reelState, autoAdvance: !state.reelState.autoAdvance }
  })),
  
  toggleAudio: () => set((state) => ({
    reelState: { ...state.reelState, audioEnabled: !state.reelState.audioEnabled }
  })),
  
  addInteraction: (interaction) => set((state) => ({
    reelState: {
      ...state.reelState,
      interactionHistory: [...state.reelState.interactionHistory, interaction]
    }
  })),
  
  // UI State
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
  
  showReel: false,
  setShowReel: (show) => set({ showReel: show }),
  
  currentQuery: '',
  setCurrentQuery: (query) => set({ currentQuery: query }),
  
  // Decision Support - track user behavior to detect stress
  updateStressIndicators: (scrollVelocity, dwellTime, focusChanges) => {
    const state = get();
    
    // Calculate stress level based on behavioral signals
    // High scroll velocity + low dwell time + many focus changes = high stress
    const velocityFactor = Math.min(scrollVelocity / 1000, 1) * 0.3;
    const dwellFactor = dwellTime < 2000 ? 0.3 : dwellTime < 5000 ? 0.15 : 0;
    const focusFactor = Math.min(focusChanges / 10, 1) * 0.4;
    
    const newStressLevel = velocityFactor + dwellFactor + focusFactor;
    
    set({
      userProfile: {
        ...state.userProfile,
        decisionState: {
          ...state.userProfile.decisionState,
          stressLevel: newStressLevel,
          scrollVelocity,
          dwellTime,
          focusChanges
        }
      }
    });
  }
}));
