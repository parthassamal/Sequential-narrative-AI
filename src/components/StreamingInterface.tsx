import { useState, useCallback, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, Sparkles, Search, User, ChevronRight, 
  Volume2, VolumeX, Clock, Star, Loader2, X,
  Brain, Zap, BarChart3, HelpCircle,
  LogIn, LogOut, ChevronDown, Settings
} from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { apiClient, getErrorMessage, transformRecommendations, transformUserProfileToBackend } from '../api/client';
import { useAnalytics } from '../hooks/useAnalytics';
import { useUserPersistence } from '../hooks/useUserPersistence';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { HelpGuide } from './HelpGuide';
import { AuthModal } from './AuthModal';

// Mock trending content for the streaming UI with YouTube trailer IDs
const TRENDING_CONTENT = [
  {
    id: '1',
    title: 'Top Gun: Maverick',
    image: 'https://image.tmdb.org/t/p/w500/62HCnUTziyWcpDaBO2i1DX17ljH.jpg',
    year: 2022,
    rating: 8.3,
    trailerId: 'giXco2jaZ_4', // Official Top Gun: Maverick trailer
  },
  {
    id: '2', 
    title: 'Yellowstone',
    image: 'https://image.tmdb.org/t/p/w500/peNC0eyc3TQJa6x4TdKcBPNP4t0.jpg',
    year: 2018,
    rating: 8.7,
    trailerId: 'HxBdYHzKDGg', // Yellowstone Season 1 trailer
  },
  {
    id: '3',
    title: 'Mission: Impossible - Dead Reckoning',
    image: 'https://image.tmdb.org/t/p/w500/NNxYkU70HPurnNCSiCjYAmacwm.jpg',
    year: 2023,
    rating: 7.8,
    trailerId: 'avz06PDqDbM', // Mission Impossible Dead Reckoning trailer
  },
  {
    id: '4',
    title: 'Star Trek: Strange New Worlds',
    image: 'https://image.tmdb.org/t/p/w500/wiBq2p6l5G3oCOvFWBN3rX381py.jpg',
    year: 2022,
    rating: 8.4,
    trailerId: 'vNwf6VMmLhU', // Star Trek SNW trailer
  },
  {
    id: '5',
    title: 'The Martian',
    image: 'https://image.tmdb.org/t/p/w500/5BHuvQ6p9kfc091Z8RiFNhCwL4b.jpg',
    year: 2015,
    rating: 8.0,
    trailerId: 'ej3ioOneTy8', // The Martian official trailer
  },
  {
    id: '6',
    title: '1883',
    image: 'https://image.tmdb.org/t/p/w500/waVmlq9fCJGbL5hmcjCNCfpYI9Q.jpg',
    year: 2021,
    rating: 8.6,
    trailerId: 'IYVlhQXVjU4', // 1883 official trailer
  },
];

// Hero content for background
const HERO_CONTENT = {
  title: 'Top Gun: Maverick',
  tagline: 'Feel the need for speed. Tom Cruise returns as Maverick in the most thrilling aviation movie ever filmed.',
  image: 'https://image.tmdb.org/t/p/original/AaV1YIdWKhxX5pM52MWNRHH5jOm.jpg',
  logo: null,
};

// AI-powered mood detection
function useAIMoodPrediction() {
  const { userProfile } = useAppStore();
  
  return useMemo(() => {
    const timeOfDay = userProfile.contextualSignals.timeOfDay;
    const stressLevel = userProfile.decisionState.stressLevel;
    const genres = userProfile.preferences.favoriteGenres;
    
    // Multi-signal mood inference
    let suggestedQuery = "Something exciting";
    let confidence = 0.7;
    let reason = "Based on your viewing patterns";
    
    if (timeOfDay === 'night' && stressLevel < 0.4) {
      suggestedQuery = "Something thrilling for late night";
      reason = "Perfect for a late-night thriller";
      confidence = 0.85;
    } else if (timeOfDay === 'morning') {
      suggestedQuery = "Something uplifting to start the day";
      reason = "Start your day with something great";
      confidence = 0.75;
    } else if (genres.includes('Documentary')) {
      suggestedQuery = "An engaging documentary";
      reason = "Based on your love for documentaries";
      confidence = 0.82;
    } else if (stressLevel > 0.6) {
      suggestedQuery = "Something relaxing and calming";
      reason = "You seem like you need to unwind";
      confidence = 0.78;
    }
    
    return { suggestedQuery, confidence, reason };
  }, [userProfile]);
}

export function StreamingInterface() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAITooltip, setShowAITooltip] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [trailerItem, setTrailerItem] = useState<typeof TRENDING_CONTENT[0] | null>(null);
  
  const { 
    userProfile, 
    setIsLoading, 
    setShowReel, 
    setRecommendations,
    setCurrentQuery 
  } = useAppStore();
  
  const { startSession, recordRecommendationsShown } = useAnalytics();
  const { user, saveUser, clearUser } = useUserPersistence();
  const aiPrediction = useAIMoodPrediction();

  useEffect(() => {
    if (!errorMessage) return;
    const timer = setTimeout(() => setErrorMessage(null), 5000);
    return () => clearTimeout(timer);
  }, [errorMessage]);

  const handleLogin = (userData: { name: string; email: string }) => {
    saveUser(userData);
    setShowAuthModal(false);
  };

  const handleLogout = () => {
    clearUser();
    setShowUserMenu(false);
  };

  // One-click personalized recommendation trigger
  const handleWhatToWatch = useCallback(async (customQuery?: string) => {
    if (isProcessing) return;
    
    const query = customQuery || aiPrediction.suggestedQuery;
    
    startSession();
    setIsProcessing(true);
    setIsLoading(true);
    setCurrentQuery(query);
    setErrorMessage(null);

    try {
      // DPP-based diversity optimization with cognitive load adaptation
      const response = await apiClient.generateRecommendations({
        query: query,
        user_profile: transformUserProfileToBackend(userProfile),
        constraints: { 
          max_results: 5,
          // Adaptive set size based on decision state
          cognitive_load_factor: userProfile.decisionState.stressLevel
        }
      });

      const recommendations = transformRecommendations(response.recommendations);
      
      if (recommendations.length > 0) {
        recordRecommendationsShown(recommendations.length);
        setRecommendations(recommendations);
        setShowReel(true);
      } else {
        setErrorMessage('No recommendations found for that request. Try a different mood or search.');
      }
    } catch (error) {
      console.error('Recommendation error:', error);
      setErrorMessage(getErrorMessage(error, 'Unable to fetch recommendations right now. Please try again.'));
    } finally {
      setIsProcessing(false);
      setIsLoading(false);
    }
  }, [isProcessing, userProfile, aiPrediction, setIsLoading, setShowReel, setRecommendations, setCurrentQuery, startSession, recordRecommendationsShown]);

  // Handle category navigation
  const handleCategoryClick = useCallback((category: string) => {
    setActiveCategory(category);
    const queryMap: Record<string, string> = {
      'Home': 'something popular right now',
      'Movies': 'best movies to watch',
      'Shows': 'great TV shows to binge',
      'Sports': 'sports documentaries and highlights',
      'Live TV': 'live events and breaking news'
    };
    handleWhatToWatch(queryMap[category] || 'something great');
  }, [handleWhatToWatch]);

  // Handle trending item click - opens trailer player
  const handleTrendingClick = useCallback((item: typeof TRENDING_CONTENT[0]) => {
    setTrailerItem(item);
  }, []);

  // Close trailer and stop video
  const closeTrailer = useCallback(() => {
    // Stop the YouTube video by posting a message to the iframe
    const iframe = document.getElementById('trailer-iframe') as HTMLIFrameElement;
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.postMessage('{"event":"command","func":"stopVideo","args":""}', '*');
    }
    setTrailerItem(null);
  }, []);

  // Handle Play Demo - opens Figma presentation
  const handlePlayDemo = useCallback(() => {
    window.open('https://kindle-upload-01134552.figma.site/', '_blank');
  }, []);

  // Auto-show AI tooltip after delay
  useEffect(() => {
    const timer = setTimeout(() => setShowAITooltip(true), 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-hidden">
      {/* Navigation Bar - Paramount+ Style */}
      <nav className="fixed top-0 left-0 right-0 z-40 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center justify-between px-8 py-4">
          {/* Logo */}
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center">
                <span className="text-white font-bold text-sm">P+</span>
              </div>
              <span className="text-xl font-bold text-white">Paramount+</span>
            </div>
            
            <div className="hidden md:flex items-center gap-6 text-sm font-medium text-white/70">
              {['Home', 'Movies', 'Shows', 'Sports', 'Live TV'].map((category) => (
                <button
                  key={category}
                  onClick={() => handleCategoryClick(category)}
                  className={`hover:text-white transition-colors ${activeCategory === category ? 'text-white border-b-2 border-blue-500 pb-1' : ''}`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
          
          {/* Right side */}
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setShowSearch(!showSearch)}
              className="p-2 text-white/70 hover:text-white transition-colors"
              title="Search"
            >
              <Search className="w-5 h-5" />
            </button>
            <button 
              onClick={() => setShowHelp(true)}
              className="p-2 text-white/70 hover:text-white transition-colors"
              title="Help & Guide"
            >
              <HelpCircle className="w-5 h-5" />
            </button>
            <button 
              onClick={() => setShowAnalytics(true)}
              className="p-2 text-white/70 hover:text-white transition-colors"
              title="Analytics Dashboard"
            >
              <BarChart3 className="w-5 h-5" />
            </button>
            
            {user ? (
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-3 py-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                >
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
                    <User className="w-3.5 h-3.5 text-white" />
                  </div>
                  <span className="text-sm font-medium hidden sm:block">{user.name}</span>
                  <ChevronDown className="w-4 h-4 text-white/50" />
                </button>

                <AnimatePresence>
                  {showUserMenu && (
                    <motion.div
                      className="absolute right-0 top-full mt-2 w-56 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-xl overflow-hidden z-50"
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                    >
                      <div className="px-4 py-3 border-b border-white/10">
                        <p className="text-white font-medium text-sm">{user.name}</p>
                        <p className="text-white/50 text-xs">{user.email}</p>
                      </div>
                      
                      <div className="py-1">
                        <button
                          onClick={() => { setShowHelp(true); setShowUserMenu(false); }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5"
                        >
                          <HelpCircle className="w-4 h-4" />
                          <span className="text-sm">Help & Guide</span>
                        </button>
                        <button
                          onClick={() => { setShowAnalytics(true); setShowUserMenu(false); }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5"
                        >
                          <BarChart3 className="w-4 h-4" />
                          <span className="text-sm">Analytics</span>
                        </button>
                        <button 
                          onClick={() => { setShowSettings(true); setShowUserMenu(false); }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5"
                        >
                          <Settings className="w-4 h-4" />
                          <span className="text-sm">Preferences</span>
                        </button>
                      </div>
                      
                      <div className="border-t border-white/10 py-1">
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-red-400 hover:bg-white/5"
                        >
                          <LogOut className="w-4 h-4" />
                          <span className="text-sm">Sign Out</span>
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-400 hover:to-blue-500 transition-colors font-medium"
              >
                <LogIn className="w-4 h-4" />
                <span className="text-sm">Sign In</span>
              </button>
            )}
          </div>
        </div>
        
        {/* Search Bar */}
        <AnimatePresence>
          {showSearch && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="px-8 pb-4"
            >
              <div className="max-w-xl mx-auto relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleWhatToWatch(searchQuery)}
                  placeholder="Search movies, shows, or describe what you want..."
                  className="w-full px-4 py-3 bg-white/10 backdrop-blur-xl rounded-lg border border-white/20 text-white placeholder:text-white/50 focus:outline-none focus:border-blue-500"
                  autoFocus
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Hero Section */}
      <div className="relative h-[85vh] overflow-hidden">
        {/* Background Image */}
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ 
            backgroundImage: `url(${HERO_CONTENT.image})`,
          }}
        >
          {/* Gradient Overlays */}
          <div className="absolute inset-0 bg-gradient-to-r from-[#0a0a0f] via-[#0a0a0f]/60 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0f] via-transparent to-transparent" />
        </div>

        {/* Hero Content */}
        <div className="relative z-10 h-full flex flex-col justify-center px-8 md:px-16 max-w-3xl">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold mb-4 leading-tight">
              {HERO_CONTENT.title}
            </h1>
            
            <p className="text-lg text-white/80 mb-8 max-w-xl">
              {HERO_CONTENT.tagline}
            </p>

            {/* AI Suggestion Tooltip */}
            <AnimatePresence>
              {showAITooltip && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-4"
                >
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gradient-to-r from-amber-500/20 to-purple-500/20 border border-amber-500/30">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span className="text-sm text-amber-200">Try the Demo</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center gap-4">
              {/* PRIMARY: What Should I Watch? */}
              <motion.button
                onClick={() => handleWhatToWatch()}
                disabled={isProcessing}
                className="group relative flex items-center gap-3 px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-lg font-semibold text-lg transition-all shadow-lg shadow-blue-600/30"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isProcessing ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : (
                  <Sparkles className="w-6 h-6" />
                )}
                <span>WHAT SHOULD I WATCH?</span>
                
                {/* AI Confidence Badge */}
                <div className="absolute -top-2 -right-2 px-2 py-0.5 rounded-full bg-green-500 text-xs font-bold">
                  AI
                </div>
              </motion.button>

              {/* Play Demo - Opens Figma Presentation */}
              <motion.button
                onClick={handlePlayDemo}
                disabled={isProcessing}
                className="flex items-center gap-3 px-6 py-4 bg-purple-600/80 hover:bg-purple-500 rounded-lg font-semibold transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Play className="w-5 h-5" />
                <span>PLAY DEMO</span>
              </motion.button>
            </div>

            {/* Mood-Based Quick Actions */}
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button
                onClick={() => handleWhatToWatch('Something exciting and action-packed')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-orange-500/20 to-red-500/20 border border-orange-500/30 text-orange-300 hover:from-orange-500/30 hover:to-red-500/30 transition-all disabled:opacity-50"
                title="Exciting action content"
              >
                <span className="text-lg">⚡</span>
                <span>Exciting</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Something relaxing and calming')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-teal-500/20 to-cyan-500/20 border border-teal-500/30 text-teal-300 hover:from-teal-500/30 hover:to-cyan-500/30 transition-all disabled:opacity-50"
                title="Relaxing content"
              >
                <span className="text-lg">☕</span>
                <span>Relaxing</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Something funny to make me laugh')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border border-yellow-500/30 text-yellow-300 hover:from-yellow-500/30 hover:to-amber-500/30 transition-all disabled:opacity-50"
                title="Comedy content"
              >
                <span className="text-lg">😂</span>
                <span>Funny</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Something scary and thrilling')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-purple-500/20 to-violet-500/20 border border-purple-500/30 text-purple-300 hover:from-purple-500/30 hover:to-violet-500/30 transition-all disabled:opacity-50"
                title="Horror/Thriller content"
              >
                <span className="text-lg">💀</span>
                <span>Scary</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Something romantic')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-pink-500/20 to-rose-500/20 border border-pink-500/30 text-pink-300 hover:from-pink-500/30 hover:to-rose-500/30 transition-all disabled:opacity-50"
                title="Romance content"
              >
                <span className="text-lg">💕</span>
                <span>Romantic</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Something thought-provoking and mind-blowing')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-300 hover:from-indigo-500/30 hover:to-purple-500/30 transition-all disabled:opacity-50"
                title="Mind-blowing content"
              >
                <span className="text-lg">🤯</span>
                <span>Mind-Blowing</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('A great documentary to learn something new')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-emerald-500/20 to-green-500/20 border border-emerald-500/30 text-emerald-300 hover:from-emerald-500/30 hover:to-green-500/30 transition-all disabled:opacity-50"
                title="Documentary content"
              >
                <span className="text-lg">📚</span>
                <span>Learn</span>
              </button>
              <button
                onClick={() => handleWhatToWatch('Surprise me with something unexpected')}
                disabled={isProcessing}
                className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-gradient-to-r from-fuchsia-500/20 to-pink-500/20 border border-fuchsia-500/30 text-fuchsia-300 hover:from-fuchsia-500/30 hover:to-pink-500/30 transition-all disabled:opacity-50"
                title="Surprise me!"
              >
                <span className="text-lg">🎲</span>
                <span>Surprise</span>
              </button>
            </div>
          </motion.div>
        </div>

        {/* Mute Button */}
        <button
          onClick={() => setIsMuted(!isMuted)}
          className="absolute bottom-32 right-8 p-3 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-colors"
        >
          {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>
      </div>

      {/* Trending Section */}
      <div className="relative z-20 -mt-20 px-8 md:px-16">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Trending Now</h2>
          <button 
            onClick={() => handleWhatToWatch('trending movies and shows')}
            className="flex items-center gap-1 text-sm text-white/60 hover:text-white transition-colors"
          >
            <span>See All</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Content Row */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {TRENDING_CONTENT.map((item, index) => (
            <motion.button
              key={item.id}
              onClick={() => handleTrendingClick(item)}
              className="group relative aspect-[2/3] rounded-lg overflow-hidden cursor-pointer text-left"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              whileHover={{ scale: 1.05, zIndex: 10 }}
              aria-label={`Play ${item.title} trailer`}
            >
              <img
                src={item.image}
                alt={item.title}
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Use inline SVG data URL as fallback instead of external service
                  const title = item.title.substring(0, 20);
                  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450">
                    <rect fill="#1a1a2e" width="300" height="450"/>
                    <text fill="#ffffff" font-family="Arial" font-size="16" x="150" y="225" text-anchor="middle">${title}</text>
                  </svg>`;
                  (e.target as HTMLImageElement).src = 'data:image/svg+xml,' + encodeURIComponent(svg);
                }}
              />
              
              {/* Hover Overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="absolute bottom-0 left-0 right-0 p-4">
                  <h3 className="font-bold text-sm mb-1">{item.title}</h3>
                  <div className="flex items-center gap-2 text-xs text-white/70">
                    <span>{item.year}</span>
                    <span>•</span>
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
                      <span>{item.rating}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Play Icon on Hover */}
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <Play className="w-6 h-6 text-white fill-white" />
                </div>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Innovative Features Section */}
      <div className="px-8 md:px-16 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-center">Innovative Features</h2>
          
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <Brain className="w-10 h-10 text-purple-400 mb-4" />
              <h3 className="font-bold mb-2">AI Mood Detection</h3>
              <p className="text-sm text-white/60">
                Multi-signal inference from viewing history, time of day, and behavioral patterns to predict user mood.
              </p>
            </div>
            
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <Zap className="w-10 h-10 text-amber-400 mb-4" />
              <h3 className="font-bold mb-2">DPP Diversity Optimization</h3>
              <p className="text-sm text-white/60">
                Determinantal Point Process kernel ensures diverse yet relevant recommendations in each set.
              </p>
            </div>
            
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <Clock className="w-10 h-10 text-green-400 mb-4" />
              <h3 className="font-bold mb-2">Adaptive Cognitive Load</h3>
              <p className="text-sm text-white/60">
                Dynamically adjusts recommendation count (2-5) based on detected user stress and decision state.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Processing Overlay */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="flex flex-col items-center gap-6"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
            >
              <div className="relative w-24 h-24">
                <motion.div
                  className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 to-purple-600"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />
                <div className="absolute inset-2 rounded-full bg-[#0a0a0f] flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-blue-400" />
                </div>
              </div>
              
              <div className="text-center">
                <p className="text-xl font-bold mb-2">Analyzing Your Preferences</p>
                <p className="text-white/50 text-sm">{aiPrediction.reason}</p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Toast */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[70]"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
          >
            <div className="max-w-lg px-4 py-3 bg-red-500/90 border border-red-300/40 rounded-xl text-white text-sm shadow-lg backdrop-blur">
              {errorMessage}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analytics Dashboard Modal */}
      <AnalyticsDashboard
        isOpen={showAnalytics}
        onClose={() => setShowAnalytics(false)}
      />

      {/* Help Guide Modal */}
      <HelpGuide
        isOpen={showHelp}
        onClose={() => setShowHelp(false)}
      />

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onLogin={handleLogin}
      />

      {/* Settings Modal */}
      <AnimatePresence>
        {showSettings && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowSettings(false)}
          >
            <motion.div
              className="relative w-full max-w-md bg-[#1a1a2e] rounded-2xl shadow-2xl border border-white/10 overflow-hidden"
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6 border-b border-white/10">
                <h2 className="text-xl font-bold">Preferences</h2>
                <p className="text-white/50 text-sm mt-1">Customize your experience</p>
              </div>
              
              <div className="p-6 space-y-6">
                {/* Audio Settings */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-blue-400" />
                    Audio Narration
                  </h3>
                  <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                    <span className="text-sm text-white/70">Auto-play narration</span>
                    <button
                      onClick={() => setIsMuted(!isMuted)}
                      className={`w-12 h-6 rounded-full transition-colors ${!isMuted ? 'bg-blue-500' : 'bg-white/20'}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white shadow-md transform transition-transform ${!isMuted ? 'translate-x-6' : 'translate-x-0.5'}`} />
                    </button>
                  </div>
                </div>

                {/* Recommendation Preferences */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    AI Recommendations
                  </h3>
                  <div className="space-y-2">
                    <div className="p-3 bg-white/5 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white/70">Personalized suggestions</span>
                        <div className="w-12 h-6 rounded-full bg-blue-500">
                          <div className="w-5 h-5 rounded-full bg-white shadow-md transform translate-x-6" />
                        </div>
                      </div>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white/70">Show match percentages</span>
                        <div className="w-12 h-6 rounded-full bg-blue-500">
                          <div className="w-5 h-5 rounded-full bg-white shadow-md transform translate-x-6" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Privacy */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Settings className="w-4 h-4 text-green-400" />
                    Privacy
                  </h3>
                  <p className="text-sm text-white/50">
                    Your viewing preferences are stored locally and used only to improve recommendations. 
                    No personal data is sent to external servers.
                  </p>
                </div>
              </div>

              <div className="p-6 border-t border-white/10 flex justify-end gap-3">
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors text-sm font-medium"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Trailer Player Modal */}
      <AnimatePresence>
        {trailerItem && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-md p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeTrailer}
          >
            <motion.div
              className="relative w-full max-w-5xl aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={closeTrailer}
                className="absolute top-4 right-4 z-10 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 flex items-center justify-center transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
              
              {/* YouTube Embed */}
              <iframe
                key={trailerItem.trailerId}
                className="w-full h-full"
                src={`https://www.youtube.com/embed/${trailerItem.trailerId}?autoplay=1&rel=0&modestbranding=1&enablejsapi=1`}
                title={`${trailerItem.title} Trailer`}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                id="trailer-iframe"
              />
              
              {/* Title Overlay */}
              <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/90 to-transparent pointer-events-none">
                <h2 className="text-2xl font-bold">{trailerItem.title}</h2>
                <div className="flex items-center gap-4 mt-2 text-white/70">
                  <span>{trailerItem.year}</span>
                  <div className="flex items-center gap-1">
                    <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                    <span>{trailerItem.rating}</span>
                  </div>
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="absolute bottom-6 right-6 flex items-center gap-3 pointer-events-auto">
                <motion.button
                  onClick={() => {
                    closeTrailer();
                    handleWhatToWatch(`something similar to ${trailerItem.title}`);
                  }}
                  className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 font-medium text-sm flex items-center gap-2 transition-colors"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Sparkles className="w-4 h-4" />
                  Find Similar
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Click outside to close user menu */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </div>
  );
}
