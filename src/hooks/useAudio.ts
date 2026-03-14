/**
 * Audio Hook - Uses backend TTS with Web Speech API fallback
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE_URL, apiClient } from '../api/client';

interface UseAudioOptions {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}

interface UseAudioReturn {
  speak: (text: string) => Promise<void>;
  stop: () => void;
  isPlaying: boolean;
  isLoading: boolean;
  error: string | null;
  audioMethod: 'backend' | 'webspeech' | 'none';
}

export function useAudio(options: UseAudioOptions = {}): UseAudioReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [audioMethod, setAudioMethod] = useState<'backend' | 'webspeech' | 'none'>('backend');
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const abortRef = useRef(false);
  const optionsRef = useRef(options);
  
  // Keep options ref updated
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  // Check available audio methods on mount
  useEffect(() => {
    const checkAudioMethods = async () => {
      // Try backend first
      try {
        const stats = await apiClient.getAudioStats();
        console.log('Audio stats:', stats);
        if (stats.tts_enabled) {
          setAudioMethod('backend');
          console.log('Using backend TTS');
          return;
        }
      } catch (err) {
        console.log('Backend TTS not available:', err);
      }
      
      // Fall back to Web Speech API
      if ('speechSynthesis' in window) {
        setAudioMethod('webspeech');
        console.log('Using Web Speech API');
        return;
      }
      
      setAudioMethod('none');
      console.log('No audio method available');
    };
    
    checkAudioMethods();
  }, []);

  const stop = useCallback(() => {
    abortRef.current = true;
    
    // Stop HTML5 audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.src = '';
      audioRef.current = null;
    }
    
    // Stop Web Speech
    if (utteranceRef.current) {
      window.speechSynthesis?.cancel();
      utteranceRef.current = null;
    }
    
    setIsPlaying(false);
    setIsLoading(false);
  }, []);

  const speakWithBackend = useCallback(async (text: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      console.log('Generating audio for:', text.substring(0, 50) + '...');
      
      const response = await apiClient.generateAudio(text, 'default', 1.0);
      console.log('Audio response:', response);
      
      if (abortRef.current) {
        setIsLoading(false);
        return false;
      }
      
      // Create audio element
      const audioUrl = `${API_BASE_URL}${response.audio_url}`;
      console.log('Playing audio from:', audioUrl);
      
      const audio = new Audio();
      audioRef.current = audio;
      
      return new Promise((resolve) => {
        let resolved = false;
        
        const cleanup = () => {
          if (!resolved) {
            resolved = true;
            setIsLoading(false);
          }
        };
        
        audio.onloadeddata = () => {
          console.log('Audio loaded');
        };
        
        audio.oncanplaythrough = () => {
          if (abortRef.current || resolved) {
            cleanup();
            resolve(false);
            return;
          }
          console.log('Audio can play through');
          setIsLoading(false);
          setIsPlaying(true);
          optionsRef.current.onStart?.();
          
          audio.play()
            .then(() => console.log('Audio playing'))
            .catch((err) => {
              console.error('Audio play failed:', err);
              cleanup();
              resolve(false);
            });
        };
        
        audio.onended = () => {
          console.log('Audio ended');
          setIsPlaying(false);
          optionsRef.current.onEnd?.();
          cleanup();
          resolve(true);
        };
        
        audio.onerror = (e) => {
          console.error('Audio error:', e);
          cleanup();
          resolve(false);
        };
        
        // Set source and load
        audio.src = audioUrl;
        audio.load();
        
        // Timeout for loading
        setTimeout(() => {
          if (!resolved && isLoading) {
            console.log('Audio loading timeout');
            cleanup();
            resolve(false);
          }
        }, 15000);
      });
    } catch (err) {
      console.error('Backend TTS error:', err);
      setIsLoading(false);
      return false;
    }
  }, [isLoading]);

  const speakWithWebSpeech = useCallback(async (text: string): Promise<boolean> => {
    if (!('speechSynthesis' in window)) return false;
    
    console.log('Trying Web Speech API');
    
    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance;
      
      // Get best available voice
      const voices = window.speechSynthesis.getVoices();
      const englishVoice = voices.find(v => 
        v.name.includes('Samantha') || 
        v.name.includes('Daniel') ||
        v.name.includes('Karen') ||
        v.lang.startsWith('en')
      );
      if (englishVoice) {
        utterance.voice = englishVoice;
      }
      
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      
      utterance.onstart = () => {
        if (abortRef.current) {
          window.speechSynthesis.cancel();
          resolve(false);
          return;
        }
        setIsPlaying(true);
        optionsRef.current.onStart?.();
      };
      
      utterance.onend = () => {
        setIsPlaying(false);
        optionsRef.current.onEnd?.();
        resolve(true);
      };
      
      utterance.onerror = (event) => {
        if (event.error !== 'interrupted' && event.error !== 'canceled') {
          console.warn('Web Speech error:', event.error);
        }
        setIsPlaying(false);
        resolve(false);
      };
      
      // Chrome bug workaround
      window.speechSynthesis.cancel();
      
      setTimeout(() => {
        if (!abortRef.current) {
          window.speechSynthesis.speak(utterance);
        } else {
          resolve(false);
        }
      }, 50);
    });
  }, []);

  const speak = useCallback(async (text: string) => {
    stop();
    abortRef.current = false;
    setError(null);
    
    if (!text.trim()) {
      optionsRef.current.onEnd?.();
      return;
    }
    
    console.log('Speaking with method:', audioMethod);
    
    // Try backend TTS first (always try if available)
    const backendSuccess = await speakWithBackend(text);
    if (backendSuccess) return;
    
    // Fall back to Web Speech API
    if (audioMethod === 'webspeech' || audioMethod === 'backend') {
      const webSpeechSuccess = await speakWithWebSpeech(text);
      if (webSpeechSuccess) return;
    }
    
    // No audio available
    console.log('No audio method succeeded');
    setError('Audio not available');
    optionsRef.current.onError?.('Audio playback not available');
    optionsRef.current.onEnd?.();
  }, [audioMethod, speakWithBackend, speakWithWebSpeech, stop]);

  return {
    speak,
    stop,
    isPlaying,
    isLoading,
    error,
    audioMethod
  };
}
