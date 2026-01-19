"""
Commitment Trigger Logic

Implements patent specification sections 6.3-6.4:
- Three-way gate: C_cal > τ(x) AND t_expose > t_min AND σ(x) < σ_max
- Quick Cancel detection within 30-second window
- Post-trigger validation and learning signal
"""

import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from app.models import DecisionState, EnhancedDecisionState
from app.services.confidence_calibrator import (
    confidence_estimator,
    ConfidenceEstimate
)


class TriggerResult(Enum):
    """Possible outcomes of commitment trigger evaluation"""
    TRIGGERED = "triggered"  # All conditions met
    CONFIDENCE_LOW = "confidence_low"  # C_cal < τ(x)
    EXPOSURE_SHORT = "exposure_short"  # t < t_min
    UNCERTAINTY_HIGH = "uncertainty_high"  # σ > σ_max
    MULTIPLE_FAILURES = "multiple_failures"  # Multiple conditions failed


@dataclass
class TriggerEvaluation:
    """Result of commitment trigger evaluation"""
    should_trigger: bool
    result: TriggerResult
    
    # Individual gate values
    calibrated_confidence: float
    dynamic_threshold: float
    exposure_time: float
    min_exposure_time: float
    uncertainty: float
    max_uncertainty: float
    
    # Metadata
    timestamp: float
    content_id: str
    user_id: str
    
    # For learning
    trigger_id: Optional[str] = None


@dataclass  
class QuickCancelEvent:
    """Tracks a quick cancel for learning"""
    trigger_id: str
    trigger_timestamp: float
    cancel_timestamp: float
    content_id: str
    user_id: str
    time_to_cancel: float  # seconds
    
    @property
    def is_quick_cancel(self) -> bool:
        return self.time_to_cancel < 30.0


@dataclass
class TriggerStats:
    """Statistics for trigger quality monitoring"""
    total_triggers: int = 0
    successful_commits: int = 0
    quick_cancels: int = 0
    
    @property
    def accuracy(self) -> float:
        if self.total_triggers == 0:
            return 0.0
        return self.successful_commits / self.total_triggers
    
    @property
    def quick_cancel_rate(self) -> float:
        if self.total_triggers == 0:
            return 0.0
        return self.quick_cancels / self.total_triggers


class CommitmentTrigger:
    """
    Commitment Trigger with Three-Way Gate and Quick Cancel Detection
    
    The trigger fires when ALL conditions are met:
    1. C_cal(t|x) > τ(x) - Calibrated confidence exceeds dynamic threshold
    2. t_expose > t_min - Minimum exposure time has elapsed
    3. σ(x) < σ_max - Uncertainty is below safety threshold
    
    This cascaded guardrail approach prevents:
    - Premature commits (exposure time gate)
    - Low-confidence commits (confidence gate)
    - Uncertain commits (uncertainty gate)
    """
    
    # Gate parameters
    MIN_EXPOSURE_TIME = 3.0  # seconds - minimum time on content
    MAX_UNCERTAINTY = 0.7  # σ_max - uncertainty guardrail
    QUICK_CANCEL_WINDOW = 30.0  # seconds to detect quick cancel
    
    def __init__(self):
        # Track pending triggers for quick cancel detection
        self._pending_triggers: Dict[str, TriggerEvaluation] = {}
        
        # Quick cancel history for learning
        self._quick_cancels: deque = deque(maxlen=1000)
        
        # Statistics
        self.stats = TriggerStats()
        
        # Counter for trigger IDs
        self._trigger_counter = 0
    
    def _generate_trigger_id(self) -> str:
        """Generate unique trigger ID"""
        self._trigger_counter += 1
        return f"trigger_{int(time.time())}_{self._trigger_counter}"
    
    def evaluate_trigger(
        self,
        decision_state: DecisionState,
        exposure_time: float,
        time_in_session: float,
        content_id: str,
        user_id: str,
        recent_interactions: Optional[List[Dict]] = None
    ) -> TriggerEvaluation:
        """
        Evaluate whether commitment should be triggered.
        
        Three-way gate:
        1. Confidence gate: C_cal > τ(x)
        2. Exposure gate: t_expose > t_min
        3. Uncertainty gate: σ(x) < σ_max
        """
        # Get confidence estimate
        conf_estimate = confidence_estimator.estimate_confidence(
            decision_state,
            time_in_session,
            recent_interactions
        )
        
        # Get uncertainty
        uncertainty = getattr(decision_state, 'epistemic_uncertainty', 0.3)
        
        # Evaluate gates
        confidence_gate = conf_estimate.calibrated_confidence > conf_estimate.dynamic_threshold
        exposure_gate = exposure_time >= self.MIN_EXPOSURE_TIME
        uncertainty_gate = uncertainty < self.MAX_UNCERTAINTY
        
        # Determine result
        should_trigger = confidence_gate and exposure_gate and uncertainty_gate
        
        if should_trigger:
            result = TriggerResult.TRIGGERED
        elif not confidence_gate and not exposure_gate:
            result = TriggerResult.MULTIPLE_FAILURES
        elif not confidence_gate:
            result = TriggerResult.CONFIDENCE_LOW
        elif not exposure_gate:
            result = TriggerResult.EXPOSURE_SHORT
        else:
            result = TriggerResult.UNCERTAINTY_HIGH
        
        # Create evaluation
        evaluation = TriggerEvaluation(
            should_trigger=should_trigger,
            result=result,
            calibrated_confidence=conf_estimate.calibrated_confidence,
            dynamic_threshold=conf_estimate.dynamic_threshold,
            exposure_time=exposure_time,
            min_exposure_time=self.MIN_EXPOSURE_TIME,
            uncertainty=uncertainty,
            max_uncertainty=self.MAX_UNCERTAINTY,
            timestamp=time.time(),
            content_id=content_id,
            user_id=user_id
        )
        
        # If triggered, track for quick cancel detection
        if should_trigger:
            evaluation.trigger_id = self._generate_trigger_id()
            self._pending_triggers[evaluation.trigger_id] = evaluation
            self.stats.total_triggers += 1
        
        return evaluation
    
    def report_commit_success(self, trigger_id: str) -> bool:
        """
        Report that a triggered commit was successful (not cancelled).
        Called after the quick cancel window expires.
        """
        if trigger_id in self._pending_triggers:
            evaluation = self._pending_triggers.pop(trigger_id)
            self.stats.successful_commits += 1
            
            # Record positive outcome for calibration
            conf_estimate = ConfidenceEstimate(
                raw_confidence=evaluation.calibrated_confidence,
                calibrated_confidence=evaluation.calibrated_confidence,
                dynamic_threshold=evaluation.dynamic_threshold,
                exceeds_threshold=True,
                ece_contribution=0,
                observation_window_seconds=10
            )
            confidence_estimator.record_outcome(conf_estimate, committed=True)
            
            return True
        return False
    
    def report_quick_cancel(
        self,
        trigger_id: str,
        cancel_timestamp: Optional[float] = None
    ) -> Optional[QuickCancelEvent]:
        """
        Report that a triggered commit was quickly cancelled.
        This is a negative learning signal.
        
        q(i) = -1 if quick_cancel else 0
        """
        if trigger_id not in self._pending_triggers:
            return None
        
        evaluation = self._pending_triggers.pop(trigger_id)
        cancel_time = cancel_timestamp or time.time()
        time_to_cancel = cancel_time - evaluation.timestamp
        
        # Create quick cancel event
        event = QuickCancelEvent(
            trigger_id=trigger_id,
            trigger_timestamp=evaluation.timestamp,
            cancel_timestamp=cancel_time,
            content_id=evaluation.content_id,
            user_id=evaluation.user_id,
            time_to_cancel=time_to_cancel
        )
        
        if event.is_quick_cancel:
            self._quick_cancels.append(event)
            self.stats.quick_cancels += 1
            
            # Record negative outcome for calibration
            conf_estimate = ConfidenceEstimate(
                raw_confidence=evaluation.calibrated_confidence,
                calibrated_confidence=evaluation.calibrated_confidence,
                dynamic_threshold=evaluation.dynamic_threshold,
                exceeds_threshold=True,
                ece_contribution=0,
                observation_window_seconds=10
            )
            confidence_estimator.record_outcome(conf_estimate, committed=False)
        
        return event
    
    def report_abandonment(
        self,
        user_id: str,
        content_id: str
    ):
        """
        Report that user abandoned without committing.
        Used for learning even when no trigger fired.
        """
        # Find any pending triggers for this user/content
        to_remove = []
        for tid, eval in self._pending_triggers.items():
            if eval.user_id == user_id and eval.content_id == content_id:
                to_remove.append(tid)
        
        for tid in to_remove:
            self._pending_triggers.pop(tid)
    
    def cleanup_expired_triggers(self):
        """Remove triggers past the quick cancel window"""
        current_time = time.time()
        expired = [
            tid for tid, eval in self._pending_triggers.items()
            if current_time - eval.timestamp > self.QUICK_CANCEL_WINDOW * 2
        ]
        
        for tid in expired:
            # Treat as successful if not cancelled within window
            self.report_commit_success(tid)
    
    def get_trigger_quality(self) -> Dict:
        """Get trigger quality metrics"""
        return {
            "total_triggers": self.stats.total_triggers,
            "successful_commits": self.stats.successful_commits,
            "quick_cancels": self.stats.quick_cancels,
            "accuracy": self.stats.accuracy,
            "quick_cancel_rate": self.stats.quick_cancel_rate,
            "pending_triggers": len(self._pending_triggers),
            "confidence_calibration": confidence_estimator.get_calibration_stats()
        }
    
    def get_recommended_action(
        self,
        evaluation: TriggerEvaluation
    ) -> Dict:
        """
        Get recommended action based on trigger evaluation.
        Useful for frontend to know what to do.
        """
        if evaluation.should_trigger:
            return {
                "action": "commit",
                "message": "Ready to play! High confidence match.",
                "auto_play": True
            }
        
        if evaluation.result == TriggerResult.EXPOSURE_SHORT:
            remaining = self.MIN_EXPOSURE_TIME - evaluation.exposure_time
            return {
                "action": "wait",
                "message": f"Taking a moment to consider...",
                "wait_seconds": remaining
            }
        
        if evaluation.result == TriggerResult.CONFIDENCE_LOW:
            gap = evaluation.dynamic_threshold - evaluation.calibrated_confidence
            return {
                "action": "continue",
                "message": "Still exploring options...",
                "confidence_gap": gap
            }
        
        if evaluation.result == TriggerResult.UNCERTAINTY_HIGH:
            return {
                "action": "clarify",
                "message": "Would you like me to narrow down the options?",
                "uncertainty": evaluation.uncertainty
            }
        
        return {
            "action": "continue",
            "message": "Keep browsing..."
        }


# Singleton instance
commitment_trigger = CommitmentTrigger()
