/**
 * Analytics Dashboard Component
 * Displays AI-powered decision metrics and user behavior insights
 * 
 * Core Metrics:
 * - CCR: Commit Conversion Rate
 * - DLR: Decision Latency Reduction
 * - DI: Deferral Index
 * - SRR: Stress Reduction Ratio
 * - CTA: Confidence Trigger Accuracy
 * - DE: Diversity Exposure
 */
import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { X, Clock, CheckCircle, XCircle, Eye, TrendingUp, Activity, BarChart3, Target, Brain, Gauge, Zap, Shield, Sparkles } from 'lucide-react';
import { useAnalytics, AggregatedMetrics } from '../hooks/useAnalytics';

interface AnalyticsDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SystemMetrics {
  ccr_3: number;
  ccr_5: number;
  ccr_7: number;
  dlr: number;
  di: number;
  srr: number;
  cta: number;
  de: number;
  total_sessions: number;
  committed_sessions: number;
  abandoned_sessions: number;
  ece: number;
}

interface CalibrationStats {
  ece: number;
  num_calibration_points: number;
  is_calibrator_fitted: boolean;
  bins: Array<{
    accuracy: number;
    mean_confidence: number;
    count: number;
  }>;
}

interface RealtimeMetrics {
  active_sessions: number;
  recent_conversion_rate: number;
  recent_sessions_count: number;
  trigger_quality: {
    total_triggers: number;
    successful_commits: number;
    quick_cancels: number;
    accuracy: number;
    quick_cancel_rate: number;
  };
  stress_trend: {
    trend: string;
    average: number;
    slope?: number;
  };
  calibration_ece: number;
}

export function AnalyticsDashboard({ isOpen, onClose }: AnalyticsDashboardProps) {
  const { getSessions, clearMetrics } = useAnalytics();
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [calibrationStats, setCalibrationStats] = useState<CalibrationStats | null>(null);
  const [realtimeMetrics, setRealtimeMetrics] = useState<RealtimeMetrics | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'advanced' | 'calibration'>('overview');
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Calculate metrics fresh from localStorage each render
  const sessions = getSessions();
  const aggregatedMetrics = useMemo(() => {
    if (sessions.length === 0) {
      return {
        totalSessions: 0,
        avgDecisionTimeMs: 0,
        completionRate: 0,
        abandonmentRate: 0,
        avgViewedCards: 0,
        avgRecommendationsCount: 0,
        mostSelectedGenres: [],
        hourlyDistribution: [],
      };
    }

    const completedSessions = sessions.filter(s => s.selectedContentId && !s.abandoned);
    const abandonedSessions = sessions.filter(s => s.abandoned && !s.selectedContentId);
    const sessionsWithDecision = sessions.filter(s => s.decisionTimeMs !== null && s.decisionTimeMs > 0);

    const avgDecisionTime = sessionsWithDecision.length > 0
      ? sessionsWithDecision.reduce((sum, s) => sum + (s.decisionTimeMs || 0), 0) / sessionsWithDecision.length
      : 0;

    const avgViewedCards = sessions.reduce((sum, s) => sum + s.viewedCards, 0) / sessions.length;
    const avgRecommendations = sessions.reduce((sum, s) => sum + s.recommendationsCount, 0) / sessions.length;

    return {
      totalSessions: sessions.length,
      avgDecisionTimeMs: Math.round(avgDecisionTime),
      completionRate: Math.round((completedSessions.length / sessions.length) * 100),
      abandonmentRate: Math.round((abandonedSessions.length / sessions.length) * 100),
      avgViewedCards: Math.round(avgViewedCards * 10) / 10,
      avgRecommendationsCount: Math.round(avgRecommendations * 10) / 10,
      mostSelectedGenres: [],
      hourlyDistribution: [],
    };
  }, [sessions, refreshKey]);

  // Fetch system metrics from backend
  useEffect(() => {
    if (isOpen) {
      fetchSystemMetrics();
      const interval = setInterval(fetchRealtimeMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const fetchSystemMetrics = async () => {
    setLoading(true);
    try {
      const [metricsRes, calibrationRes, realtimeRes] = await Promise.all([
        fetch('http://localhost:8888/api/metrics/aggregate'),
        fetch('http://localhost:8888/api/metrics/calibration'),
        fetch('http://localhost:8888/api/metrics/realtime'),
      ]);
      
      if (metricsRes.ok) {
        setSystemMetrics(await metricsRes.json());
      }
      if (calibrationRes.ok) {
        setCalibrationStats(await calibrationRes.json());
      }
      if (realtimeRes.ok) {
        setRealtimeMetrics(await realtimeRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch system metrics:', error);
    }
    setLoading(false);
  };

  const fetchRealtimeMetrics = async () => {
    try {
      const res = await fetch('http://localhost:8888/api/metrics/realtime');
      if (res.ok) {
        setRealtimeMetrics(await res.json());
      }
    } catch (error) {
      // Silently fail for realtime updates
    }
  };

  if (!isOpen) return null;

  const hasData = sessions.length > 0 || (systemMetrics?.total_sessions ?? 0) > 0;

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Dashboard */}
      <motion.div
        className="relative w-full max-w-5xl max-h-[90vh] overflow-auto bg-midnight-900 rounded-2xl border border-white/10 shadow-2xl"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-midnight-900/95 backdrop-blur-sm border-b border-white/10 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <BarChart3 className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Decision Analytics</h2>
              <p className="text-white/50 text-sm">AI-powered metrics & insights</p>
            </div>
          </div>
          
          {/* Tab Switcher */}
          <div className="flex items-center gap-2">
            <div className="flex bg-white/5 rounded-lg p-1">
              {(['overview', 'advanced', 'calibration'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                    activeTab === tab
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'text-white/50 hover:text-white/70'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
            <button onClick={onClose} className="p-2 text-white/50 hover:text-white ml-4">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading && (
            <div className="absolute inset-0 bg-midnight-900/50 flex items-center justify-center z-20">
              <div className="animate-spin w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full" />
            </div>
          )}

          {activeTab === 'overview' && (
            <OverviewTab 
              aggregatedMetrics={aggregatedMetrics}
              realtimeMetrics={realtimeMetrics}
              sessions={sessions}
              hasData={hasData}
              clearMetrics={clearMetrics}
            />
          )}

          {activeTab === 'advanced' && (
            <AdvancedMetricsTab 
              systemMetrics={systemMetrics}
              realtimeMetrics={realtimeMetrics}
            />
          )}

          {activeTab === 'calibration' && (
            <CalibrationTab 
              calibrationStats={calibrationStats}
              realtimeMetrics={realtimeMetrics}
            />
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

// ========== Overview Tab ==========
function OverviewTab({ 
  aggregatedMetrics, 
  realtimeMetrics, 
  sessions, 
  hasData, 
  clearMetrics 
}: {
  aggregatedMetrics: AggregatedMetrics | null;
  realtimeMetrics: RealtimeMetrics | null;
  sessions: any[];
  hasData: boolean;
  clearMetrics: () => void;
}) {
  const loadDemoData = async () => {
    try {
      const res = await fetch('http://localhost:8888/api/metrics/seed-demo', { method: 'POST' });
      if (res.ok) {
        window.location.reload();
      }
    } catch (error) {
      console.error('Failed to load demo data:', error);
    }
  };

  if (!hasData || !aggregatedMetrics) {
    return (
      <div className="p-12 text-center">
        <BarChart3 className="w-16 h-16 text-white/20 mx-auto mb-4" />
        <h3 className="text-white/70 text-lg mb-2">No Analytics Data Yet</h3>
        <p className="text-white/40 text-sm mb-6">
          Start using the recommendation system to collect decision metrics
        </p>
        <button
          onClick={loadDemoData}
          className="px-6 py-3 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg text-amber-400 font-medium transition-colors"
        >
          Load Demo Data
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={<Activity className="w-5 h-5" />}
          label="Total Sessions"
          value={aggregatedMetrics.totalSessions.toString()}
          color="blue"
        />
        <MetricCard
          icon={<Clock className="w-5 h-5" />}
          label="Avg Decision Time"
          value={formatTime(aggregatedMetrics.avgDecisionTimeMs)}
          color="amber"
          subtitle="Goal: < 90s"
        />
        <MetricCard
          icon={<CheckCircle className="w-5 h-5" />}
          label="Completion Rate"
          value={`${aggregatedMetrics.completionRate}%`}
          color="green"
          subtitle="Goal: > 70%"
        />
        <MetricCard
          icon={<XCircle className="w-5 h-5" />}
          label="Abandonment Rate"
          value={`${aggregatedMetrics.abandonmentRate}%`}
          color="red"
          subtitle="Goal: < 20%"
        />
      </div>

      {/* Realtime Status */}
      {realtimeMetrics && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-emerald-500/10 rounded-xl p-4 border border-emerald-500/20">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-400 text-sm font-medium">Live</span>
            </div>
            <div className="text-2xl font-bold text-white">{realtimeMetrics.active_sessions}</div>
            <div className="text-white/50 text-sm">Active Sessions</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="text-2xl font-bold text-white">
              {(realtimeMetrics.recent_conversion_rate * 100).toFixed(0)}%
            </div>
            <div className="text-white/50 text-sm">Recent Conversion</div>
            <div className="text-white/30 text-xs">{realtimeMetrics.recent_sessions_count} sessions</div>
          </div>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${
                realtimeMetrics.stress_trend.trend === 'increasing' ? 'text-red-400' :
                realtimeMetrics.stress_trend.trend === 'decreasing' ? 'text-green-400' :
                'text-white'
              }`}>
                {realtimeMetrics.stress_trend.trend === 'increasing' ? '↑' :
                 realtimeMetrics.stress_trend.trend === 'decreasing' ? '↓' : '→'}
              </span>
              <span className="text-white text-2xl font-bold">
                {(realtimeMetrics.stress_trend.average * 100).toFixed(0)}%
              </span>
            </div>
            <div className="text-white/50 text-sm">Stress Trend</div>
          </div>
        </div>
      )}

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          icon={<Eye className="w-5 h-5" />}
          label="Avg Cards Viewed"
          value={aggregatedMetrics.avgViewedCards.toFixed(1)}
          color="purple"
        />
        <MetricCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Avg Recommendations"
          value={aggregatedMetrics.avgRecommendationsCount.toFixed(1)}
          color="teal"
        />
      </div>

      {/* Recent Sessions */}
      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
        <h3 className="text-white font-medium mb-4">Recent Sessions</h3>
        <div className="space-y-2 max-h-48 overflow-auto">
          {sessions.slice(0, 10).map((session, index) => (
            <div
              key={`${session.sessionId}-${index}`}
              className="flex items-center justify-between py-2 px-3 bg-white/5 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {session.selectedContentId ? (
                  <CheckCircle className="w-4 h-4 text-green-400" />
                ) : session.abandoned ? (
                  <XCircle className="w-4 h-4 text-red-400" />
                ) : (
                  <Clock className="w-4 h-4 text-amber-400" />
                )}
                <span className="text-white/70 text-sm">
                  {new Date(session.querySubmittedAt).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-white/50">
                  {session.viewedCards} cards viewed
                </span>
                {session.decisionTimeMs && (
                  <span className="text-amber-400">
                    {formatTime(session.decisionTimeMs)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Clear Data */}
      <div className="flex justify-end">
        <button
          onClick={() => {
            if (confirm('Clear all analytics data?')) {
              clearMetrics();
            }
          }}
          className="text-red-400/70 hover:text-red-400 text-sm"
        >
          Clear Analytics Data
        </button>
      </div>
    </div>
  );
}

// ========== Advanced Metrics Tab ==========
function AdvancedMetricsTab({ 
  systemMetrics, 
  realtimeMetrics 
}: {
  systemMetrics: SystemMetrics | null;
  realtimeMetrics: RealtimeMetrics | null;
}) {
  const loadDemoData = async () => {
    try {
      const res = await fetch('http://localhost:8888/api/metrics/seed-demo', { method: 'POST' });
      if (res.ok) {
        window.location.reload();
      }
    } catch (error) {
      console.error('Failed to load demo data:', error);
    }
  };

  if (!systemMetrics || systemMetrics.total_sessions === 0) {
    return (
      <div className="p-12 text-center">
        <Target className="w-16 h-16 text-white/20 mx-auto mb-4" />
        <h3 className="text-white/70 text-lg mb-2">No Metrics Yet</h3>
        <p className="text-white/40 text-sm mb-6">
          Complete some recommendation sessions to generate metrics
        </p>
        <button
          onClick={loadDemoData}
          className="px-6 py-3 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 rounded-lg text-amber-400 font-medium transition-colors"
        >
          Load Demo Data
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Advanced Metrics Header */}
      <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-xl p-4 border border-cyan-500/20">
        <h3 className="text-cyan-400 font-medium mb-1 flex items-center gap-2">
          <Shield className="w-4 h-4" />
          Advanced AI Metrics
        </h3>
        <p className="text-white/50 text-sm">
          Core metrics from the AI-driven sequential narrative recommendation system
        </p>
      </div>

      {/* CCR Metrics - Commit Conversion Rate */}
      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
        <h4 className="text-white font-medium mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-amber-400" />
          CCR - Commit Conversion Rate
        </h4>
        <p className="text-white/40 text-xs mb-4">
          % of sessions with commit event by N-th NRU
        </p>
        <div className="grid grid-cols-3 gap-4">
          <CCRGauge label="By 3rd NRU" value={systemMetrics.ccr_3} target={0.5} />
          <CCRGauge label="By 5th NRU" value={systemMetrics.ccr_5} target={0.7} />
          <CCRGauge label="By 7th NRU" value={systemMetrics.ccr_7} target={0.85} />
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <AdvancedMetricCard
          icon={<Clock className="w-5 h-5" />}
          label="DLR"
          fullName="Decision Latency Reduction"
          value={`${(systemMetrics.dlr * 100).toFixed(1)}%`}
          description="(T_baseline - T_system) / T_baseline"
          color="amber"
          good={systemMetrics.dlr > 0.2}
        />
        <AdvancedMetricCard
          icon={<Gauge className="w-5 h-5" />}
          label="DI"
          fullName="Deferral Index"
          value={`${(systemMetrics.di * 100).toFixed(1)}%`}
          description="T_browse / T_total"
          color="purple"
          good={systemMetrics.di < 0.5}
        />
        <AdvancedMetricCard
          icon={<Brain className="w-5 h-5" />}
          label="SRR"
          fullName="Stress Reduction Ratio"
          value={`${(systemMetrics.srr * 100).toFixed(1)}%`}
          description="(S_baseline - S_system) / S_baseline"
          color="green"
          good={systemMetrics.srr > 0.1}
        />
        <AdvancedMetricCard
          icon={<Zap className="w-5 h-5" />}
          label="CTA"
          fullName="Confidence Trigger Accuracy"
          value={`${(systemMetrics.cta * 100).toFixed(1)}%`}
          description="commits w/o quick-cancel / triggers"
          color="cyan"
          good={systemMetrics.cta > 0.8}
        />
        <AdvancedMetricCard
          icon={<Sparkles className="w-5 h-5" />}
          label="DE"
          fullName="Diversity Exposure"
          value={`${(systemMetrics.de * 100).toFixed(1)}%`}
          description="-Σ p(g)·log(p(g)) normalized"
          color="pink"
          good={systemMetrics.de > 0.5}
        />
        <AdvancedMetricCard
          icon={<Target className="w-5 h-5" />}
          label="ECE"
          fullName="Expected Calibration Error"
          value={`${(systemMetrics.ece * 100).toFixed(1)}%`}
          description="Σ (n_b/N)|acc_b - conf_b|"
          color="red"
          good={systemMetrics.ece < 0.1}
        />
      </div>

      {/* Session Counts */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white/5 rounded-xl p-4 border border-white/10 text-center">
          <div className="text-3xl font-bold text-white">{systemMetrics.total_sessions}</div>
          <div className="text-white/50 text-sm">Total Sessions</div>
        </div>
        <div className="bg-green-500/10 rounded-xl p-4 border border-green-500/20 text-center">
          <div className="text-3xl font-bold text-green-400">{systemMetrics.committed_sessions}</div>
          <div className="text-white/50 text-sm">Committed</div>
        </div>
        <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20 text-center">
          <div className="text-3xl font-bold text-red-400">{systemMetrics.abandoned_sessions}</div>
          <div className="text-white/50 text-sm">Abandoned</div>
        </div>
      </div>

      {/* Trigger Quality */}
      {realtimeMetrics?.trigger_quality && (
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <h4 className="text-white font-medium mb-4">Trigger Quality</h4>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">
                {realtimeMetrics.trigger_quality.total_triggers}
              </div>
              <div className="text-white/50 text-xs">Total Triggers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {realtimeMetrics.trigger_quality.successful_commits}
              </div>
              <div className="text-white/50 text-xs">Successful</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">
                {realtimeMetrics.trigger_quality.quick_cancels}
              </div>
              <div className="text-white/50 text-xs">Quick Cancels</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400">
                {(realtimeMetrics.trigger_quality.accuracy * 100).toFixed(0)}%
              </div>
              <div className="text-white/50 text-xs">Accuracy</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ========== Calibration Tab ==========
function CalibrationTab({ 
  calibrationStats, 
}: {
  calibrationStats: CalibrationStats | null;
  realtimeMetrics?: RealtimeMetrics | null;
}) {
  if (!calibrationStats) {
    return (
      <div className="p-12 text-center">
        <Gauge className="w-16 h-16 text-white/20 mx-auto mb-4" />
        <h3 className="text-white/70 text-lg mb-2">No Calibration Data Yet</h3>
        <p className="text-white/40 text-sm">
          The confidence calibrator needs more data points
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Calibration Header */}
      <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-xl p-4 border border-purple-500/20">
        <h3 className="text-purple-400 font-medium mb-1 flex items-center gap-2">
          <Gauge className="w-4 h-4" />
          Confidence Calibration (Isotonic Regression)
        </h3>
        <p className="text-white/50 text-sm">
          C_cal = f_iso(C_raw) - Post-hoc calibration for reliable confidence scores
        </p>
      </div>

      {/* Calibration Status */}
      <div className="grid grid-cols-3 gap-4">
        <div className={`rounded-xl p-4 border ${
          calibrationStats.is_calibrator_fitted 
            ? 'bg-green-500/10 border-green-500/20' 
            : 'bg-amber-500/10 border-amber-500/20'
        }`}>
          <div className="text-2xl font-bold text-white">
            {calibrationStats.is_calibrator_fitted ? '✓' : '○'}
          </div>
          <div className="text-white/50 text-sm">
            {calibrationStats.is_calibrator_fitted ? 'Calibrator Fitted' : 'Not Yet Fitted'}
          </div>
        </div>
        <div className="bg-white/5 rounded-xl p-4 border border-white/10">
          <div className="text-2xl font-bold text-white">
            {calibrationStats.num_calibration_points}
          </div>
          <div className="text-white/50 text-sm">Calibration Points</div>
        </div>
        <div className={`rounded-xl p-4 border ${
          calibrationStats.ece < 0.1 
            ? 'bg-green-500/10 border-green-500/20' 
            : calibrationStats.ece < 0.2 
              ? 'bg-amber-500/10 border-amber-500/20'
              : 'bg-red-500/10 border-red-500/20'
        }`}>
          <div className="text-2xl font-bold text-white">
            {(calibrationStats.ece * 100).toFixed(1)}%
          </div>
          <div className="text-white/50 text-sm">ECE (Lower is Better)</div>
        </div>
      </div>

      {/* Reliability Diagram */}
      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
        <h4 className="text-white font-medium mb-4">Reliability Diagram</h4>
        <p className="text-white/40 text-xs mb-4">
          Predicted confidence vs actual accuracy per bin
        </p>
        <div className="relative h-64">
          {/* Perfect calibration line */}
          <div className="absolute inset-0">
            <svg className="w-full h-full">
              <line 
                x1="0" y1="100%" x2="100%" y2="0" 
                stroke="rgba(255,255,255,0.2)" 
                strokeDasharray="4"
              />
            </svg>
          </div>
          
          {/* Bins */}
          <div className="absolute inset-0 flex items-end justify-around">
            {calibrationStats.bins.map((bin, i) => {
              const height = bin.accuracy * 100;
              const confidenceHeight = bin.mean_confidence * 100;
              
              return (
                <div key={i} className="flex flex-col items-center w-full max-w-12">
                  {/* Accuracy bar */}
                  <div 
                    className="w-8 bg-amber-500/50 rounded-t relative group"
                    style={{ height: `${height}%`, minHeight: '4px' }}
                  >
                    {/* Confidence marker */}
                    <div 
                      className="absolute w-full h-1 bg-cyan-400"
                      style={{ bottom: `${confidenceHeight}%` }}
                    />
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-white/50 opacity-0 group-hover:opacity-100 whitespace-nowrap">
                      {(bin.accuracy * 100).toFixed(0)}% / {(bin.mean_confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="text-xs text-white/30 mt-1">{bin.count}</div>
                </div>
              );
            })}
          </div>
        </div>
        <div className="flex justify-center gap-6 mt-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-amber-500/50 rounded" />
            <span className="text-white/50">Actual Accuracy</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-1 bg-cyan-400 rounded" />
            <span className="text-white/50">Mean Confidence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-white/20" style={{ borderStyle: 'dashed' }} />
            <span className="text-white/50">Perfect Calibration</span>
          </div>
        </div>
      </div>

      {/* Bin Details */}
      <div className="bg-white/5 rounded-xl p-4 border border-white/10 overflow-auto">
        <h4 className="text-white font-medium mb-4">Calibration Bins Detail</h4>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-white/50 text-left">
              <th className="pb-2">Bin</th>
              <th className="pb-2">Samples</th>
              <th className="pb-2">Mean Confidence</th>
              <th className="pb-2">Actual Accuracy</th>
              <th className="pb-2">Gap</th>
            </tr>
          </thead>
          <tbody>
            {calibrationStats.bins.map((bin, idx) => {
              const gap = Math.abs(bin.mean_confidence - bin.accuracy);
              return (
                <tr key={idx} className="text-white/70 border-t border-white/5">
                  <td className="py-2">{idx + 1}</td>
                  <td>{bin.count}</td>
                  <td>{(bin.mean_confidence * 100).toFixed(1)}%</td>
                  <td>{(bin.accuracy * 100).toFixed(1)}%</td>
                  <td className={gap > 0.15 ? 'text-red-400' : gap > 0.1 ? 'text-amber-400' : 'text-green-400'}>
                    {(gap * 100).toFixed(1)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ========== Helper Components ==========

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'blue' | 'amber' | 'green' | 'red' | 'purple' | 'teal' | 'cyan' | 'pink';
  subtitle?: string;
}

function MetricCard({ icon, label, value, color, subtitle }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400',
    amber: 'bg-amber-500/20 text-amber-400',
    green: 'bg-green-500/20 text-green-400',
    red: 'bg-red-500/20 text-red-400',
    purple: 'bg-purple-500/20 text-purple-400',
    teal: 'bg-teal-500/20 text-teal-400',
    cyan: 'bg-cyan-500/20 text-cyan-400',
    pink: 'bg-pink-500/20 text-pink-400',
  };

  return (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10">
      <div className={`inline-flex p-2 rounded-lg ${colorClasses[color]} mb-3`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-white/50 text-sm">{label}</div>
      {subtitle && <div className="text-white/30 text-xs mt-1">{subtitle}</div>}
    </div>
  );
}

interface AdvancedMetricCardProps {
  icon: React.ReactNode;
  label: string;
  fullName: string;
  value: string;
  description: string;
  color: 'blue' | 'amber' | 'green' | 'red' | 'purple' | 'teal' | 'cyan' | 'pink';
  good: boolean;
}

function AdvancedMetricCard({ icon, label, fullName, value, description, color, good }: AdvancedMetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/20',
    amber: 'bg-amber-500/20 text-amber-400 border-amber-500/20',
    green: 'bg-green-500/20 text-green-400 border-green-500/20',
    red: 'bg-red-500/20 text-red-400 border-red-500/20',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/20',
    teal: 'bg-teal-500/20 text-teal-400 border-teal-500/20',
    cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/20',
    pink: 'bg-pink-500/20 text-pink-400 border-pink-500/20',
  };

  return (
    <div className={`rounded-xl p-4 border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`inline-flex p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        {good ? (
          <CheckCircle className="w-4 h-4 text-green-400" />
        ) : (
          <XCircle className="w-4 h-4 text-red-400" />
        )}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      <div className="text-white font-medium text-sm">{label}</div>
      <div className="text-white/50 text-xs">{fullName}</div>
      <div className="text-white/30 text-xs mt-2 font-mono">{description}</div>
    </div>
  );
}

function CCRGauge({ label, value, target }: { label: string; value: number; target: number }) {
  const percentage = value * 100;
  const isGood = value >= target;
  
  return (
    <div className="text-center">
      <div className="relative w-24 h-24 mx-auto">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="8"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke={isGood ? '#34d399' : '#fbbf24'}
            strokeWidth="8"
            strokeDasharray={`${percentage * 2.51} 251`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xl font-bold ${isGood ? 'text-green-400' : 'text-amber-400'}`}>
            {percentage.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="text-white/70 text-sm mt-2">{label}</div>
      <div className="text-white/30 text-xs">Target: {(target * 100).toFixed(0)}%</div>
    </div>
  );
}

function formatTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}
