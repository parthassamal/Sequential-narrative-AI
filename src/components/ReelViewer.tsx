import { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, X, Pause, Play, RotateCcw, Volume2, VolumeX, Activity, Clock } from 'lucide-react';
import { ReelCard } from './ReelCard';
import { useAppStore } from '../store/appStore';
import { useTelemetry, useDwellTime, useFocusTracking } from '../hooks/useTelemetry';
import { createPresentationController, PresentationContext } from '../engine/presentationController';
import { useAnalytics } from '../hooks/useAnalytics';

interface ReelViewerProps {
  onClose: () => void;
}

export function ReelViewer({ onClose }: ReelViewerProps) {
  const { 
    reelState, 
    nextRecommendation, 
    previousRecommendation,
    togglePlayback,
    setCurrentIndex,
    addInteraction,
    userProfile,
    updateDecisionState
  } = useAppStore();
  
  const { recommendations, currentIndex, isPlaying, autoAdvance } = reelState;
  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const viewStartTime = useRef<number>(Date.now());
  
  // Analytics tracking
  const { 
    startSession,
    recordCardViewStart, 
    recordCardViewEnd, 
    recordSelection, 
    recordAbandonment,
    recordBacktrack,
    recordRecommendationsShown
  } = useAnalytics();
  
  // Start analytics session when reel opens
  useEffect(() => {
    startSession();
    recordRecommendationsShown(recommendations.length);
  }, []);
  
  // Audio auto-play state - starts ON by default
  const [audioEnabled, setAudioEnabled] = useState(true);
  
  // ========== AI Presentation Controller ==========
  // State machine for adaptive pacing
  const [presentationContext, setPresentationContext] = useState<PresentationContext | null>(null);
  const [adaptedExposureTime, setAdaptedExposureTime] = useState(10); // Default 10 seconds
  const [exposureProgress, setExposureProgress] = useState(0);
  
  // Create presentation controller
  const presentationController = useMemo(() => {
    return createPresentationController(
      {
        baseExposureTime: 10,
        minExposureTime: 3,
        hesitationAlpha: 2,
        confidenceBeta: 3,
        confidenceThreshold: 0.7,
        quickCancelWindow: 30,
      },
      {
        onStateChange: (ctx) => {
          setPresentationContext(ctx);
          setAdaptedExposureTime(ctx.adaptedExposureTarget);
        },
        onCommitTriggered: (nruIndex, triggerId) => {
          console.log(`🎯 Commit triggered for NRU ${nruIndex}, ID: ${triggerId}`);
          // Could auto-play content here
        },
        onUndoTriggered: (triggerId) => {
          console.log(`↩️ Undo triggered for ${triggerId}`);
        },
      }
    );
  }, []);
  
  // Initialize controller when recommendations change
  useEffect(() => {
    if (recommendations.length > 0) {
      presentationController.initialize(recommendations.length);
      presentationController.send({ type: 'START_PRESENT', nruIndex: currentIndex });
      // Start tracking first card view
      recordCardViewStart();
    }
  }, [recommendations.length, recordCardViewStart]);
  
  // ========== Real-Time Telemetry ==========
  // Generate stable session ID
  const sessionId = useMemo(() => `session-${Date.now()}`, []);
  
  // Initialize telemetry hook
  const telemetry = useTelemetry({
    userId: userProfile.id,
    sessionId,
    backendUrl: 'http://localhost:8888',
    batchIntervalMs: 2000,
    useWebSocket: true,
  });
  
  // Track dwell time on each card
  const currentContentId = recommendations[currentIndex]?.content.id || null;
  useDwellTime(currentContentId, telemetry.trackDwell);
  
  // Track focus changes (tab switching)
  useFocusTracking(telemetry.trackFocusChange);
  
  // Track navigation as potential hesitation signal
  const navigationCount = useRef(0);
  const lastNavigationTime = useRef<number>(Date.now());
  
  // Update decision state from enhanced telemetry and presentation controller
  useEffect(() => {
    if (telemetry.enhancedDecisionState) {
      updateDecisionState({
        stressLevel: telemetry.enhancedDecisionState.stressLevel,
        scrollVelocity: telemetry.enhancedDecisionState.scrollVelocity,
        dwellTime: telemetry.enhancedDecisionState.dwellTime,
        focusChanges: telemetry.enhancedDecisionState.focusChanges,
        confidenceScore: telemetry.enhancedDecisionState.confidenceScore,
      });
      
      // Update presentation controller with decision state
      presentationController.updateDecisionState(telemetry.enhancedDecisionState);
    }
  }, [telemetry.enhancedDecisionState, updateDecisionState, presentationController]);
  
  // Periodic monitor tick for presentation controller
  useEffect(() => {
    const tickInterval = setInterval(() => {
      presentationController.send({ type: 'MONITOR_TICK' });
      
      // Update exposure progress
      const ctx = presentationController.getContext();
      if (ctx.adaptedExposureTarget > 0) {
        setExposureProgress((ctx.currentExposureTime / ctx.adaptedExposureTarget) * 100);
      }
    }, 500);
    
    return () => clearInterval(tickInterval);
  }, [presentationController]);
  
  // Track back-and-forth navigation as hesitation
  const trackNavigationHesitation = useCallback(() => {
    const now = Date.now();
    const timeSinceLastNav = now - lastNavigationTime.current;
    
    // Quick successive navigations indicate hesitation
    if (timeSinceLastNav < 2000) {
      navigationCount.current += 1;
      
      // After 3+ quick navigations, this is likely hesitation
      if (navigationCount.current >= 3) {
        telemetry.trackMicroPause(navigationCount.current / 10);
        telemetry.trackFocusChange();
      }
    } else {
      navigationCount.current = 1;
    }
    
    lastNavigationTime.current = now;
  }, [telemetry]);

  // Auto-advance logic with ADAPTIVE PACING
  // T_expose = T_base - α·h(t|x) - β·(dC/dt)
  useEffect(() => {
    if (autoAdvance && isPlaying && currentIndex < recommendations.length - 1) {
      // Use adapted exposure time from presentation controller (in ms)
      const exposureMs = adaptedExposureTime * 1000;
      
      autoAdvanceTimer.current = setTimeout(() => {
        addInteraction({
          contentId: recommendations[currentIndex].content.id,
          action: 'view',
          timestamp: new Date(),
          viewDuration: Date.now() - viewStartTime.current,
        });
        viewStartTime.current = Date.now();
        
        // Notify presentation controller
        presentationController.send({ type: 'EXPOSURE_COMPLETE' });
        nextRecommendation();
      }, exposureMs);
    }

    return () => {
      if (autoAdvanceTimer.current) {
        clearTimeout(autoAdvanceTimer.current);
      }
    };
  }, [currentIndex, isPlaying, autoAdvance, recommendations.length, adaptedExposureTime, presentationController, addInteraction, nextRecommendation]);

  // Enhanced navigation with telemetry and analytics
  const handleNext = useCallback(() => {
    if (currentIndex < recommendations.length - 1) {
      trackNavigationHesitation();
      recordCardViewEnd(); // End current card view
      nextRecommendation();
      recordCardViewStart(); // Start new card view
    }
  }, [currentIndex, recommendations.length, nextRecommendation, trackNavigationHesitation, recordCardViewEnd, recordCardViewStart]);
  
  const handlePrevious = useCallback(() => {
    if (currentIndex > 0) {
      trackNavigationHesitation();
      recordBacktrack(); // Track going back as backtrack
      // Going back is a stronger hesitation signal
      telemetry.trackFocusChange();
      previousRecommendation();
    }
  }, [currentIndex, previousRecommendation, trackNavigationHesitation, telemetry, recordBacktrack]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case ' ':
          e.preventDefault();
          handleNext();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          handlePrevious();
          break;
        case 'Escape':
          telemetry.flush(); // Flush telemetry before closing
          recordCardViewEnd(); // Record current card view before closing
          recordAbandonment(); // Track as abandonment
          onClose();
          break;
        case 'p':
          togglePlayback();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleNext, handlePrevious, onClose, togglePlayback, telemetry, recordCardViewEnd, recordAbandonment]);

  // Touch/swipe handling
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    touchEndX.current = e.touches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback(() => {
    const diff = touchStartX.current - touchEndX.current;
    const threshold = 50;

    if (Math.abs(diff) > threshold) {
      if (diff > 0) {
        handleNext();
      } else if (diff < 0) {
        handlePrevious();
      }
    }
  }, [handleNext, handlePrevious]);

  // Handle narration end - advance to next card
  const handleNarrationEnd = useCallback(() => {
    if (audioEnabled && currentIndex < recommendations.length - 1) {
      // Log interaction for current card
      addInteraction({
        contentId: recommendations[currentIndex].content.id,
        action: 'view',
        timestamp: new Date(),
        viewDuration: Date.now() - viewStartTime.current,
      });
      viewStartTime.current = Date.now();
      // Advance to next (natural progression, not hesitation)
      nextRecommendation();
    }
  }, [audioEnabled, currentIndex, recommendations.length, addInteraction, nextRecommendation]);
  
  // Toggle audio mode
  const toggleAudio = useCallback(() => {
    if (audioEnabled) {
      window.speechSynthesis.cancel();
    }
    setAudioEnabled(!audioEnabled);
  }, [audioEnabled]);

  if (recommendations.length === 0) return null;

  const currentRec = recommendations[currentIndex];
  const isLastCard = currentIndex === recommendations.length - 1;

  return (
    <motion.div
      className="fixed inset-0 z-50 bg-midnight-950"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,_rgba(251,191,36,0.1)_0%,_transparent_50%)]" />
      </div>

      {/* Close Button */}
      <button
        className="absolute top-6 right-6 z-50 p-3 bg-midnight-900/80 backdrop-blur-md rounded-full border border-white/10 hover:border-coral-400/50 hover:bg-coral-500/10 transition-all"
        onClick={() => {
          telemetry.flush();
          recordCardViewEnd(); // Record current card view before closing
          recordAbandonment();
          onClose();
        }}
      >
        <X className="w-6 h-6 text-white/70 hover:text-coral-400" />
      </button>

      {/* Current Card - No AnimatePresence needed */}
      <div className="relative w-full h-full">
        <ReelCard
          key={currentRec.content.id}
          recommendation={currentRec}
          isActive={true}
          index={currentIndex}
          totalCards={recommendations.length}
          onNarrationEnd={handleNarrationEnd}
          autoPlayAudio={audioEnabled}
          onSelect={(contentId) => {
            recordCardViewEnd(); // Record card view before selection
            recordSelection(contentId);
            telemetry.flush();
          }}
          onSelectionComplete={() => {
            // Close the reel after selection
            onClose();
          }}
        />
      </div>

      {/* Navigation Arrows */}
      <div className="absolute inset-y-0 left-0 flex items-center pl-4 md:pl-8">
        <button
          className={`p-4 rounded-full backdrop-blur-md transition-all ${
            currentIndex > 0 
              ? 'bg-white/10 hover:bg-white/20 text-white cursor-pointer' 
              : 'bg-white/5 text-white/20 cursor-not-allowed'
          }`}
          onClick={handlePrevious}
          disabled={currentIndex === 0}
        >
          <ChevronLeft className="w-8 h-8" />
        </button>
      </div>

      <div className="absolute inset-y-0 right-0 flex items-center pr-4 md:pr-8">
        <button
          className={`p-4 rounded-full backdrop-blur-md transition-all ${
            currentIndex < recommendations.length - 1 
              ? 'bg-white/10 hover:bg-white/20 text-white cursor-pointer' 
              : 'bg-white/5 text-white/20 cursor-not-allowed'
          }`}
          onClick={handleNext}
          disabled={currentIndex === recommendations.length - 1}
        >
          <ChevronRight className="w-8 h-8" />
        </button>
      </div>

      {/* Bottom Controls */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-4">
        {/* Audio Toggle - Enable/Disable auto narration */}
        <button
          className={`p-4 backdrop-blur-md rounded-full border transition-all ${
            audioEnabled 
              ? 'bg-amber-500/20 border-amber-400/50 hover:border-amber-400' 
              : 'bg-midnight-900/80 border-white/10 hover:border-white/30'
          }`}
          onClick={toggleAudio}
          title={audioEnabled ? 'Mute narration' : 'Enable narration'}
        >
          {audioEnabled ? (
            <Volume2 className="w-5 h-5 text-amber-400" />
          ) : (
            <VolumeX className="w-5 h-5 text-white/50" />
          )}
        </button>

        {/* Play/Pause Toggle */}
        <button
          className="p-4 bg-midnight-900/80 backdrop-blur-md rounded-full border border-white/10 hover:border-amber-400/50"
          onClick={togglePlayback}
        >
          {isPlaying ? (
            <Pause className="w-5 h-5 text-amber-400" />
          ) : (
            <Play className="w-5 h-5 text-white" />
          )}
        </button>

        {/* Card Indicators */}
        <div className="flex items-center gap-2 px-4">
          {recommendations.map((_, idx) => (
            <button
              key={idx}
              className={`w-2.5 h-2.5 rounded-full transition-all ${
                idx === currentIndex 
                  ? 'bg-amber-400 scale-125' 
                  : idx < currentIndex
                    ? 'bg-amber-400/50'
                    : 'bg-white/30 hover:bg-white/50'
              }`}
              onClick={() => setCurrentIndex(idx)}
            />
          ))}
        </div>

        {/* Restart Button */}
        {isLastCard && (
          <button
            className="p-4 bg-amber-500/20 backdrop-blur-md rounded-full border border-amber-400/30 hover:border-amber-400"
            onClick={() => setCurrentIndex(0)}
          >
            <RotateCcw className="w-5 h-5 text-amber-400" />
          </button>
        )}
      </div>

      {/* Keyboard Hints */}
      <div className="absolute bottom-8 right-8 hidden md:flex items-center gap-4 text-white/30 text-xs">
        <span className="flex items-center gap-1">
          <kbd className="px-2 py-1 bg-white/10 rounded">←</kbd>
          <kbd className="px-2 py-1 bg-white/10 rounded">→</kbd>
          Navigate
        </span>
        <span className="flex items-center gap-1">
          <kbd className="px-2 py-1 bg-white/10 rounded">Esc</kbd>
          Close
        </span>
      </div>
      
      {/* Telemetry Status Indicator */}
      <div className="absolute top-6 left-6 z-50 hidden md:flex items-center gap-2">
        <div 
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full backdrop-blur-md border text-xs ${
            telemetry.state.isConnected 
              ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-400'
              : 'bg-midnight-900/80 border-white/10 text-white/40'
          }`}
          title="Decision state telemetry"
        >
          <Activity className="w-3 h-3" />
          <span>
            {telemetry.state.isConnected ? 'Live' : 'Offline'}
          </span>
        </div>
        
        {/* Enhanced State Metrics */}
        {telemetry.enhancedDecisionState && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-midnight-900/80 backdrop-blur-md rounded-full border border-white/10 text-xs text-white/50">
            <span title="Hesitation Score">
              η: {(telemetry.enhancedDecisionState.hesitationScore * 100).toFixed(0)}%
            </span>
            <span className="text-white/20">|</span>
            <span title="Commit Probability">
              P: {(telemetry.enhancedDecisionState.commitProbability * 100).toFixed(0)}%
            </span>
            <span className="text-white/20">|</span>
            <span title="Optimal Set Size">
              n: {telemetry.enhancedDecisionState.optimalSetSize}
            </span>
          </div>
        )}
        
        {/* Adaptive Pacing Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-midnight-900/80 backdrop-blur-md rounded-full border border-cyan-400/20 text-xs">
          <Clock className="w-3 h-3 text-cyan-400" />
          <span className="text-cyan-400" title="Adaptive Exposure Time">
            T: {adaptedExposureTime.toFixed(1)}s
          </span>
          <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div 
              className="h-full bg-cyan-400 transition-all duration-300"
              style={{ width: `${Math.min(exposureProgress, 100)}%` }}
            />
          </div>
          {presentationContext?.currentState && (
            <>
              <span className="text-white/20">|</span>
              <span 
                className={`${
                  presentationContext.currentState === 'COMMIT' ? 'text-emerald-400' :
                  presentationContext.currentState === 'ADJUST' ? 'text-amber-400' :
                  'text-white/50'
                }`}
                title="State Machine State"
              >
                {presentationContext.currentState}
              </span>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
