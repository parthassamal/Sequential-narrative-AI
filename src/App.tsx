import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ConversationalInterface } from './components/ConversationalInterface';
import { ReelViewer } from './components/ReelViewer';
import { DecisionStateIndicator } from './components/DecisionStateIndicator';
import { AuthModal } from './components/AuthModal';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { HelpGuide, HelpButton } from './components/HelpGuide';
import { useAppStore } from './store/appStore';
import { useUserPersistence } from './hooks/useUserPersistence';
import { useAnalytics } from './hooks/useAnalytics';
import { Sparkles, LogIn, LogOut, User, ChevronDown, BarChart3, Settings } from 'lucide-react';

function App() {
  const { showReel, setShowReel, updateDecisionState } = useAppStore();
  const { user, saveUser, clearUser } = useUserPersistence();
  const { recordAbandonment } = useAnalytics();
  
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Simulate decision state updates based on time spent
  useEffect(() => {
    const interval = setInterval(() => {
      updateDecisionState({
        confidenceScore: Math.random() * 0.3 + 0.6,
      });
    }, 10000);

    return () => clearInterval(interval);
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

  const handleLogout = () => {
    clearUser();
    setShowUserMenu(false);
  };

  return (
    <div className="relative min-h-screen bg-midnight-950 overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        {/* Gradient Orbs */}
        <motion.div
          className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 rounded-full bg-gradient-to-br from-amber-500/10 to-transparent blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, 50, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 rounded-full bg-gradient-to-tl from-coral-500/10 to-transparent blur-3xl"
          animate={{
            x: [0, -80, 0],
            y: [0, -60, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1/3 h-1/3 rounded-full bg-gradient-to-r from-teal-500/5 to-transparent blur-3xl"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Grid Pattern */}
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
            `,
            backgroundSize: '100px 100px',
          }}
        />

        {/* Noise Texture */}
        <div className="absolute inset-0 opacity-[0.015] mix-blend-overlay bg-noise" />
      </div>

      {/* Header */}
      <header className="relative z-10 px-6 py-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-coral-500 shadow-lg shadow-amber-500/20">
              <Sparkles className="w-5 h-5 text-midnight-950" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold text-white tracking-tight">
                Vibe AI
              </h1>
              <p className="text-[10px] text-white/40 uppercase tracking-widest">
                Sequential Narrative
              </p>
            </div>
          </motion.div>

          {/* Auth Section */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            {/* Help Button */}
            <HelpButton onClick={() => setShowHelp(true)} />
            
            {/* Analytics Button */}
            <button
              onClick={() => setShowAnalytics(true)}
              className="p-2.5 text-white/50 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="View Analytics"
            >
              <BarChart3 className="w-5 h-5" />
            </button>

            {user ? (
              // Logged in - show user menu
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full hover:bg-white/10 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-coral-500 flex items-center justify-center">
                    <User className="w-4 h-4 text-midnight-950" />
                  </div>
                  <span className="text-white text-sm font-medium hidden sm:block">
                    {user.name}
                  </span>
                  <ChevronDown className="w-4 h-4 text-white/50" />
                </button>

                {/* Dropdown Menu */}
                <AnimatePresence>
                  {showUserMenu && (
                    <motion.div
                      className="absolute right-0 top-full mt-2 w-56 bg-midnight-900 border border-white/10 rounded-xl shadow-xl overflow-hidden z-50"
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
                          onClick={() => {
                            setShowHelp(true);
                            setShowUserMenu(false);
                          }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5 transition-colors"
                        >
                          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                            <line x1="12" y1="17" x2="12.01" y2="17"/>
                          </svg>
                          <span className="text-sm">Help & Guide</span>
                        </button>
                        
                        <button
                          onClick={() => {
                            setShowAnalytics(true);
                            setShowUserMenu(false);
                          }}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5 transition-colors"
                        >
                          <BarChart3 className="w-4 h-4" />
                          <span className="text-sm">Analytics Dashboard</span>
                        </button>
                        
                        <button
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-white/70 hover:text-white hover:bg-white/5 transition-colors"
                        >
                          <Settings className="w-4 h-4" />
                          <span className="text-sm">Preferences</span>
                        </button>
                      </div>
                      
                      <div className="border-t border-white/10 py-1">
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-red-400 hover:bg-white/5 transition-colors"
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
              // Not logged in - show login button
              <button
                onClick={() => setShowAuthModal(true)}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-amber-500 to-coral-500 rounded-full text-midnight-950 font-semibold hover:from-amber-400 hover:to-coral-400 transition-colors shadow-lg shadow-amber-500/20"
              >
                <LogIn className="w-4 h-4" />
                <span>Sign In</span>
              </button>
            )}
          </motion.div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-200px)] px-6 py-12">
        <ConversationalInterface />
      </main>

      {/* Footer */}
      <footer className="relative z-10 px-6 py-6 text-center">
        <p className="text-xs text-white/30">
          AI-Driven Sequential Narrative Recommendation System
        </p>
        <p className="text-xs text-white/20 mt-1">
          Powered by TMDb, YouTube & Paramount+
        </p>
      </footer>

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

      {/* Reel Viewer Modal */}
      <AnimatePresence>
        {showReel && (
          <ReelViewer onClose={handleReelClose} />
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

export default App;
