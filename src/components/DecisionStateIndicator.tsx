import { motion } from 'framer-motion';
import { Brain, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { createPortal } from 'react-dom';
import { useAppStore } from '../store/appStore';

export function DecisionStateIndicator() {
  const { userProfile } = useAppStore();
  const { decisionState } = userProfile;

  const getStressLevel = () => {
    if (decisionState.stressLevel < 0.3) return 'low';
    if (decisionState.stressLevel < 0.6) return 'moderate';
    return 'high';
  };

  const stressLevel = getStressLevel();

  const stressConfig = {
    low: {
      color: 'teal',
      icon: CheckCircle,
      message: 'You seem relaxed. Take your time browsing!',
      bgGradient: 'from-teal-500/20 to-teal-600/10',
      borderColor: 'border-teal-500/30',
      iconColor: 'text-teal-400',
    },
    moderate: {
      color: 'amber',
      icon: Info,
      message: 'Let me help narrow down your choices.',
      bgGradient: 'from-amber-500/20 to-amber-600/10',
      borderColor: 'border-amber-500/30',
      iconColor: 'text-amber-400',
    },
    high: {
      color: 'coral',
      icon: AlertTriangle,
      message: 'Feeling overwhelmed? Try asking me directly!',
      bgGradient: 'from-coral-500/20 to-coral-600/10',
      borderColor: 'border-coral-500/30',
      iconColor: 'text-coral-400',
    },
  };

  const config = stressConfig[stressLevel];
  const Icon = config.icon;

  // Use portal to render directly to body, ensuring fixed positioning works
  return createPortal(
    <motion.div
      className={`fixed bottom-6 left-6 z-[9999] max-w-xs bg-gradient-to-r ${config.bgGradient} backdrop-blur-xl rounded-2xl border ${config.borderColor} p-4 shadow-xl`}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: 1 }}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg bg-white/5 ${config.iconColor}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Brain className={`w-4 h-4 ${config.iconColor}`} />
            <span className="text-xs font-medium text-white/60">Decision Support</span>
          </div>
          <p className="text-sm text-white/80">{config.message}</p>
          
          {/* Stress Bar */}
          <div className="mt-3 h-1.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${
                stressLevel === 'low' 
                  ? 'bg-teal-400' 
                  : stressLevel === 'moderate' 
                    ? 'bg-amber-400' 
                    : 'bg-coral-400'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${decisionState.stressLevel * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-white/40">Relaxed</span>
            <span className="text-[10px] text-white/40">Overwhelmed</span>
          </div>
        </div>
      </div>
    </motion.div>,
    document.body
  );
}
