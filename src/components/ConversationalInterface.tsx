import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Send, Mic, Loader2, Wand2, Brain, Zap, Heart, Ghost, Film } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { apiClient, transformRecommendations, transformUserProfileToBackend } from '../api/client';
import { useAnalytics } from '../hooks/useAnalytics';

const QUICK_PROMPTS = [
  { icon: Sparkles, text: "What should I watch?", color: "amber" },
  { icon: Zap, text: "Something exciting", color: "coral" },
  { icon: Heart, text: "I want to relax", color: "teal" },
  { icon: Ghost, text: "Surprise me", color: "purple" },
  { icon: Brain, text: "Something thought-provoking", color: "blue" },
  { icon: Film, text: "A great documentary", color: "green" },
];

// Speech Recognition setup
const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

export function ConversationalInterface() {
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [responseMessage, setResponseMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  
  const { 
    userProfile, 
    setIsLoading, 
    setShowReel, 
    setRecommendations,
    setCurrentQuery 
  } = useAppStore();
  
  const { startSession, recordRecommendationsShown } = useAnalytics();

  // Initialize speech recognition
  useEffect(() => {
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        console.log('Voice input:', transcript);
        setQuery(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  // Handle voice input button click
  const handleVoiceInput = () => {
    if (!SpeechRecognition) {
      alert('Voice input is not supported in this browser. Try Chrome.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleSubmit = useCallback(async (submittedQuery: string) => {
    console.log('handleSubmit called with:', submittedQuery, 'isProcessing:', isProcessing);
    if (!submittedQuery.trim() || isProcessing) return;
    console.log('Starting to process query...');

    // Start analytics session
    startSession();

    setIsProcessing(true);
    setIsLoading(true);
    setCurrentQuery(submittedQuery);
    setErrorMessage(null);
    setResponseMessage(null);

    try {
      // Call the backend API
      const response = await apiClient.generateRecommendations({
        query: submittedQuery,
        user_profile: transformUserProfileToBackend(userProfile),
        constraints: {
          max_results: 5,
        }
      });

      // Transform backend response to frontend format
      const recommendations = transformRecommendations(response.recommendations);
      
      if (recommendations.length === 0) {
        setResponseMessage("I couldn't find any matching recommendations. Try a different query!");
        return;
      }

      console.log('Got recommendations:', recommendations);
      
      // Record that recommendations were shown
      recordRecommendationsShown(recommendations.length);
      
      // Set recommendations and show reel immediately
      setRecommendations(recommendations);
      setShowReel(true);
      console.log('Reel should be visible now');
      
    } catch (error) {
      console.error('Error generating recommendations:', error);
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      setErrorMessage(`Failed to connect to the recommendation engine: ${errorMsg}`);
      setResponseMessage(null);
    } finally {
      setIsProcessing(false);
      setIsLoading(false);
      setQuery('');
    }
  }, [isProcessing, userProfile, setIsLoading, setShowReel, setRecommendations, setCurrentQuery, startSession, recordRecommendationsShown]);

  const handleQuickPrompt = useCallback((prompt: string) => {
    console.log('Quick prompt clicked:', prompt);
    setQuery(prompt);
    handleSubmit(prompt);
  }, [handleSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(query);
    }
  }, [handleSubmit, query]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Header */}
      <motion.div
        className="text-center mb-12"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <motion.div
          className="inline-flex items-center justify-center w-20 h-20 mb-6 rounded-2xl bg-gradient-to-br from-amber-400 to-coral-500 shadow-lg shadow-amber-500/25"
          animate={{ 
            boxShadow: [
              '0 10px 40px rgba(251, 191, 36, 0.25)',
              '0 10px 60px rgba(251, 191, 36, 0.4)',
              '0 10px 40px rgba(251, 191, 36, 0.25)',
            ]
          }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <Wand2 className="w-10 h-10 text-midnight-950" />
        </motion.div>
        
        <h1 className="font-display text-5xl md:text-6xl font-bold text-white mb-4 tracking-tight">
          What are you in the mood for?
        </h1>
        <p className="text-xl text-white/60 max-w-xl mx-auto">
          Tell me what you want to watch, and I'll curate the perfect selection just for you.
        </p>
      </motion.div>

      {/* Input Area */}
      <motion.div
        className="relative mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <div className="relative group">
          {/* Glow Effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 via-coral-500 to-teal-500 rounded-2xl blur-lg opacity-30 group-hover:opacity-50 group-focus-within:opacity-60 transition-opacity" />
          
          {/* Input Container */}
          <div className="relative bg-midnight-900/90 backdrop-blur-xl rounded-2xl border border-white/10 group-hover:border-white/20 group-focus-within:border-amber-400/50 transition-colors overflow-hidden">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isListening ? "Listening..." : "Ask me anything..."}
              disabled={isProcessing}
              className="w-full px-6 py-5 pr-32 bg-transparent text-white text-lg placeholder:text-white/40 focus:outline-none disabled:opacity-50"
            />
            
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
              {/* Voice Input Button */}
              <motion.button
                type="button"
                onClick={handleVoiceInput}
                className={`p-2.5 rounded-xl transition-colors ${
                  isListening 
                    ? 'bg-red-500 text-white' 
                    : 'text-white/40 hover:text-white/70 hover:bg-white/10'
                }`}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                disabled={isProcessing}
              >
                <Mic className={`w-5 h-5 ${isListening ? 'animate-pulse' : ''}`} />
              </motion.button>
              
              {/* Submit Button */}
              <motion.button
                className={`p-3 rounded-xl transition-all ${
                  query.trim() && !isProcessing
                    ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-midnight-950 shadow-lg shadow-amber-500/25'
                    : 'bg-white/10 text-white/30'
                }`}
                onClick={() => handleSubmit(query)}
                disabled={!query.trim() || isProcessing}
                whileHover={query.trim() && !isProcessing ? { scale: 1.05 } : {}}
                whileTap={query.trim() && !isProcessing ? { scale: 0.95 } : {}}
              >
                {isProcessing ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </motion.button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Listening indicator */}
      <AnimatePresence>
        {isListening && (
          <motion.div
            className="text-center mb-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <p className="text-amber-400 animate-pulse">🎤 Listening... Speak now!</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Response Message */}
      <AnimatePresence>
        {responseMessage && (
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <p className="text-lg text-amber-400/90 font-medium">{responseMessage}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Message */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            className="text-center mb-8"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <p className="text-lg text-red-400/90 font-medium">{errorMessage}</p>
            <p className="text-sm text-white/50 mt-2">Make sure the backend is running on port 8888</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quick Prompts */}
      <motion.div
        className="flex flex-wrap justify-center gap-3"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        {QUICK_PROMPTS.map((prompt, index) => {
          const Icon = prompt.icon;
          return (
            <motion.button
              key={prompt.text}
              className={`group flex items-center gap-2 px-4 py-2.5 rounded-full border transition-all
                ${isProcessing 
                  ? 'bg-white/5 border-white/10 text-white/30 cursor-not-allowed' 
                  : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10 hover:border-white/20 hover:text-white'
                }`}
              onClick={() => !isProcessing && handleQuickPrompt(prompt.text)}
              disabled={isProcessing}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              whileHover={!isProcessing ? { scale: 1.05, y: -2 } : {}}
              whileTap={!isProcessing ? { scale: 0.95 } : {}}
            >
              <Icon className={`w-4 h-4 transition-colors ${
                !isProcessing ? `group-hover:text-${prompt.color}-400` : ''
              }`} />
              <span className="text-sm font-medium">{prompt.text}</span>
            </motion.button>
          );
        })}
      </motion.div>

      {/* Processing State */}
      <AnimatePresence>
        {isProcessing && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center bg-midnight-950/80 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="flex flex-col items-center gap-6"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
            >
              {/* AI Processing Animation */}
              <div className="relative">
                <motion.div
                  className="w-24 h-24 rounded-full bg-gradient-to-br from-amber-400 to-coral-500"
                  animate={{ 
                    scale: [1, 1.2, 1],
                    rotate: [0, 180, 360],
                  }}
                  transition={{ 
                    duration: 2, 
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                />
                <motion.div
                  className="absolute inset-0 flex items-center justify-center"
                  animate={{ rotate: [0, -360] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                >
                  <Brain className="w-10 h-10 text-midnight-950" />
                </motion.div>
              </div>
              
              <div className="text-center">
                <motion.p
                  className="text-xl text-white font-medium mb-2"
                  animate={{ opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  Analyzing your preferences...
                </motion.p>
                <p className="text-white/50 text-sm">
                  Finding the perfect recommendations
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
