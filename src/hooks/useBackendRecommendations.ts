/**
 * Hook for fetching recommendations from backend API
 * Falls back to local engine if backend is unavailable
 */
import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import { generateRecommendations } from '../engine/recommendationEngine';
import { UserProfile, RecommendationResponse } from '../types';
import { useAppStore } from '../store/appStore';

interface UseBackendRecommendationsReturn {
  fetchRecommendations: (query: string) => Promise<RecommendationResponse>;
  isLoading: boolean;
  error: string | null;
  isBackendAvailable: boolean;
}

export function useBackendRecommendations(): UseBackendRecommendationsReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isBackendAvailable, setIsBackendAvailable] = useState(true);
  const { userProfile } = useAppStore();

  const fetchRecommendations = useCallback(async (query: string): Promise<RecommendationResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      // Try backend first
      if (isBackendAvailable) {
        try {
          const response = await apiClient.generateRecommendations({
            query,
            user_profile: convertToBackendProfile(userProfile),
            constraints: {
              max_results: 5,
            },
          });

          // Convert backend response to frontend format
          return convertFromBackendResponse(response);
        } catch (backendError) {
          console.warn('Backend unavailable, falling back to local engine:', backendError);
          setIsBackendAvailable(false);
        }
      }

      // Fallback to local engine
      return generateRecommendations({
        query,
        userProfile,
        constraints: {
          maxResults: 5,
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch recommendations';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [userProfile, isBackendAvailable]);

  return {
    fetchRecommendations,
    isLoading,
    error,
    isBackendAvailable,
  };
}

// Convert frontend user profile to backend format
function convertToBackendProfile(profile: UserProfile): any {
  return {
    id: profile.id,
    viewing_history: profile.viewingHistory.map(record => ({
      content_id: record.contentId,
      watched_at: record.watchedAt.toISOString(),
      completion_rate: record.completionRate,
      rewatched: record.rewatched,
      rating: record.rating,
      engagement_score: record.engagementScore,
    })),
    preferences: {
      favorite_genres: profile.preferences.favoriteGenres,
      disliked_genres: profile.preferences.dislikedGenres,
      preferred_moods: profile.preferences.preferredMoods,
      preferred_duration: profile.preferences.preferredDuration,
      maturity_rating: profile.preferences.maturityRating,
    },
    decision_state: {
      stress_level: profile.decisionState.stressLevel,
      scroll_velocity: profile.decisionState.scrollVelocity,
      dwell_time: profile.decisionState.dwellTime,
      focus_changes: profile.decisionState.focusChanges,
      search_rewrites: profile.decisionState.searchRewrites,
      confidence_score: profile.decisionState.confidenceScore,
    },
    contextual_signals: {
      time_of_day: profile.contextualSignals.timeOfDay,
      day_of_week: profile.contextualSignals.dayOfWeek,
      device: profile.contextualSignals.device,
      session_duration: profile.contextualSignals.sessionDuration,
      previous_sessions: profile.contextualSignals.previousSessions,
    },
  };
}

// Convert backend response to frontend format
function convertFromBackendResponse(response: any): RecommendationResponse {
  return {
    recommendations: response.recommendations.map((rec: any, index: number) => ({
      content: {
        id: rec.content.id,
        title: rec.content.title,
        type: rec.content.type,
        genre: rec.content.genre,
        year: rec.content.year,
        rating: rec.content.rating,
        duration: rec.content.duration,
        posterUrl: rec.content.poster_url,
        backdropUrl: rec.content.backdrop_url,
        description: rec.content.description,
        cast: rec.content.cast,
        director: rec.content.director,
        themes: rec.content.themes,
        mood: rec.content.mood,
        standoutScenes: rec.content.standout_scenes,
        funFacts: rec.content.fun_facts,
        trailerUrl: rec.content.trailer_url,
      },
      matchScore: rec.match_score,
      reasoning: rec.reasoning,
      microPitch: {
        script: rec.micro_pitch.script,
        headline: rec.micro_pitch.headline,
        hook: rec.micro_pitch.hook,
        personalizedReason: rec.micro_pitch.personalized_reason,
        standoutMoment: rec.micro_pitch.standout_moment,
        funFact: rec.micro_pitch.fun_fact,
        callToAction: rec.micro_pitch.call_to_action,
      },
      sequencePosition: index,
      diversityContribution: rec.diversity_contribution,
    })),
    processingTime: response.processing_time_ms,
    confidence: response.confidence,
    diversityScore: response.diversity_score,
    decisionSupportScore: response.decision_support_score,
  };
}
