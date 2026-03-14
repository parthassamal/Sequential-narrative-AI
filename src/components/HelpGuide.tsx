/**
 * Help Guide Component
 * Provides user flows and guidance for the app
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  HelpCircle, 
  X, 
  Play, 
  MessageSquare, 
  Sparkles, 
  BarChart3,
  ChevronRight,
  ChevronLeft,
  Volume2,
  Bookmark,
  Zap,
  Target,
  Clock,
  MousePointer2,
  Lightbulb
} from 'lucide-react';

interface HelpGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

interface GuideStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  tips: string[];
  color: string;
}

const guideSteps: GuideStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to Sequential Narrative AI',
    description: 'An intelligent content discovery system that understands what you want to watch and presents personalized recommendations through engaging, narrated stories.',
    icon: <Sparkles className="w-8 h-8" />,
    tips: [
      'Tell us what mood you\'re in or what you\'re looking for',
      'Our AI analyzes your preferences in real-time',
      'Get 2-5 curated recommendations as a visual reel'
    ],
    color: 'amber'
  },
  {
    id: 'ask',
    title: 'Ask Me Anything',
    description: 'Start by describing what you\'re in the mood for. Be as specific or vague as you like - our AI understands natural language.',
    icon: <MessageSquare className="w-8 h-8" />,
    tips: [
      '"I want something thrilling like Breaking Bad"',
      '"Show me feel-good movies for a rainy day"',
      '"What\'s good for a movie night with friends?"',
      '"I need a documentary about space exploration"'
    ],
    color: 'cyan'
  },
  {
    id: 'reel',
    title: 'Your Personalized Reel',
    description: 'Swipe through AI-curated recommendations presented as a beautiful visual reel. Each recommendation comes with a personalized micro-narrative explaining why it\'s perfect for you.',
    icon: <Play className="w-8 h-8" />,
    tips: [
      'Swipe left/right or use arrow keys to navigate',
      'Listen to AI-narrated explanations for each pick',
      'Click the Watch button to select a title and open its streaming destination',
      'The AI adapts based on how long you view each card'
    ],
    color: 'purple'
  },
  {
    id: 'audio',
    title: 'Audio Narration',
    description: 'Each recommendation includes an AI-generated audio explanation. Toggle audio on/off using the speaker icon in the reel viewer.',
    icon: <Volume2 className="w-8 h-8" />,
    tips: [
      'Audio plays automatically when enabled',
      'Click the speaker icon to mute/unmute',
      'Narration continues seamlessly between cards',
      'Perfect for hands-free browsing'
    ],
    color: 'green'
  },
  {
    id: 'decision',
    title: 'Smart Decision Support',
    description: 'Our AI tracks your browsing patterns in real-time to optimize recommendations. The system adapts to your decision-making style.',
    icon: <Target className="w-8 h-8" />,
    tips: [
      'The AI notices when you\'re hesitating',
      'Recommendations adjust based on your behavior',
      'Quick decisions get faster pacing',
      'Uncertainty triggers more diverse options'
    ],
    color: 'blue'
  },
  {
    id: 'analytics',
    title: 'Decision Analytics',
    description: 'Track your viewing patterns and decision metrics. See how quickly you find content you love and how diverse your viewing habits are.',
    icon: <BarChart3 className="w-8 h-8" />,
    tips: [
      'View your session history and trends',
      'Track decision time improvements',
      'See diversity in your recommendations',
      'Access from the chart icon in the header'
    ],
    color: 'pink'
  }
];

const quickTips = [
  { icon: <MousePointer2 className="w-4 h-4" />, text: 'Swipe or use arrow keys to navigate recommendations' },
  { icon: <Clock className="w-4 h-4" />, text: 'Spend more time on cards you like - the AI learns' },
  { icon: <Volume2 className="w-4 h-4" />, text: 'Enable audio for hands-free discovery' },
  { icon: <Bookmark className="w-4 h-4" />, text: 'Click the "Watch on ..." button when you find something great' },
  { icon: <Lightbulb className="w-4 h-4" />, text: 'Be specific in your queries for better results' },
];

export function HelpGuide({ isOpen, onClose }: HelpGuideProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [view, setView] = useState<'guide' | 'tips'>('guide');

  if (!isOpen) return null;

  const step = guideSteps[currentStep];
  
  const colorClasses: Record<string, { bg: string; border: string; text: string; icon: string }> = {
    amber: { bg: 'from-amber-500/20 to-orange-500/20', border: 'border-amber-500/30', text: 'text-amber-400', icon: 'bg-amber-500/20' },
    cyan: { bg: 'from-cyan-500/20 to-blue-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400', icon: 'bg-cyan-500/20' },
    purple: { bg: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500/30', text: 'text-purple-400', icon: 'bg-purple-500/20' },
    green: { bg: 'from-green-500/20 to-emerald-500/20', border: 'border-green-500/30', text: 'text-green-400', icon: 'bg-green-500/20' },
    blue: { bg: 'from-blue-500/20 to-indigo-500/20', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'bg-blue-500/20' },
    pink: { bg: 'from-pink-500/20 to-rose-500/20', border: 'border-pink-500/30', text: 'text-pink-400', icon: 'bg-pink-500/20' },
  };

  const colors = colorClasses[step.color];

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <motion.div
        className="relative w-full max-w-2xl bg-midnight-900 rounded-2xl border border-white/10 shadow-2xl overflow-hidden"
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        transition={{ type: 'spring', damping: 25 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <HelpCircle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Help & Guide</h2>
              <p className="text-white/50 text-sm">Learn how to use the app</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-white/50 hover:text-white transition-colors rounded-lg hover:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Toggle */}
        <div className="flex border-b border-white/10">
          <button
            onClick={() => setView('guide')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              view === 'guide'
                ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-500/5'
                : 'text-white/50 hover:text-white/70'
            }`}
          >
            Step-by-Step Guide
          </button>
          <button
            onClick={() => setView('tips')}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              view === 'tips'
                ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-500/5'
                : 'text-white/50 hover:text-white/70'
            }`}
          >
            Quick Tips
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <AnimatePresence mode="wait">
            {view === 'guide' ? (
              <motion.div
                key="guide"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                {/* Step Content */}
                <div className={`bg-gradient-to-br ${colors.bg} rounded-xl p-6 border ${colors.border}`}>
                  <div className="flex items-start gap-4">
                    <div className={`p-3 ${colors.icon} rounded-xl ${colors.text}`}>
                      {step.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className={`text-xl font-bold ${colors.text} mb-2`}>
                        {step.title}
                      </h3>
                      <p className="text-white/70 leading-relaxed">
                        {step.description}
                      </p>
                    </div>
                  </div>

                  {/* Tips */}
                  <div className="mt-6 space-y-2">
                    <h4 className="text-white/50 text-sm font-medium uppercase tracking-wide">
                      {step.id === 'ask' ? 'Example Queries' : 'Tips'}
                    </h4>
                    <ul className="space-y-2">
                      {step.tips.map((tip, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-white/80">
                          <Zap className={`w-4 h-4 ${colors.text} mt-0.5 flex-shrink-0`} />
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Navigation */}
                <div className="flex items-center justify-between mt-6">
                  <button
                    onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                    disabled={currentStep === 0}
                    className="flex items-center gap-2 px-4 py-2 text-white/70 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Previous
                  </button>

                  {/* Step Indicators */}
                  <div className="flex items-center gap-2">
                    {guideSteps.map((_, idx) => (
                      <button
                        key={idx}
                        onClick={() => setCurrentStep(idx)}
                        className={`w-2.5 h-2.5 rounded-full transition-all ${
                          idx === currentStep
                            ? 'bg-amber-400 w-6'
                            : 'bg-white/20 hover:bg-white/40'
                        }`}
                      />
                    ))}
                  </div>

                  <button
                    onClick={() => {
                      if (currentStep === guideSteps.length - 1) {
                        onClose();
                      } else {
                        setCurrentStep(currentStep + 1);
                      }
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 text-amber-400 rounded-lg hover:bg-amber-500/30 transition-colors"
                  >
                    {currentStep === guideSteps.length - 1 ? 'Get Started' : 'Next'}
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="tips"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <h3 className="text-white font-semibold text-lg mb-4">Quick Reference</h3>
                
                {quickTips.map((tip, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-4 p-4 bg-white/5 rounded-xl border border-white/10 hover:bg-white/10 transition-colors"
                  >
                    <div className="p-2 bg-amber-500/20 rounded-lg text-amber-400">
                      {tip.icon}
                    </div>
                    <span className="text-white/80">{tip.text}</span>
                  </div>
                ))}

                {/* Keyboard Shortcuts */}
                <div className="mt-6 p-4 bg-white/5 rounded-xl border border-white/10">
                  <h4 className="text-white font-medium mb-3">Keyboard Shortcuts</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-white/10 rounded text-white/70">←</kbd>
                      <span className="text-white/50">Previous card</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-white/10 rounded text-white/70">→</kbd>
                      <span className="text-white/50">Next card</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-white/10 rounded text-white/70">Space</kbd>
                      <span className="text-white/50">Next card</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-white/10 rounded text-white/70">Esc</kbd>
                      <span className="text-white/50">Close viewer</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <kbd className="px-2 py-1 bg-white/10 rounded text-white/70">P</kbd>
                      <span className="text-white/50">Play/Pause</span>
                    </div>
                  </div>
                </div>

                {/* Need More Help */}
                <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20 mt-4">
                  <h4 className="text-amber-400 font-medium mb-2 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" />
                    Pro Tip
                  </h4>
                  <p className="text-white/70 text-sm">
                    The more you use the app, the better it understands your preferences. 
                    Don't hesitate to make multiple queries to refine your recommendations!
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  );
}

// Floating Help Button Component
export function HelpButton({ onClick }: { onClick: () => void }) {
  return (
    <motion.button
      onClick={onClick}
      className="p-2 text-white/50 hover:text-amber-400 transition-colors rounded-lg hover:bg-white/5"
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      title="Help & Guide"
    >
      <HelpCircle className="w-5 h-5" />
    </motion.button>
  );
}
