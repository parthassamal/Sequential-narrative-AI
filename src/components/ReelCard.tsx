import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Star, Clock, Film, Tv, BookOpen, Volume2, StopCircle, Youtube, ExternalLink, Check } from 'lucide-react';
import { Recommendation } from '../types';
import { useAppStore } from '../store/appStore';

interface ReelCardProps {
  recommendation: Recommendation;
  isActive: boolean;
  index: number;
  totalCards: number;
  onNarrationEnd?: () => void;
  autoPlayAudio?: boolean;
  onSelect?: (contentId: string) => void;
  onSelectionComplete?: () => void; // Called after selection is recorded
}

const typeIcons: Record<string, typeof Film> = {
  movie: Film,
  series: Tv,
  documentary: BookOpen,
  video: Youtube,
};

const providerColors: Record<string, string> = {
  tmdb: 'bg-emerald-500',
  youtube: 'bg-red-500',
  paramount: 'bg-blue-500',
};

const providerNames: Record<string, string> = {
  tmdb: 'TMDb',
  youtube: 'YouTube',
  paramount: 'Paramount+',
};

function withFallback(value: string | undefined, fallback: string): string {
  return value && value.trim().length > 0 ? value : fallback;
}

export function ReelCard({ recommendation, index, totalCards, onNarrationEnd, autoPlayAudio = false, onSelect, onSelectionComplete }: ReelCardProps) {
  const { content, matchScore, microPitch } = recommendation;
  const [imageLoaded, setImageLoaded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isSelected, setIsSelected] = useState(false);
  const { addInteraction } = useAppStore();
  const hasAutoPlayed = useRef(false);
  
  const TypeIcon = typeIcons[content.type] || Film;
  const providerColor = providerColors[content.provider || ''] || 'bg-gray-500';
  const providerName = providerNames[content.provider || ''] || content.provider;
  const hookText = withFallback(microPitch?.hook, content.description || 'A personalized pick selected for you.');
  const reasonText = withFallback(microPitch?.personalizedReason, 'Hand-picked based on your current preferences and viewing signals.');
  const funFactText = withFallback(microPitch?.funFact, 'Fresh recommendation with a strong relevance score for this session.');

  // Play audio function
  const playAudio = () => {
    window.speechSynthesis.cancel();
    
    const text = microPitch?.script || "No script available";
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    utterance.onstart = () => setIsPlaying(true);
    
    utterance.onend = () => {
      setIsPlaying(false);
      // Notify parent that narration finished - trigger next card
      if (onNarrationEnd) {
        // Small delay before advancing for better UX
        setTimeout(() => {
          onNarrationEnd();
        }, 500);
      }
    };
    
    utterance.onerror = (e) => {
      // Ignore "interrupted" and "canceled" - these are expected when navigating
      if (e.error !== 'interrupted' && e.error !== 'canceled') {
        console.warn('Speech synthesis error:', e.error);
      }
      setIsPlaying(false);
    };
    
    window.speechSynthesis.speak(utterance);
  };

  // Auto-play audio when card becomes active
  useEffect(() => {
    if (autoPlayAudio && !hasAutoPlayed.current) {
      hasAutoPlayed.current = true;
      // Small delay to let the card animate in
      const timer = setTimeout(() => {
        playAudio();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [autoPlayAudio]);

  // Reset auto-play flag when card changes
  useEffect(() => {
    hasAutoPlayed.current = false;
  }, [content.id]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
    };
  }, []);

  // Toggle audio manually
  const handleAudioToggle = () => {
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }
    playAudio();
  };

  const handlePlayClick = () => {
    if (isSelected) return; // Prevent double clicks
    
    window.speechSynthesis.cancel();
    setIsSelected(true);
    
    addInteraction({
      contentId: content.id,
      action: 'select',
      timestamp: new Date(),
      viewDuration: 0,
    });
    
    // Track selection in analytics
    onSelect?.(content.id);
    
    // Open the streaming URL if available
    if (content.streamingUrl) {
      window.open(content.streamingUrl, '_blank');
    }
    
    // Show success state then close after a delay
    setTimeout(() => {
      onSelectionComplete?.();
    }, 1500);
  };

  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="relative w-full max-w-4xl mx-4 aspect-[16/10] rounded-3xl overflow-hidden shadow-2xl">
        {/* Background Image */}
        <motion.div
          className="absolute inset-0"
          animate={{ scale: [1, 1.1], x: [0, -20], y: [0, -10] }}
          transition={{ duration: 20, ease: "linear", repeat: Infinity, repeatType: "reverse" }}
        >
          <img
            src={content.backdropUrl}
            alt={content.title}
            className={`w-full h-full object-cover transition-opacity duration-700 ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
            onLoad={() => setImageLoaded(true)}
          />
          {!imageLoaded && <div className="absolute inset-0 bg-midnight-800 animate-pulse" />}
        </motion.div>

        {/* Gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-midnight-950 via-midnight-950/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-midnight-950/80 via-transparent to-transparent" />

        {/* Progress */}
        <div className="absolute top-6 left-6 right-6 flex gap-2">
          {Array.from({ length: totalCards }).map((_, i) => (
            <div key={i} className="flex-1 h-1 rounded-full overflow-hidden bg-white/20">
              <div 
                className="h-full bg-amber-400 transition-all duration-300"
                style={{ width: i <= index ? '100%' : '0%' }}
              />
            </div>
          ))}
        </div>

        {/* Provider Badge & Match Score */}
        <div className="absolute top-16 right-6 flex flex-col gap-2 items-end">
          {content.provider && (
            <div className={`${providerColor} px-3 py-1 rounded-full text-white text-xs font-bold uppercase tracking-wider shadow-lg`}>
              {providerName}
            </div>
          )}
          <div className="flex items-center gap-2 bg-midnight-950/80 backdrop-blur-md px-4 py-2 rounded-full border border-amber-400/30">
            <span className="text-amber-400 font-mono text-sm font-bold">{Math.round(matchScore)}%</span>
            <span className="text-white/70 text-xs">match</span>
          </div>
        </div>

        {/* Audio Toggle Button */}
        <button
          type="button"
          onClick={handleAudioToggle}
          className={`absolute top-16 left-6 flex items-center gap-2 px-4 py-3 rounded-full shadow-lg z-[100] transition-all ${
            isPlaying 
              ? 'bg-red-500 hover:bg-red-400' 
              : 'bg-amber-500 hover:bg-amber-400'
          }`}
        >
          {isPlaying ? (
            <>
              <StopCircle className="w-5 h-5 text-white" />
              <span className="text-white font-semibold text-sm">Stop</span>
            </>
          ) : (
            <>
              <Volume2 className="w-5 h-5 text-black" />
              <span className="text-black font-semibold text-sm">Listen</span>
            </>
          )}
        </button>

        {/* Content */}
        <div className="absolute bottom-0 left-0 right-0 p-8">
          {/* Type & Genre */}
          <div className="flex items-center gap-3 mb-4">
            <span className="flex items-center gap-1.5 text-amber-400 text-sm font-medium">
              <TypeIcon className="w-4 h-4" />
              {content.type.charAt(0).toUpperCase() + content.type.slice(1)}
            </span>
            <span className="text-white/30">•</span>
            {content.genre.slice(0, 3).map((genre, i, arr) => (
              <span key={genre} className="text-white/60 text-sm">
                {genre}{i < arr.length - 1 ? ' / ' : ''}
              </span>
            ))}
          </div>

          {/* Title */}
          <h2 className="font-display text-5xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            {content.title}
          </h2>

          {/* Meta */}
          <div className="flex items-center gap-4 mb-6">
            <span className="flex items-center gap-1.5 text-amber-400">
              <Star className="w-5 h-5 fill-current" />
              <span className="font-bold">{content.rating}</span>
            </span>
            <span className="flex items-center gap-1.5 text-white/70">
              <Clock className="w-4 h-4" />
              {content.duration}
            </span>
            <span className="text-white/50">{content.year}</span>
          </div>

          {/* Hook */}
          <p className="text-lg text-white/90 leading-relaxed max-w-2xl mb-6">
            {hookText}
          </p>

          {/* Why you'll love this */}
          <div className="bg-white/5 backdrop-blur-sm rounded-xl p-4 mb-6 border border-white/10">
            <p className="text-teal-400 text-sm font-medium mb-1">Why you'll love this</p>
            <p className="text-white/80 text-sm">{reasonText}</p>
          </div>

          {/* Fun Fact */}
          <div className="flex items-start gap-3 mb-8">
            <span className="text-amber-400 text-xl">✦</span>
            <p className="text-white/70 text-sm italic">{funFactText}</p>
          </div>

          {/* CTA */}
          <button
            className={`flex items-center gap-3 px-8 py-4 rounded-full font-bold text-lg shadow-lg transition-all ${
              isSelected 
                ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white scale-105' 
                : 'bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-midnight-950 hover:scale-105'
            }`}
            onClick={handlePlayClick}
            disabled={isSelected}
          >
            {isSelected ? (
              <>
                <Check className="w-6 h-6" />
                <span>Added to Watch List!</span>
              </>
            ) : (
              <>
                <Play className="w-6 h-6 fill-current" />
                <span>Watch on {providerName || 'Platform'}</span>
                {content.streamingUrl && <ExternalLink className="w-5 h-5" />}
              </>
            )}
          </button>
        </div>
        
        {/* Selection Success Overlay */}
        <AnimatePresence>
          {isSelected && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-green-500/20 backdrop-blur-sm flex items-center justify-center z-50"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="bg-green-500 rounded-full p-6"
              >
                <Check className="w-16 h-16 text-white" />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Glow */}
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-amber-500/20 rounded-full blur-3xl pointer-events-none" />
      </div>
    </div>
  );
}
