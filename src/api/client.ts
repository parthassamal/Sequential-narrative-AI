/**
 * API Client for Sequential Narrative AI Backend
 */
import { Recommendation, UserProfile, Content, MicroPitch } from '../types';

// Use environment variable in production, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8888';

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  getBaseUrl() {
    return this.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: FetchOptions = {}
  ): Promise<T> {
    const { params, ...fetchOptions } = options;
    
    let url = `${this.baseUrl}${endpoint}`;
    
    if (params) {
      const searchParams = new URLSearchParams(params);
      url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async healthCheck() {
    return this.request<{
      status: string;
      version: string;
      services: Record<string, string>;
    }>('/health');
  }

  // Recommendations API
  async generateRecommendations(request: {
    query?: string;
    user_profile: any;
    constraints?: {
      max_results?: number;
      exclude_content_ids?: string[];
    };
  }) {
    return this.request<any>('/api/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async processQuery(query: string, userContext?: any) {
    return this.request<{
      intent: any;
      narrative: string;
      suggested_prompts: string[];
    }>('/api/recommendations/process-query', {
      method: 'POST',
      body: JSON.stringify({ query, user_context: userContext }),
    });
  }

  async getContentCatalog(options?: { genre?: string; search?: string; limit?: number }) {
    const params: Record<string, string> = {};
    if (options?.genre) params.genre = options.genre;
    if (options?.search) params.search = options.search;
    if (options?.limit) params.limit = options.limit.toString();
    
    return this.request<any[]>('/api/recommendations/content', { params });
  }

  async getContentDetail(contentId: string) {
    return this.request<any>(`/api/recommendations/content/${contentId}`);
  }

  // Decision State API
  async updateDecisionState(request: {
    user_id: string;
    scroll_velocity: number;
    dwell_time: number;
    focus_changes: number;
    interaction_type?: string;
  }) {
    return this.request<{
      user_id: string;
      decision_state: any;
      recommendation_count: number;
      should_intervene: boolean;
      intervention_message?: string;
    }>('/api/decision-state/update', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getDecisionState(userId: string) {
    return this.request<any>(`/api/decision-state/${userId}`);
  }

  async logInteraction(request: {
    user_id: string;
    content_id: string;
    action: 'view' | 'skip' | 'select' | 'dismiss' | 'replay';
    view_duration: number;
  }) {
    return this.request<any>('/api/decision-state/log-interaction', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getSessionSummary(userId: string) {
    return this.request<any>(`/api/decision-state/${userId}/summary`);
  }

  async resetSession(userId: string) {
    return this.request<any>(`/api/decision-state/${userId}/reset`, {
      method: 'POST',
    });
  }

  // Audio API
  async generateAudio(text: string, voice: string = 'default', speed: number = 1.0) {
    return this.request<{
      audio_url: string;
      duration_seconds: number;
      text: string;
    }>('/api/audio/generate', {
      method: 'POST',
      body: JSON.stringify({ text, voice, speed }),
    });
  }

  getAudioUrl(filename: string) {
    return `${this.baseUrl}/audio/${filename}`;
  }

  async getAudioStats() {
    return this.request<{
      backend: string;
      cache_dir: string;
      cached_files: number;
      total_size_mb: number;
      tts_enabled: boolean;
    }>('/api/audio/stats');
  }

  // Streaming APIs
  async getStreamingProviders() {
    return this.request<{
      providers: any[];
      total: number;
    }>('/api/streaming/providers');
  }

  async searchStreaming(query: string, provider?: string, limit: number = 10) {
    const params: Record<string, string> = { q: query, limit: limit.toString() };
    if (provider) params.provider = provider;
    return this.request<{
      query: string;
      provider: string;
      results: any[];
      total: number;
    }>('/api/streaming/search', { params });
  }

  async getTrendingContent(provider?: string, limit: number = 20) {
    const params: Record<string, string> = { limit: limit.toString() };
    if (provider) params.provider = provider;
    return this.request<{
      provider: string;
      results: any[];
      total: number;
    }>('/api/streaming/trending', { params });
  }

  async getStreamingContentDetails(contentId: string) {
    return this.request<any>(`/api/streaming/content/${contentId}`);
  }

  async getParamountStatus() {
    return this.request<{
      status: string;
      message: string;
      demo_content_available: boolean;
      enterprise_integration: any;
    }>('/api/streaming/paramount/status');
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export class for custom instances
export { APIClient };

// ============================================
// TRANSFORMERS: Convert backend snake_case to frontend camelCase
// ============================================

/**
 * Transform backend content response to frontend Content type
 */
export function transformContent(backendContent: any): Content {
  return {
    id: backendContent.id,
    title: backendContent.title,
    type: backendContent.type,
    genre: backendContent.genre,
    year: backendContent.year,
    rating: backendContent.rating,
    duration: backendContent.duration,
    posterUrl: backendContent.poster_url,
    backdropUrl: backendContent.backdrop_url,
    description: backendContent.description,
    cast: backendContent.cast || [],
    director: backendContent.director || '',
    themes: backendContent.themes || [],
    mood: backendContent.mood || [],
    standoutScenes: backendContent.standout_scenes || [],
    funFacts: backendContent.fun_facts || [],
    trailerUrl: backendContent.trailer_url,
    streamingUrl: backendContent.streaming_url,
    provider: backendContent.provider,
  };
}

/**
 * Transform backend micro_pitch to frontend MicroPitch type
 */
export function transformMicroPitch(backendPitch: any): MicroPitch {
  return {
    script: backendPitch.script,
    headline: backendPitch.headline,
    hook: backendPitch.hook,
    personalizedReason: backendPitch.personalized_reason,
    standoutMoment: backendPitch.standout_moment,
    funFact: backendPitch.fun_fact,
    callToAction: backendPitch.call_to_action,
  };
}

/**
 * Transform backend recommendation to frontend Recommendation type
 */
export function transformRecommendation(backendRec: any): Recommendation {
  return {
    content: transformContent(backendRec.content),
    matchScore: backendRec.match_score,
    reasoning: backendRec.reasoning,
    microPitch: transformMicroPitch(backendRec.micro_pitch),
    sequencePosition: backendRec.sequence_position,
    diversityContribution: backendRec.diversity_contribution,
  };
}

/**
 * Transform array of backend recommendations
 */
export function transformRecommendations(backendRecs: any[]): Recommendation[] {
  return backendRecs.map(transformRecommendation);
}

/**
 * Transform frontend UserProfile to backend format (camelCase to snake_case)
 */
export function transformUserProfileToBackend(profile: UserProfile): any {
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
