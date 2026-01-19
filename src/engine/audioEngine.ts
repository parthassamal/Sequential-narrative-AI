// Audio Engine using Web Speech API
// Handles text-to-speech synthesis for micro-pitches

interface AudioQueueItem {
  id: string;
  text: string;
  onStart?: () => void;
  onEnd?: () => void;
}

class AudioEngine {
  private synthesis: SpeechSynthesis | null = null;
  private queue: AudioQueueItem[] = [];
  private isPlaying: boolean = false;
  private selectedVoice: SpeechSynthesisVoice | null = null;
  private volume: number = 1;
  private rate: number = 0.95; // Slightly slower for natural feel
  private pitch: number = 1.05; // Slightly higher for warmer tone
  private isReady: boolean = false;
  private initPromise: Promise<void> | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.synthesis = window.speechSynthesis;
      this.initPromise = this.initVoice();
    }
  }

  private async initVoice(): Promise<void> {
    if (!this.synthesis) return;
    
    // Wait for voices to load with timeout
    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        console.warn('Speech synthesis voice loading timed out');
        this.isReady = false;
        resolve();
      }, 3000);

      const setVoice = () => {
        clearTimeout(timeout);
        const voices = this.synthesis!.getVoices();
        
        if (voices.length === 0) {
          console.warn('No speech synthesis voices available');
          this.isReady = false;
          resolve();
          return;
        }
        
        // Prefer high-quality, natural-sounding English voices
        // Prioritize premium/neural voices first
        const preferredVoices = [
          // Premium macOS voices (most natural)
          'Samantha (Enhanced)',
          'Samantha',
          'Ava (Premium)',
          'Ava',
          'Zoe (Premium)',
          'Zoe',
          // Chrome/Edge premium voices
          'Google US English',
          'Microsoft Aria Online',
          'Microsoft Jenny Online',
          // Other good options
          'Karen',
          'Daniel (UK English)',
          'Daniel',
          'Moira',
          'Fiona',
          'Google UK English Female',
          'Google UK English Male',
        ];
        
        for (const preferred of preferredVoices) {
          const found = voices.find(v => 
            v.name.includes(preferred) || v.name === preferred
          );
          if (found) {
            this.selectedVoice = found;
            console.log(`Selected voice: ${found.name}`);
            break;
          }
        }
        
        // Fallback to first English voice with preference for female voices (often clearer)
        if (!this.selectedVoice) {
          const englishVoices = voices.filter(v => v.lang.startsWith('en'));
          this.selectedVoice = englishVoices.find(v => 
            v.name.toLowerCase().includes('female') || 
            v.name.includes('Samantha') ||
            v.name.includes('Karen')
          ) || englishVoices[0] || voices[0];
        }
        
        this.isReady = true;
        resolve();
      };

      // Chrome loads voices asynchronously
      if (this.synthesis!.getVoices().length > 0) {
        setVoice();
      } else {
        this.synthesis!.onvoiceschanged = setVoice;
        // Also try after a short delay (Safari workaround)
        setTimeout(() => {
          if (!this.isReady && this.synthesis!.getVoices().length > 0) {
            setVoice();
          }
        }, 100);
      }
    });
  }

  async speak(item: AudioQueueItem): Promise<void> {
    // Wait for initialization
    if (this.initPromise) {
      await this.initPromise;
    }
    
    if (!this.isSupported() || !this.isReady) {
      // Silently skip if not supported - call onEnd to not block UI
      item.onEnd?.();
      return;
    }
    
    this.queue.push(item);
    if (!this.isPlaying) {
      this.processQueue();
    }
  }

  private processQueue(): void {
    if (this.queue.length === 0 || !this.synthesis) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const item = this.queue.shift()!;
    
    try {
      // Cancel any ongoing speech first
      this.synthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(item.text);
      
      if (this.selectedVoice) {
        utterance.voice = this.selectedVoice;
      }
      
      utterance.volume = this.volume;
      utterance.rate = this.rate;
      utterance.pitch = this.pitch;
      
      utterance.onstart = () => {
        item.onStart?.();
      };
      
      utterance.onend = () => {
        item.onEnd?.();
        // Small delay before processing next to avoid race conditions
        setTimeout(() => this.processQueue(), 50);
      };
      
      utterance.onerror = (event) => {
        // Only log actual errors, not interruptions
        if (event.error !== 'interrupted' && event.error !== 'canceled') {
          console.warn('Speech synthesis issue:', event.error);
        }
        item.onEnd?.();
        setTimeout(() => this.processQueue(), 50);
      };
      
      this.synthesis.speak(utterance);
    } catch (error) {
      console.warn('Speech synthesis failed:', error);
      item.onEnd?.();
      this.processQueue();
    }
  }

  stop(): void {
    if (this.synthesis) {
      this.synthesis.cancel();
    }
    this.queue = [];
    this.isPlaying = false;
  }

  pause(): void {
    if (this.synthesis) {
      this.synthesis.pause();
    }
  }

  resume(): void {
    if (this.synthesis) {
      this.synthesis.resume();
    }
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));
  }

  setRate(rate: number): void {
    this.rate = Math.max(0.5, Math.min(2, rate));
  }

  setPitch(pitch: number): void {
    this.pitch = Math.max(0, Math.min(2, pitch));
  }

  getAvailableVoices(): SpeechSynthesisVoice[] {
    if (!this.synthesis) return [];
    return this.synthesis.getVoices().filter(v => v.lang.startsWith('en'));
  }

  selectVoice(voiceName: string): void {
    if (!this.synthesis) return;
    const voices = this.synthesis.getVoices();
    const voice = voices.find(v => v.name === voiceName);
    if (voice) {
      this.selectedVoice = voice;
    }
  }

  isSupported(): boolean {
    return typeof window !== 'undefined' && 'speechSynthesis' in window && this.synthesis !== null;
  }
  
  isInitialized(): boolean {
    return this.isReady;
  }

  isSpeaking(): boolean {
    return this.isPlaying;
  }
}

// Singleton instance
export const audioEngine = new AudioEngine();

// Helper function to generate audio-friendly text
export function prepareTextForSpeech(text: string): string {
  return text
    // Add natural pauses after sentences (shorter pause)
    .replace(/\. /g, '. ')
    .replace(/\.\.\./g, '... ')
    // Add slight pause after commas
    .replace(/, /g, ', ')
    // Handle numbers
    .replace(/(\d+)%/g, '$1 percent')
    // Handle common abbreviations
    .replace(/vs\./gi, 'versus')
    .replace(/etc\./gi, 'et cetera')
    .replace(/&amp;/g, 'and')
    .replace(/&/g, 'and')
    // Handle quotes for natural reading
    .replace(/"/g, '')
    .replace(/'/g, "'")
    // Remove emojis and special characters but keep basic punctuation
    .replace(/[^\w\s.,!?'"-]/g, '')
    // Clean up multiple spaces
    .replace(/\s+/g, ' ')
    .trim();
}

// Calculate estimated speech duration (words per minute ~150)
export function estimateSpeechDuration(text: string): number {
  const words = text.split(/\s+/).length;
  const wordsPerMinute = 150;
  return (words / wordsPerMinute) * 60 * 1000; // Return in milliseconds
}
