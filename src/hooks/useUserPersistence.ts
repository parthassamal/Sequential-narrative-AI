/**
 * User Persistence Hook
 * Manages user profile, watch history, and preferences in localStorage
 */
import { useState, useEffect, useCallback } from 'react';

export interface WatchHistoryItem {
  contentId: string;
  title: string;
  type: 'movie' | 'series' | 'video';
  provider: string;
  watchedAt: string;
  completionRate: number;
  rating?: number;
}

export interface UserPreferences {
  favoriteGenres: string[];
  dislikedGenres: string[];
  preferredProviders: string[];
  preferredMoods: string[];
  maturityRating: 'G' | 'PG' | 'PG-13' | 'R';
}

export interface PersistedUser {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  createdAt: string;
  lastLoginAt: string;
  preferences: UserPreferences;
  watchHistory: WatchHistoryItem[];
  likedContent: string[];
  dislikedContent: string[];
}

const STORAGE_KEY = 'vibe_ai_user';

export function useUserPersistence() {
  const [user, setUser] = useState<PersistedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load user from localStorage on mount
  useEffect(() => {
    const loadUser = () => {
      try {
        const storedUser = localStorage.getItem(STORAGE_KEY);
        if (storedUser) {
          const parsed = JSON.parse(storedUser);
          setUser(parsed);
        }
      } catch (error) {
        console.error('Error loading user:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadUser();
  }, []);

  // Save user to localStorage whenever it changes
  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    }
  }, [user]);

  // Create or update user
  const saveUser = useCallback((userData: { name: string; email: string; avatar?: string }) => {
    const now = new Date().toISOString();
    
    setUser(prev => {
      if (prev) {
        // Update existing user
        return {
          ...prev,
          ...userData,
          lastLoginAt: now,
        };
      }
      
      // Create new user
      return {
        id: `user_${Date.now()}`,
        ...userData,
        createdAt: now,
        lastLoginAt: now,
        preferences: {
          favoriteGenres: [],
          dislikedGenres: [],
          preferredProviders: ['tmdb', 'youtube', 'paramount'],
          preferredMoods: [],
          maturityRating: 'PG-13',
        },
        watchHistory: [],
        likedContent: [],
        dislikedContent: [],
      };
    });
  }, []);

  // Clear user (logout)
  const clearUser = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // Add to watch history
  const addToWatchHistory = useCallback((item: Omit<WatchHistoryItem, 'watchedAt'>) => {
    setUser(prev => {
      if (!prev) return prev;
      
      const newItem: WatchHistoryItem = {
        ...item,
        watchedAt: new Date().toISOString(),
      };
      
      // Remove duplicate if exists
      const filteredHistory = prev.watchHistory.filter(h => h.contentId !== item.contentId);
      
      return {
        ...prev,
        watchHistory: [newItem, ...filteredHistory].slice(0, 100), // Keep last 100
      };
    });
  }, []);

  // Update preferences
  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setUser(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          ...updates,
        },
      };
    });
  }, []);

  // Like content
  const likeContent = useCallback((contentId: string) => {
    setUser(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        likedContent: [...new Set([...prev.likedContent, contentId])],
        dislikedContent: prev.dislikedContent.filter(id => id !== contentId),
      };
    });
  }, []);

  // Dislike content
  const dislikeContent = useCallback((contentId: string) => {
    setUser(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        dislikedContent: [...new Set([...prev.dislikedContent, contentId])],
        likedContent: prev.likedContent.filter(id => id !== contentId),
      };
    });
  }, []);

  // Add favorite genre
  const addFavoriteGenre = useCallback((genre: string) => {
    setUser(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        preferences: {
          ...prev.preferences,
          favoriteGenres: [...new Set([...prev.preferences.favoriteGenres, genre])],
          dislikedGenres: prev.preferences.dislikedGenres.filter(g => g !== genre),
        },
      };
    });
  }, []);

  // Get recommendation weight for content
  const getContentWeight = useCallback((contentId: string, genres: string[]): number => {
    if (!user) return 1;
    
    let weight = 1;
    
    // Boost if user liked similar content
    if (user.likedContent.includes(contentId)) {
      weight += 0.5;
    }
    
    // Reduce if disliked
    if (user.dislikedContent.includes(contentId)) {
      weight -= 0.8;
    }
    
    // Boost for favorite genres
    const matchingGenres = genres.filter(g => user.preferences.favoriteGenres.includes(g));
    weight += matchingGenres.length * 0.2;
    
    // Reduce for disliked genres
    const dislikedGenres = genres.filter(g => user.preferences.dislikedGenres.includes(g));
    weight -= dislikedGenres.length * 0.3;
    
    return Math.max(0.1, Math.min(2, weight));
  }, [user]);

  return {
    user,
    isLoading,
    saveUser,
    clearUser,
    addToWatchHistory,
    updatePreferences,
    likeContent,
    dislikeContent,
    addFavoriteGenre,
    getContentWeight,
  };
}
