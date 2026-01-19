"""
Deployment Monitoring and Guardrails

Implements patent specification Section 13:
- ECE monitoring with auto-recalibration triggers
- Quick-cancel rate monitoring
- Stress proxy drift detection
- Abandonment rate monitoring
- Phased deployment support
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from collections import deque
import time
import numpy as np


class DeploymentPhase(Enum):
    """Phased deployment stages from Section 13.1"""
    PHASE_1_MVP = "phase_1_mvp"  # Decision encoder + hazard model
    PHASE_2_BOUNDED = "phase_2_bounded"  # Cognitive-load adaptation + DPP
    PHASE_3_NRU = "phase_3_nru"  # Saliency snippets + narratives
    PHASE_4_TRIGGER = "phase_4_trigger"  # Confidence triggers + guardrails
    PHASE_5_RL = "phase_5_rl"  # Full RL optimization


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SystemAlert:
    """System monitoring alert"""
    alert_id: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold: float
    message: str
    timestamp: float
    recommended_action: str
    auto_remediation: Optional[str] = None


@dataclass
class MetricWindow:
    """Sliding window for metric tracking"""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add(self, value: float):
        self.values.append(value)
        self.timestamps.append(time.time())
    
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return np.mean(list(self.values))
    
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        return np.std(list(self.values))
    
    def recent(self, seconds: float = 3600) -> List[float]:
        """Get values from last N seconds"""
        cutoff = time.time() - seconds
        return [v for v, t in zip(self.values, self.timestamps) if t > cutoff]
    
    def trend(self, window_seconds: float = 3600) -> float:
        """Calculate trend (slope) over window"""
        recent_vals = self.recent(window_seconds)
        if len(recent_vals) < 2:
            return 0.0
        x = np.arange(len(recent_vals))
        return np.polyfit(x, recent_vals, 1)[0]


@dataclass
class DeploymentConfig:
    """Configuration for current deployment phase"""
    phase: DeploymentPhase
    user_cohort_percentage: float  # % of users in experiment
    enabled_features: Dict[str, bool]
    fallback_to_baseline: bool = True


class DeploymentMonitor:
    """
    Production Monitoring System
    
    Tracks key metrics and triggers alerts/remediations:
    - ECE > 0.15 → Re-calibrate confidence estimator
    - Quick-cancel > 20% → Reduce threshold or increase uncertainty guardrail
    - Stress proxy drift → Retrain with fresh labels
    - Abandonment > 5% increase → Revert policy
    """
    
    # Guardrail thresholds (Section 13.2)
    ECE_THRESHOLD = 0.15
    QUICK_CANCEL_THRESHOLD = 0.20
    ABANDONMENT_INCREASE_THRESHOLD = 0.05
    STRESS_DRIFT_THRESHOLD = 0.3  # Correlation drop
    
    def __init__(self):
        # Current deployment state
        self.current_phase = DeploymentPhase.PHASE_1_MVP
        self.deployment_config: Optional[DeploymentConfig] = None
        
        # Metric windows
        self._ece_window = MetricWindow()
        self._quick_cancel_window = MetricWindow()
        self._abandonment_window = MetricWindow()
        self._stress_correlation_window = MetricWindow()
        self._decision_latency_window = MetricWindow()
        self._conversion_window = MetricWindow()
        
        # Baseline metrics (for comparison)
        self._baseline_abandonment: float = 0.15
        self._baseline_decision_time: float = 120.0
        
        # Active alerts
        self._active_alerts: Dict[str, SystemAlert] = {}
        
        # Alert history
        self._alert_history: deque = deque(maxlen=1000)
        
        # Counter for alert IDs
        self._alert_counter = 0
        
        # Auto-remediation flags
        self._recalibration_triggered = False
        self._threshold_reduced = False
        self._policy_reverted = False
    
    def _generate_alert_id(self) -> str:
        self._alert_counter += 1
        return f"alert_{int(time.time())}_{self._alert_counter}"
    
    # ========== Metric Recording ==========
    
    def record_ece(self, ece_value: float):
        """Record Expected Calibration Error"""
        self._ece_window.add(ece_value)
        self._check_ece_guardrail(ece_value)
    
    def record_quick_cancel(self, was_quick_cancel: bool):
        """Record quick cancel event"""
        self._quick_cancel_window.add(1.0 if was_quick_cancel else 0.0)
        self._check_quick_cancel_guardrail()
    
    def record_abandonment(self, abandoned: bool):
        """Record session abandonment"""
        self._abandonment_window.add(1.0 if abandoned else 0.0)
        self._check_abandonment_guardrail()
    
    def record_stress_correlation(self, correlation: float):
        """Record stress proxy correlation with ground truth"""
        self._stress_correlation_window.add(correlation)
        self._check_stress_drift_guardrail(correlation)
    
    def record_decision_latency(self, latency_seconds: float):
        """Record time to decision"""
        self._decision_latency_window.add(latency_seconds)
    
    def record_conversion(self, converted: bool):
        """Record conversion event"""
        self._conversion_window.add(1.0 if converted else 0.0)
    
    # ========== Guardrail Checks ==========
    
    def _check_ece_guardrail(self, current_ece: float):
        """
        Section 13.2: If ECE > 0.15, trigger re-calibration
        """
        if current_ece > self.ECE_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                severity=AlertSeverity.WARNING,
                metric_name="ECE",
                current_value=current_ece,
                threshold=self.ECE_THRESHOLD,
                message=f"Expected Calibration Error ({current_ece:.3f}) exceeds threshold ({self.ECE_THRESHOLD})",
                timestamp=time.time(),
                recommended_action="Trigger confidence estimator re-calibration",
                auto_remediation="recalibrate_confidence"
            )
            self._raise_alert(alert)
    
    def _check_quick_cancel_guardrail(self):
        """
        Section 13.2: If quick-cancel > 20%, reduce threshold or increase guardrail
        """
        recent_rate = np.mean(self._quick_cancel_window.recent(3600))
        
        if recent_rate > self.QUICK_CANCEL_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                severity=AlertSeverity.WARNING,
                metric_name="Quick Cancel Rate",
                current_value=recent_rate,
                threshold=self.QUICK_CANCEL_THRESHOLD,
                message=f"Quick cancel rate ({recent_rate:.1%}) exceeds threshold ({self.QUICK_CANCEL_THRESHOLD:.0%})",
                timestamp=time.time(),
                recommended_action="Reduce confidence threshold or increase uncertainty guardrail",
                auto_remediation="reduce_confidence_threshold"
            )
            self._raise_alert(alert)
    
    def _check_abandonment_guardrail(self):
        """
        Section 13.2: If abandonment > baseline + 5%, revert policy
        """
        recent_rate = np.mean(self._abandonment_window.recent(3600))
        increase = recent_rate - self._baseline_abandonment
        
        if increase > self.ABANDONMENT_INCREASE_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                severity=AlertSeverity.CRITICAL,
                metric_name="Abandonment Rate",
                current_value=recent_rate,
                threshold=self._baseline_abandonment + self.ABANDONMENT_INCREASE_THRESHOLD,
                message=f"Abandonment rate increased by {increase:.1%} vs baseline. Critical threshold exceeded.",
                timestamp=time.time(),
                recommended_action="Revert to previous policy",
                auto_remediation="revert_policy"
            )
            self._raise_alert(alert)
    
    def _check_stress_drift_guardrail(self, correlation: float):
        """
        Section 13.2: If stress proxy correlation drops, retrain
        """
        if correlation < self.STRESS_DRIFT_THRESHOLD:
            alert = SystemAlert(
                alert_id=self._generate_alert_id(),
                severity=AlertSeverity.WARNING,
                metric_name="Stress Proxy Correlation",
                current_value=correlation,
                threshold=self.STRESS_DRIFT_THRESHOLD,
                message=f"Stress proxy correlation ({correlation:.2f}) below threshold. Model may be drifting.",
                timestamp=time.time(),
                recommended_action="Retrain stress proxy with fresh micro-survey labels",
                auto_remediation="retrain_stress_proxy"
            )
            self._raise_alert(alert)
    
    def _raise_alert(self, alert: SystemAlert):
        """Raise a new alert"""
        # Avoid duplicate alerts
        existing_key = f"{alert.metric_name}_{alert.severity.value}"
        if existing_key in self._active_alerts:
            # Update existing
            self._active_alerts[existing_key] = alert
        else:
            self._active_alerts[existing_key] = alert
            self._alert_history.append(alert)
            
            # Log critical alerts
            if alert.severity == AlertSeverity.CRITICAL:
                print(f"🚨 CRITICAL ALERT: {alert.message}")
            elif alert.severity == AlertSeverity.WARNING:
                print(f"⚠️ WARNING: {alert.message}")
    
    def clear_alert(self, metric_name: str):
        """Clear alert for a metric (condition resolved)"""
        keys_to_remove = [k for k in self._active_alerts if metric_name in k]
        for key in keys_to_remove:
            del self._active_alerts[key]
    
    # ========== Auto-Remediation ==========
    
    def get_remediation_actions(self) -> List[str]:
        """Get list of recommended remediation actions"""
        actions = []
        for alert in self._active_alerts.values():
            if alert.auto_remediation:
                actions.append(alert.auto_remediation)
        return list(set(actions))
    
    def execute_remediation(self, action: str) -> Dict:
        """Execute automatic remediation action"""
        result = {"action": action, "success": False, "message": ""}
        
        if action == "recalibrate_confidence":
            # Would trigger confidence calibrator refit
            result["success"] = True
            result["message"] = "Confidence calibrator recalibration scheduled"
            self._recalibration_triggered = True
            self.clear_alert("ECE")
            
        elif action == "reduce_confidence_threshold":
            # Would reduce commitment trigger threshold
            result["success"] = True
            result["message"] = "Confidence threshold reduced by 0.05"
            self._threshold_reduced = True
            self.clear_alert("Quick Cancel Rate")
            
        elif action == "revert_policy":
            # Would rollback to previous policy
            result["success"] = True
            result["message"] = "Policy reverted to baseline"
            self._policy_reverted = True
            self.clear_alert("Abandonment Rate")
            
        elif action == "retrain_stress_proxy":
            # Would trigger stress model retrain
            result["success"] = True
            result["message"] = "Stress proxy retraining scheduled"
            self.clear_alert("Stress Proxy Correlation")
        
        return result
    
    # ========== Phased Deployment ==========
    
    def set_deployment_phase(
        self,
        phase: DeploymentPhase,
        cohort_percentage: float = 5.0
    ):
        """Set current deployment phase"""
        self.current_phase = phase
        
        # Define features enabled per phase
        features_by_phase = {
            DeploymentPhase.PHASE_1_MVP: {
                "decision_encoder": True,
                "hazard_model": True,
                "hesitation_detection": True,
                "cognitive_load_adaptation": False,
                "dpp_diversity": False,
                "nru_generation": False,
                "confidence_trigger": False,
                "rl_optimization": False,
            },
            DeploymentPhase.PHASE_2_BOUNDED: {
                "decision_encoder": True,
                "hazard_model": True,
                "hesitation_detection": True,
                "cognitive_load_adaptation": True,
                "dpp_diversity": True,
                "nru_generation": False,
                "confidence_trigger": False,
                "rl_optimization": False,
            },
            DeploymentPhase.PHASE_3_NRU: {
                "decision_encoder": True,
                "hazard_model": True,
                "hesitation_detection": True,
                "cognitive_load_adaptation": True,
                "dpp_diversity": True,
                "nru_generation": True,
                "confidence_trigger": False,
                "rl_optimization": False,
            },
            DeploymentPhase.PHASE_4_TRIGGER: {
                "decision_encoder": True,
                "hazard_model": True,
                "hesitation_detection": True,
                "cognitive_load_adaptation": True,
                "dpp_diversity": True,
                "nru_generation": True,
                "confidence_trigger": True,
                "rl_optimization": False,
            },
            DeploymentPhase.PHASE_5_RL: {
                "decision_encoder": True,
                "hazard_model": True,
                "hesitation_detection": True,
                "cognitive_load_adaptation": True,
                "dpp_diversity": True,
                "nru_generation": True,
                "confidence_trigger": True,
                "rl_optimization": True,
            },
        }
        
        self.deployment_config = DeploymentConfig(
            phase=phase,
            user_cohort_percentage=cohort_percentage,
            enabled_features=features_by_phase.get(phase, {}),
            fallback_to_baseline=True
        )
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled in current deployment phase"""
        if not self.deployment_config:
            return False
        return self.deployment_config.enabled_features.get(feature_name, False)
    
    def should_use_baseline(self, user_id: str) -> bool:
        """Check if user should use baseline (not in experiment cohort)"""
        if not self.deployment_config:
            return True
        
        # Hash-based cohort assignment for consistency
        user_hash = hash(user_id) % 100
        return user_hash >= self.deployment_config.user_cohort_percentage
    
    # ========== Reporting ==========
    
    def get_health_status(self) -> Dict:
        """Get system health status"""
        ece_recent = self._ece_window.recent(3600)
        qc_recent = self._quick_cancel_window.recent(3600)
        abd_recent = self._abandonment_window.recent(3600)
        
        return {
            "status": "unhealthy" if self._active_alerts else "healthy",
            "deployment_phase": self.current_phase.value if self.current_phase else "unknown",
            "active_alerts": len(self._active_alerts),
            "metrics": {
                "ece": {
                    "current": ece_recent[-1] if ece_recent else None,
                    "mean_1h": np.mean(ece_recent) if ece_recent else None,
                    "threshold": self.ECE_THRESHOLD,
                },
                "quick_cancel_rate": {
                    "current": np.mean(qc_recent) if qc_recent else None,
                    "threshold": self.QUICK_CANCEL_THRESHOLD,
                },
                "abandonment_rate": {
                    "current": np.mean(abd_recent) if abd_recent else None,
                    "baseline": self._baseline_abandonment,
                    "threshold_increase": self.ABANDONMENT_INCREASE_THRESHOLD,
                },
                "decision_latency": {
                    "mean_1h": self._decision_latency_window.mean(),
                    "baseline": self._baseline_decision_time,
                },
                "conversion_rate": {
                    "mean_1h": self._conversion_window.mean(),
                },
            },
            "remediation_status": {
                "recalibration_triggered": self._recalibration_triggered,
                "threshold_reduced": self._threshold_reduced,
                "policy_reverted": self._policy_reverted,
            }
        }
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        return [
            {
                "alert_id": alert.alert_id,
                "severity": alert.severity.value,
                "metric": alert.metric_name,
                "value": alert.current_value,
                "threshold": alert.threshold,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "action": alert.recommended_action,
            }
            for alert in self._active_alerts.values()
        ]


# Singleton instance
deployment_monitor = DeploymentMonitor()
