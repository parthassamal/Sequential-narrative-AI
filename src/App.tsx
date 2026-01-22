import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { StreamingInterface } from './components/StreamingInterface';
import { ReelViewer } from './components/ReelViewer';
import { DecisionStateIndicator } from './components/DecisionStateIndicator';
import { AuthModal } from './components/AuthModal';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { HelpGuide } from './components/HelpGuide';
import { useAppStore } from './store/appStore';
import { useUserPersistence } from './hooks/useUserPersistence';
import { useAnalytics } from './hooks/useAnalytics';

function App() {
  const { showReel, setShowReel, updateDecisionState } = useAppStore();
  const { saveUser } = useUserPersistence();
  const { recordAbandonment } = useAnalytics();
  
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Stop any lingering audio/speech on page load
  useEffect(() => {
    // Cancel any speech synthesis that might be playing from previous session
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    
    // Stop any audio elements that might be playing
    document.querySelectorAll('audio, video').forEach((el) => {
      (el as HTMLMediaElement).pause();
      (el as HTMLMediaElement).currentTime = 0;
    });
  }, []);

  // Track user activity to update decision state
  useEffect(() => {
    let idleTime = 0;
    let scrollCount = 0;
    
    // Track scrolling as engagement signal
    const handleScroll = () => {
      scrollCount++;
      idleTime = 0;
      
      // More scrolling = higher stress (indecision)
      const stressFromScrolling = Math.min(scrollCount / 20, 0.4);
      updateDecisionState({
        stressLevel: 0.2 + stressFromScrolling,
        scrollVelocity: scrollCount,
      });
    };
    
    // Track idle time
    const handleActivity = () => {
      idleTime = 0;
    };
    
    // Update decision state periodically
    const interval = setInterval(() => {
      idleTime++;
      
      // Long idle time = relaxed (low stress)
      // High scroll count = overwhelmed (high stress)
      const stressLevel = Math.max(0.1, Math.min(0.9, 
        0.2 + (scrollCount / 30) - (idleTime * 0.05)
      ));
      
      updateDecisionState({
        stressLevel,
        confidenceScore: Math.max(0.3, 1 - stressLevel),
        dwellTime: idleTime * 5000,
      });
      
      // Decay scroll count over time
      scrollCount = Math.max(0, scrollCount - 2);
    }, 5000);

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('mousemove', handleActivity, { passive: true });
    window.addEventListener('click', handleActivity, { passive: true });

    return () => {
      clearInterval(interval);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('click', handleActivity);
    };
  }, [updateDecisionState]);

  // Track abandonment when reel is closed without selection
  const handleReelClose = () => {
    recordAbandonment();
    setShowReel(false);
  };

  const handleLogin = (userData: { name: string; email: string }) => {
    saveUser(userData);
    setShowAuthModal(false);
  };

  return (
    <div className="relative min-h-screen">
      {/* Main Streaming Interface */}
      <StreamingInterface />

      {/* Decision State Indicator */}
      <DecisionStateIndicator />

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onLogin={handleLogin}
      />

      {/* Analytics Dashboard */}
      <AnalyticsDashboard
        isOpen={showAnalytics}
        onClose={() => setShowAnalytics(false)}
      />

      {/* Help Guide */}
      <HelpGuide
        isOpen={showHelp}
        onClose={() => setShowHelp(false)}
      />

      {/* Reel Viewer Modal - Sequential Narrative Presentation */}
      <AnimatePresence>
        {showReel && (
          <motion.div
            className="fixed inset-0 z-[100]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ReelViewer onClose={handleReelClose} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
