import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform, PanInfo } from 'framer-motion';
import { 
  Sparkles, Search, Mic, Loader2, Brain, Zap, Heart, Ghost, Film, 
  Laugh, Skull, Clock, Users, Star, Compass, Flame, Coffee, Moon,
  Tv, Popcorn, Trophy, Baby, Rocket, Music, ChevronLeft, ChevronRight,
  Wand2, History, TrendingUp
} from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { apiClient, transformRecommendations, transformUserProfileToBackend } from '../api/client';
import { useAnalytics } from '../hooks/useAnalytics';

// Mood categories with full metadata
const MOOD_CATEGORIES = [
  { 
    id: 'exciting',
    icon: Zap, 
    label: "Exciting", 
    query: "Something exciting and action-packed",
    gradient: "from-orange-500 to-red-600",
    bgGradient: "bg-gradient-to-br from-orange-500 to-red-600",
    keywords: ['action', 'thriller', 'adventure', 'intense'],
    timePreference: ['evening', 'night'],
    emoji: "⚡"
  },
  { 
    id: 'relaxing',
    icon: Coffee, 
    label: "Relaxing", 
    query: "Something relaxing and calming",
    gradient: "from-teal-400 to-cyan-600",
    bgGradient: "bg-gradient-to-br from-teal-400 to-cyan-600",
    keywords: ['cozy', 'calm', 'feel-good', 'light'],
    timePreference: ['morning', 'afternoon'],
    emoji: "☕"
  },
  { 
    id: 'funny',
    icon: Laugh, 
    label: "Funny", 
    query: "Something funny to make me laugh",
    gradient: "from-yellow-400 to-amber-500",
    bgGradient: "bg-gradient-to-br from-yellow-400 to-amber-500",
    keywords: ['comedy', 'humor', 'laugh', 'sitcom'],
    timePreference: ['afternoon', 'evening'],
    emoji: "😂"
  },
  { 
    id: 'scary',
    icon: Skull, 
    label: "Scary", 
    query: "Something scary and thrilling",
    gradient: "from-purple-600 to-violet-800",
    bgGradient: "bg-gradient-to-br from-purple-600 to-violet-800",
    keywords: ['horror', 'thriller', 'suspense', 'dark'],
    timePreference: ['night'],
    emoji: "💀"
  },
  { 
    id: 'romantic',
    icon: Heart, 
    label: "Romantic", 
    query: "Something romantic",
    gradient: "from-pink-400 to-rose-600",
    bgGradient: "bg-gradient-to-br from-pink-400 to-rose-600",
    keywords: ['romance', 'love', 'drama', 'relationship'],
    timePreference: ['evening', 'night'],
    emoji: "💕"
  },
  { 
    id: 'mindblowing',
    icon: Brain, 
    label: "Mind-Blowing", 
    query: "Something thought-provoking and mind-blowing",
    gradient: "from-indigo-500 to-purple-600",
    bgGradient: "bg-gradient-to-br from-indigo-500 to-purple-600",
    keywords: ['sci-fi', 'mystery', 'twist', 'intellectual'],
    timePreference: ['evening', 'night'],
    emoji: "🤯"
  },
  { 
    id: 'documentary',
    icon: Film, 
    label: "Learn Something", 
    query: "A great documentary to learn something new",
    gradient: "from-emerald-500 to-green-600",
    bgGradient: "bg-gradient-to-br from-emerald-500 to-green-600",
    keywords: ['documentary', 'educational', 'true story', 'informative'],
    timePreference: ['morning', 'afternoon'],
    emoji: "📚"
  },
  { 
    id: 'surprise',
    icon: Ghost, 
    label: "Surprise Me", 
    query: "Surprise me with something unexpected",
    gradient: "from-fuchsia-500 to-pink-600",
    bgGradient: "bg-gradient-to-br from-fuchsia-500 to-pink-600",
    keywords: ['random', 'unexpected', 'discover', 'new'],
    timePreference: ['any'],
    emoji: "🎲"
  },
];

// Quick genre pills
const QUICK_GENRES = [
  { icon: Rocket, label: "Sci-Fi", query: "Best science fiction" },
  { icon: Trophy, label: "Award Winners", query: "Award-winning films and shows" },
  { icon: Clock, label: "Quick Watch", query: "Something short under 30 minutes" },
  { icon: Users, label: "Family Night", query: "Family-friendly content for all ages" },
  { icon: Star, label: "Classics", query: "Classic movies and shows" },
  { icon: Moon, label: "Late Night", query: "Something for late night viewing" },
  { icon: Tv, label: "Binge-Worthy", query: "Binge-worthy series" },
  { icon: Flame, label: "Trending", query: "Currently trending and popular" },
];

// Speech Recognition setup
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

// AI Mood Detection based on viewing history and context
function useAIMoodDetection() {
  const { userProfile } = useAppStore();
  
  const detectedMood = useMemo(() => {
    const timeOfDay = userProfile.contextualSignals.timeOfDay;
    const preferences = userProfile.preferences;
    const history = userProfile.viewingHistory;
    
    // Analyze recent viewing patterns
    const recentGenres = preferences.favoriteGenres || [];
    const preferredMoods = preferences.preferredMoods || [];
    
    // Score each mood based on user data
    const moodScores = MOOD_CATEGORIES.map(mood => {
      let score = 0;
      
      // Time of day match
      if (mood.timePreference.includes(timeOfDay) || mood.timePreference.includes('any')) {
        score += 30;
      }
      
      // Genre preference match
      mood.keywords.forEach(keyword => {
        if (recentGenres.some(g => g.toLowerCase().includes(keyword))) {
          score += 20;
        }
        if (preferredMoods.some(m => m.toLowerCase().includes(keyword))) {
          score += 15;
        }
      });
      
      // History engagement boost
      if (history.length > 0) {
        const avgEngagement = history.reduce((sum, h) => sum + (h.engagementScore || 0), 0) / history.length;
        score += avgEngagement * 10;
      }
      
      // Add some randomness for variety
      score += Math.random() * 10;
      
      return { mood, score };
    });
    
    // Sort by score and return top mood
    moodScores.sort((a, b) => b.score - a.score);
    
    return {
      primaryMood: moodScores[0].mood,
      confidence: Math.min(moodScores[0].score / 100, 0.95),
      reason: getReasonText(moodScores[0].mood, timeOfDay, recentGenres)
    };
  }, [userProfile]);
  
  return detectedMood;
}

function getReasonText(mood: typeof MOOD_CATEGORIES[0], timeOfDay: string, genres: string[]): string {
  const reasons: Record<string, string[]> = {
    exciting: [
      "Based on your love for action content",
      "Perfect for an adrenaline rush tonight",
      "Your thriller preferences suggest this"
    ],
    relaxing: [
      "Time to unwind after a busy day",
      "Perfect for a peaceful " + timeOfDay,
      "You've been watching a lot lately - time to relax"
    ],
    funny: [
      "Comedy always hits different in the " + timeOfDay,
      "Your recent watches suggest you need a laugh",
      "Perfect mood booster for today"
    ],
    scary: [
      "Late night is perfect for thrills",
      "Based on your horror favorites",
      "Ready for some suspense?"
    ],
    romantic: [
      "Perfect evening for something heartfelt",
      "Your drama preferences align with this",
      "Time for a feel-good romance"
    ],
    mindblowing: [
      "Your Sci-Fi preferences suggest this",
      "Ready for something thought-provoking?",
      "Based on your intellectual taste"
    ],
    documentary: [
      "Great time to learn something new",
      "Your curiosity deserves this",
      "Expand your knowledge today"
    ],
    surprise: [
      "Let's discover something new together",
      "Feeling adventurous?",
      "Time to break the routine"
    ]
  };
  
  const moodReasons = reasons[mood.id] || reasons.surprise;
  return moodReasons[Math.floor(Math.random() * moodReasons.length)];
}

export function ConversationalInterface() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMood, setProcessingMood] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedMoodIndex, setSelectedMoodIndex] = useState(0);
  const [showAISuggestion, setShowAISuggestion] = useState(true);
  const sliderRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  
  // Drag handling for slider
  const x = useMotionValue(0);
  const sliderWidth = useTransform(x, [-300, 300], [0, 100]);
  
  const { 
    userProfile, 
    setIsLoading, 
    setShowReel, 
    setRecommendations,
    setCurrentQuery 
  } = useAppStore();
  
  const { startSession, recordRecommendationsShown } = useAnalytics();
  
  // AI-detected mood
  const aiMood = useAIMoodDetection();
  
  // Set initial mood based on AI detection - only once on mount
  const hasInitialized = useRef(false);
  useEffect(() => {
    if (!hasInitialized.current) {
      const aiMoodIndex = MOOD_CATEGORIES.findIndex(m => m.id === aiMood.primaryMood.id);
      if (aiMoodIndex !== -1) {
        setSelectedMoodIndex(aiMoodIndex);
      }
      hasInitialized.current = true;
    }
  }, [aiMood]);

  // Initialize speech recognition
  useEffect(() => {
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setSearchQuery(transcript);
        setIsListening(false);
        handleSubmit(transcript);
      };

      recognitionRef.current.onerror = () => setIsListening(false);
      recognitionRef.current.onend = () => setIsListening(false);
    }
  }, []);

  const handleVoiceInput = () => {
    if (!SpeechRecognition) {
      alert('Voice input is not supported in this browser.');
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      setShowSearch(true);
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleSubmit = useCallback(async (query: string) => {
    if (!query.trim() || isProcessing) return;

    startSession();
    setIsProcessing(true);
    setIsLoading(true);
    setCurrentQuery(query);
    setErrorMessage(null);

    try {
      const response = await apiClient.generateRecommendations({
        query: query,
        user_profile: transformUserProfileToBackend(userProfile),
        constraints: { max_results: 5 }
      });

      const recommendations = transformRecommendations(response.recommendations);
      
      if (recommendations.length === 0) {
        setErrorMessage("No matches found. Try another mood!");
        return;
      }

      recordRecommendationsShown(recommendations.length);
      setRecommendations(recommendations);
      setShowReel(true);
      setShowSearch(false);
      setSearchQuery('');
      
    } catch (error) {
      console.error('Error:', error);
      setErrorMessage("Connection failed. Is the backend running?");
    } finally {
      setIsProcessing(false);
      setIsLoading(false);
      setProcessingMood(null);
    }
  }, [isProcessing, userProfile, setIsLoading, setShowReel, setRecommendations, setCurrentQuery, startSession, recordRecommendationsShown]);

  const handleMoodClick = useCallback((mood: typeof MOOD_CATEGORIES[0], index: number) => {
    if (isProcessing) return;
    setSelectedMoodIndex(index);
    setProcessingMood(mood.id);
    handleSubmit(mood.query);
  }, [handleSubmit, isProcessing]);

  const handleGenreClick = useCallback((genre: typeof QUICK_GENRES[0]) => {
    if (isProcessing) return;
    handleSubmit(genre.query);
  }, [handleSubmit, isProcessing]);

  // Slider navigation
  const slideMood = (direction: 'left' | 'right') => {
    if (direction === 'left') {
      setSelectedMoodIndex(prev => (prev > 0 ? prev - 1 : MOOD_CATEGORIES.length - 1));
    } else {
      setSelectedMoodIndex(prev => (prev < MOOD_CATEGORIES.length - 1 ? prev + 1 : 0));
    }
  };

  const handleDragEnd = (_: any, info: PanInfo) => {
    if (info.offset.x > 50) {
      slideMood('left');
    } else if (info.offset.x < -50) {
      slideMood('right');
    }
  };

  const selectedMood = MOOD_CATEGORIES[selectedMoodIndex];
  const Icon = selectedMood.icon;

  return (
    <div className="w-full max-w-5xl mx-auto px-4">
      {/* AI Suggestion Banner */}
      <AnimatePresence>
        {showAISuggestion && (
          <motion.div
            className="mb-6"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-500/10 via-coral-500/10 to-purple-500/10 border border-white/10 p-4">
              <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 to-purple-500/5 animate-pulse" />
              
              <div className="relative flex items-center gap-4">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-400 to-coral-500 flex items-center justify-center">
                    <Wand2 className="w-6 h-6 text-midnight-950" />
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-amber-400 uppercase tracking-wider">AI Detected</span>
                    <span className="text-xs text-white/40">•</span>
                    <span className="text-xs text-white/40">{Math.round(aiMood.confidence * 100)}% confident</span>
                  </div>
                  <p className="text-white font-medium truncate">
                    {aiMood.reason}
                  </p>
                </div>
                
                <motion.button
                  onClick={() => handleMoodClick(aiMood.primaryMood, MOOD_CATEGORIES.findIndex(m => m.id === aiMood.primaryMood.id))}
                  disabled={isProcessing}
                  className={`flex-shrink-0 px-5 py-2.5 rounded-xl font-medium transition-all ${aiMood.primaryMood.bgGradient} text-white shadow-lg`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isProcessing && processingMood === aiMood.primaryMood.id ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <span className="flex items-center gap-2">
                      <span>{aiMood.primaryMood.emoji}</span>
                      <span>{aiMood.primaryMood.label}</span>
                    </span>
                  )}
                </motion.button>
                
                <button
                  onClick={() => setShowAISuggestion(false)}
                  className="text-white/30 hover:text-white/60 transition-colors p-1"
                >
                  ✕
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Header */}
      <motion.div
        className="text-center mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="font-display text-4xl md:text-5xl font-bold text-white mb-2 tracking-tight">
          What's your vibe?
        </h1>
        <p className="text-white/50">
          Slide to explore moods or tap to watch instantly
        </p>
      </motion.div>

      {/* Mood Slider - Swipeable */}
      <motion.div 
        className="relative mb-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        {/* Navigation Arrows */}
        <button
          onClick={() => slideMood('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-12 h-12 flex items-center justify-center rounded-full bg-midnight-900/80 backdrop-blur-sm border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-all"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
        
        <button
          onClick={() => slideMood('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-12 h-12 flex items-center justify-center rounded-full bg-midnight-900/80 backdrop-blur-sm border border-white/10 text-white/60 hover:text-white hover:border-white/20 transition-all"
        >
          <ChevronRight className="w-6 h-6" />
        </button>

        {/* Slider Container */}
        <div className="overflow-hidden px-16" ref={sliderRef}>
          <motion.div
            className="flex justify-center"
            drag="x"
            dragConstraints={{ left: -100, right: 100 }}
            onDragEnd={handleDragEnd}
            style={{ x }}
          >
            {/* Main Selected Mood Card */}
            <motion.button
              onClick={() => handleMoodClick(selectedMood, selectedMoodIndex)}
              disabled={isProcessing}
              className="relative w-full max-w-md aspect-[2/1] rounded-3xl overflow-hidden"
              whileHover={!isProcessing ? { scale: 1.02 } : {}}
              whileTap={!isProcessing ? { scale: 0.98 } : {}}
              layoutId="mood-card"
            >
              {/* Background */}
              <div className={`absolute inset-0 bg-gradient-to-br ${selectedMood.gradient}`} />
              
              {/* Animated Pattern */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.2),transparent_50%)]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(255,255,255,0.15),transparent_50%)]" />
              </div>
              
              {/* Content */}
              <div className="relative h-full flex flex-col items-center justify-center p-6 text-white">
                <motion.div
                  className="mb-4 p-4 rounded-2xl bg-white/20 backdrop-blur-sm"
                  animate={{ 
                    rotate: isProcessing && processingMood === selectedMood.id ? 360 : 0 
                  }}
                  transition={{ duration: 1, repeat: isProcessing ? Infinity : 0, ease: "linear" }}
                >
                  {isProcessing && processingMood === selectedMood.id ? (
                    <Loader2 className="w-10 h-10 animate-spin" />
                  ) : (
                    <Icon className="w-10 h-10" />
                  )}
                </motion.div>
                
                <h2 className="text-3xl font-bold mb-2">{selectedMood.label}</h2>
                <p className="text-white/80 text-center">
                  {selectedMood.keywords.join(' • ')}
                </p>
                
                {!isProcessing && (
                  <motion.div
                    className="mt-4 px-6 py-2 rounded-full bg-white/20 backdrop-blur-sm text-sm font-medium"
                    animate={{ opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    Tap to discover →
                  </motion.div>
                )}
              </div>
            </motion.button>
          </motion.div>
        </div>

        {/* Mood Indicator Dots / Mini Slider */}
        <div className="flex justify-center gap-2 mt-6">
          {MOOD_CATEGORIES.map((mood, index) => (
            <button
              key={mood.id}
              onClick={() => setSelectedMoodIndex(index)}
              className={`group relative transition-all duration-300 ${
                index === selectedMoodIndex 
                  ? 'w-8 h-3' 
                  : 'w-3 h-3 hover:scale-125'
              }`}
            >
              <div className={`absolute inset-0 rounded-full transition-all ${
                index === selectedMoodIndex
                  ? `bg-gradient-to-r ${mood.gradient}`
                  : 'bg-white/20 group-hover:bg-white/40'
              }`} />
              
              {/* Tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="px-2 py-1 rounded bg-midnight-900 border border-white/10 text-xs text-white whitespace-nowrap">
                  {mood.emoji} {mood.label}
                </div>
              </div>
            </button>
          ))}
        </div>
      </motion.div>

      {/* All Moods Grid - Smaller Cards */}
      <motion.div
        className="mb-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Compass className="w-4 h-4 text-white/40" />
          <span className="text-sm text-white/40 font-medium">All moods</span>
        </div>
        
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
          {MOOD_CATEGORIES.map((mood, index) => {
            const MoodIcon = mood.icon;
            const isSelected = index === selectedMoodIndex;
            
            return (
              <motion.button
                key={mood.id}
                onClick={() => handleMoodClick(mood, index)}
                disabled={isProcessing}
                className={`relative p-3 rounded-xl transition-all ${
                  isSelected 
                    ? `${mood.bgGradient} shadow-lg` 
                    : 'bg-white/5 hover:bg-white/10 border border-white/10'
                } ${isProcessing && !isSelected ? 'opacity-50' : ''}`}
                whileHover={!isProcessing ? { scale: 1.05, y: -2 } : {}}
                whileTap={!isProcessing ? { scale: 0.95 } : {}}
              >
                <div className="flex flex-col items-center gap-1">
                  {processingMood === mood.id ? (
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  ) : (
                    <MoodIcon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-white/60'}`} />
                  )}
                  <span className={`text-xs font-medium ${isSelected ? 'text-white' : 'text-white/60'}`}>
                    {mood.label}
                  </span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Quick Genre Pills */}
      <motion.div
        className="mb-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-white/40" />
          <span className="text-sm text-white/40 font-medium">Quick picks</span>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {QUICK_GENRES.map((genre, index) => {
            const GenreIcon = genre.icon;
            return (
              <motion.button
                key={genre.label}
                onClick={() => handleGenreClick(genre)}
                disabled={isProcessing}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all text-sm
                  ${isProcessing 
                    ? 'bg-white/5 border-white/10 text-white/30 cursor-not-allowed' 
                    : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:border-white/20 hover:text-white'
                  }`}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 + index * 0.03 }}
                whileHover={!isProcessing ? { scale: 1.05 } : {}}
                whileTap={!isProcessing ? { scale: 0.95 } : {}}
              >
                <GenreIcon className="w-3.5 h-3.5" />
                <span>{genre.label}</span>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Search Toggle */}
      <motion.div
        className="flex justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <AnimatePresence mode="wait">
          {!showSearch ? (
            <motion.button
              key="search-toggle"
              onClick={() => setShowSearch(true)}
              className="flex items-center gap-2 px-4 py-2 text-white/40 hover:text-white/60 transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              <Search className="w-4 h-4" />
              <span className="text-sm">Search for something specific...</span>
            </motion.button>
          ) : (
            <motion.div
              key="search-input"
              className="w-full max-w-xl"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-amber-500/20 to-coral-500/20 rounded-xl blur-lg" />
                <div className="relative bg-midnight-900/90 backdrop-blur-xl rounded-xl border border-white/10 overflow-hidden">
                  <input
                    ref={inputRef}
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmit(searchQuery)}
                    placeholder={isListening ? "🎤 Listening..." : "Describe what you want to watch..."}
                    disabled={isProcessing}
                    autoFocus
                    className="w-full px-4 py-3 pr-24 bg-transparent text-white placeholder:text-white/40 focus:outline-none"
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    <motion.button
                      onClick={handleVoiceInput}
                      className={`p-2 rounded-lg ${isListening ? 'bg-red-500 text-white' : 'text-white/40 hover:text-white/70'}`}
                      whileTap={{ scale: 0.95 }}
                    >
                      <Mic className={`w-4 h-4 ${isListening ? 'animate-pulse' : ''}`} />
                    </motion.button>
                    <motion.button
                      onClick={() => handleSubmit(searchQuery)}
                      disabled={!searchQuery.trim() || isProcessing}
                      className={`p-2 rounded-lg ${searchQuery.trim() ? 'bg-amber-500 text-midnight-950' : 'bg-white/10 text-white/30'}`}
                      whileTap={{ scale: 0.95 }}
                    >
                      {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    </motion.button>
                  </div>
                </div>
              </div>
              <button
                onClick={() => { setShowSearch(false); setSearchQuery(''); }}
                className="w-full mt-2 text-center text-sm text-white/30 hover:text-white/50"
              >
                Cancel
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Error Toast */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
          >
            <div className="px-6 py-3 bg-red-500/90 backdrop-blur-xl rounded-xl text-white font-medium shadow-lg">
              {errorMessage}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Processing Overlay */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-midnight-950/90 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="flex flex-col items-center gap-6"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
            >
              <div className="relative w-28 h-28">
                <motion.div
                  className={`absolute inset-0 rounded-full bg-gradient-to-br ${selectedMood.gradient}`}
                  animate={{ scale: [1, 1.1, 1], rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Icon className="w-12 h-12 text-white" />
                </div>
              </div>
              
              <div className="text-center">
                <p className="text-2xl text-white font-display font-bold mb-2">
                  Finding {selectedMood.label.toLowerCase()} picks...
                </p>
                <p className="text-white/50">Curating personalized recommendations</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
