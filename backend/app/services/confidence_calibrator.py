"""
Confidence Estimation and Calibration Service

Implements patent specification sections 6.1-6.3:
- Confidence Estimator: C(t|x) = σ(w_c · φ(x_[t-Δ:t]) + b_c)
- Isotonic Regression Calibration: C_cal = f_iso(C_raw)
- Expected Calibration Error (ECE) tracking
- Dynamic Threshold: τ(x) = τ_base + λ_h·h(x) + λ_σ·σ(x) + λ_t·t
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field
from collections import deque
import time

from app.models import DecisionState, EnhancedDecisionState


@dataclass
class ConfidenceEstimate:
    """Output of confidence estimation"""
    raw_confidence: float  # C(t|x) before calibration
    calibrated_confidence: float  # C_cal after isotonic regression
    dynamic_threshold: float  # τ(x) state-dependent threshold
    exceeds_threshold: bool  # Whether C_cal > τ(x)
    ece_contribution: float  # This estimate's ECE contribution
    observation_window_seconds: float  # Δ used


@dataclass
class CalibrationBin:
    """Single bin for ECE computation"""
    predictions: List[float] = field(default_factory=list)
    outcomes: List[int] = field(default_factory=list)  # 1 = commit, 0 = no commit
    
    @property
    def accuracy(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(self.outcomes) / len(self.outcomes)
    
    @property
    def mean_confidence(self) -> float:
        if not self.predictions:
            return 0.0
        return sum(self.predictions) / len(self.predictions)
    
    @property
    def count(self) -> int:
        return len(self.predictions)


class IsotonicCalibrator:
    """
    Isotonic Regression Calibrator
    
    Learns a monotonically increasing function f_iso that maps
    raw confidence scores to calibrated probabilities.
    
    C_cal = f_iso(C_raw)
    
    This corrects for overconfident/underconfident neural network outputs.
    """
    
    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins
        # Piecewise linear isotonic function (learned boundaries)
        self.boundaries: List[float] = []
        self.calibrated_values: List[float] = []
        self._is_fitted = False
        
        # Calibration data
        self.calibration_data: List[Tuple[float, int]] = []
    
    def add_calibration_point(self, raw_confidence: float, outcome: int):
        """Add a (prediction, outcome) pair for calibration"""
        self.calibration_data.append((raw_confidence, outcome))
        
        # Fit when we have minimum data, then refit periodically
        n = len(self.calibration_data)
        if n >= 10:
            # Fit on first 10, then every 5 new points
            if not self._is_fitted or n % 5 == 0:
                self._fit()
    
    def fit(self):
        """Public method to fit the calibrator"""
        self._fit()
    
    def _fit(self):
        """Fit isotonic regression on calibration data"""
        if len(self.calibration_data) < 10:
            return
        
        # Sort by raw confidence
        sorted_data = sorted(self.calibration_data, key=lambda x: x[0])
        
        # Pool Adjacent Violators Algorithm (PAVA) for isotonic regression
        n = len(sorted_data)
        raw_scores = [d[0] for d in sorted_data]
        outcomes = [d[1] for d in sorted_data]
        
        # Initialize with actual outcomes
        calibrated = list(outcomes)
        weights = [1.0] * n
        
        # PAVA: enforce monotonicity
        i = 0
        while i < n - 1:
            if calibrated[i] > calibrated[i + 1]:
                # Pool adjacent violators
                j = i + 1
                while j < n and calibrated[j] <= calibrated[i]:
                    j += 1
                
                # Compute weighted average
                total_weight = sum(weights[i:j])
                pooled_value = sum(
                    calibrated[k] * weights[k] for k in range(i, j)
                ) / total_weight
                
                # Update values and weights
                for k in range(i, j):
                    calibrated[k] = pooled_value
                    weights[k] = total_weight
                
                # Check previous
                if i > 0:
                    i -= 1
                continue
            i += 1
        
        # Create piecewise linear function
        self.boundaries = []
        self.calibrated_values = []
        
        prev_raw = None
        for i, (raw, cal) in enumerate(zip(raw_scores, calibrated)):
            if prev_raw is None or raw != prev_raw:
                self.boundaries.append(raw)
                self.calibrated_values.append(cal)
                prev_raw = raw
        
        self._is_fitted = True
    
    def calibrate(self, raw_confidence: float) -> float:
        """Apply isotonic calibration to raw confidence"""
        if not self._is_fitted or not self.boundaries:
            return raw_confidence  # Return uncalibrated if not fitted
        
        # Binary search for position
        idx = 0
        for i, boundary in enumerate(self.boundaries):
            if raw_confidence >= boundary:
                idx = i
            else:
                break
        
        # Linear interpolation between adjacent points
        if idx >= len(self.calibrated_values) - 1:
            return self.calibrated_values[-1]
        
        # Interpolate
        x0, x1 = self.boundaries[idx], self.boundaries[idx + 1]
        y0, y1 = self.calibrated_values[idx], self.calibrated_values[idx + 1]
        
        if x1 == x0:
            return y0
        
        t = (raw_confidence - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)


class ConfidenceEstimator:
    """
    Confidence Estimator with Calibration and Dynamic Thresholding
    
    Patent specification section 6:
    - Estimates P(commit | current state)
    - Applies isotonic calibration
    - Computes state-dependent threshold
    - Tracks ECE for quality monitoring
    """
    
    # Feature weights (would be learned in production)
    W_DWELL = 0.3
    W_ENGAGEMENT = 0.25
    W_HESITATION = -0.35
    W_REPLAY = 0.15
    W_SKIP = -0.2
    
    # Dynamic threshold parameters
    TAU_BASE = 0.7  # Base threshold
    LAMBDA_H = 0.15  # Hesitation sensitivity
    LAMBDA_SIGMA = 0.1  # Uncertainty sensitivity  
    LAMBDA_T = 0.002  # Time sensitivity (per second)
    
    # Observation window
    OBSERVATION_WINDOW = 10.0  # seconds (Δ)
    
    def __init__(self, num_ece_bins: int = 10):
        self.calibrator = IsotonicCalibrator()
        self.num_ece_bins = num_ece_bins
        self.ece_bins: List[CalibrationBin] = [
            CalibrationBin() for _ in range(num_ece_bins)
        ]
        
        # Recent observations for windowed estimation
        self._observation_buffer: deque = deque(maxlen=100)
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _extract_features(
        self,
        decision_state: DecisionState,
        recent_interactions: List[Dict]
    ) -> np.ndarray:
        """
        Extract feature vector φ(x_[t-Δ:t]) from observation window
        """
        features = []
        
        # Dwell time feature (normalized)
        dwell_norm = min(decision_state.dwell_time / 30000, 1)
        features.append(dwell_norm)
        
        # Engagement (inverse of scroll velocity)
        scroll_norm = min(decision_state.scroll_velocity / 1000, 1)
        engagement = 1 - scroll_norm
        features.append(engagement)
        
        # Hesitation from decision state
        hesitation = getattr(decision_state, 'hesitation_score', 
                            decision_state.stress_level)
        features.append(hesitation)
        
        # Recent replays and skips
        replays = sum(1 for i in recent_interactions if i.get('type') == 'replay')
        skips = sum(1 for i in recent_interactions if i.get('type') == 'skip')
        
        features.append(min(replays / 3, 1))  # Normalize
        features.append(min(skips / 3, 1))
        
        return np.array(features)
    
    def estimate_raw_confidence(
        self,
        decision_state: DecisionState,
        recent_interactions: Optional[List[Dict]] = None
    ) -> float:
        """
        Estimate raw confidence C(t|x) = σ(w · φ(x) + b)
        """
        interactions = recent_interactions or []
        features = self._extract_features(decision_state, interactions)
        
        # Weights
        weights = np.array([
            self.W_DWELL,
            self.W_ENGAGEMENT,
            self.W_HESITATION,
            self.W_REPLAY,
            self.W_SKIP
        ])
        
        # Linear combination + bias
        logit = np.dot(weights, features) + 0.5  # Bias
        
        return self._sigmoid(logit)
    
    def compute_dynamic_threshold(
        self,
        decision_state: DecisionState,
        time_in_session: float
    ) -> float:
        """
        Compute state-dependent threshold:
        τ(x) = τ_base + λ_h·h(x) + λ_σ·σ(x) + λ_t·t
        
        - Higher threshold when user is hesitant (conservative)
        - Higher threshold when uncertainty is high
        - Slightly higher threshold over time (avoid premature commits)
        """
        hesitation = getattr(decision_state, 'hesitation_score',
                            decision_state.stress_level)
        uncertainty = getattr(decision_state, 'epistemic_uncertainty', 0.3)
        
        threshold = (
            self.TAU_BASE +
            self.LAMBDA_H * hesitation +
            self.LAMBDA_SIGMA * uncertainty +
            self.LAMBDA_T * min(time_in_session, 120)  # Cap at 2 min
        )
        
        return min(0.95, max(0.5, threshold))  # Clamp to reasonable range
    
    def estimate_confidence(
        self,
        decision_state: DecisionState,
        time_in_session: float,
        recent_interactions: Optional[List[Dict]] = None
    ) -> ConfidenceEstimate:
        """
        Full confidence estimation with calibration and thresholding
        """
        # Raw estimate
        raw_confidence = self.estimate_raw_confidence(
            decision_state, recent_interactions
        )
        
        # Calibrate
        calibrated = self.calibrator.calibrate(raw_confidence)
        
        # Dynamic threshold
        threshold = self.compute_dynamic_threshold(decision_state, time_in_session)
        
        # ECE contribution
        bin_idx = min(int(calibrated * self.num_ece_bins), self.num_ece_bins - 1)
        ece_contrib = abs(calibrated - self.ece_bins[bin_idx].accuracy) \
            if self.ece_bins[bin_idx].count > 0 else 0.0
        
        return ConfidenceEstimate(
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            dynamic_threshold=threshold,
            exceeds_threshold=calibrated > threshold,
            ece_contribution=ece_contrib,
            observation_window_seconds=self.OBSERVATION_WINDOW
        )
    
    def record_outcome(self, confidence_estimate: ConfidenceEstimate, committed: bool):
        """
        Record outcome for calibration learning
        """
        outcome = 1 if committed else 0
        
        # Add to calibrator
        self.calibrator.add_calibration_point(
            confidence_estimate.raw_confidence,
            outcome
        )
        
        # Add to ECE bins
        bin_idx = min(
            int(confidence_estimate.calibrated_confidence * self.num_ece_bins),
            self.num_ece_bins - 1
        )
        self.ece_bins[bin_idx].predictions.append(
            confidence_estimate.calibrated_confidence
        )
        self.ece_bins[bin_idx].outcomes.append(outcome)
    
    def compute_ece(self) -> float:
        """
        Compute Expected Calibration Error:
        ECE = Σ (n_b/N) |accuracy_b - confidence_b|
        """
        total_samples = sum(bin.count for bin in self.ece_bins)
        if total_samples == 0:
            return 0.0
        
        ece = 0.0
        for bin in self.ece_bins:
            if bin.count > 0:
                weight = bin.count / total_samples
                error = abs(bin.accuracy - bin.mean_confidence)
                ece += weight * error
        
        return ece
    
    def get_calibration_stats(self) -> Dict:
        """Get calibration quality statistics"""
        return {
            "ece": self.compute_ece(),
            "num_calibration_points": len(self.calibrator.calibration_data),
            "is_calibrator_fitted": self.calibrator._is_fitted,
            "bins": [
                {
                    "accuracy": bin.accuracy,
                    "mean_confidence": bin.mean_confidence,
                    "count": bin.count
                }
                for bin in self.ece_bins
            ]
        }
    
    @property
    def is_fitted(self) -> bool:
        """Check if calibrator is fitted"""
        return self.calibrator._is_fitted
    
    def get_calibration_data(self) -> List[Tuple[float, int]]:
        """Get raw calibration data for analysis"""
        return self.calibrator.calibration_data.copy()
    
    def record_calibration_point(self, confidence: float, outcome: int):
        """Record a calibration point directly"""
        self.calibrator.add_calibration_point(confidence, outcome)
        
        # Also add to ECE bins
        bin_idx = min(int(confidence * self.num_ece_bins), self.num_ece_bins - 1)
        self.ece_bins[bin_idx].predictions.append(confidence)
        self.ece_bins[bin_idx].outcomes.append(outcome)
    
    def fit_calibrator(self):
        """Force fit the calibrator"""
        if len(self.calibrator.calibration_data) >= 10:
            self.calibrator.fit()
    
    def clear_calibration_data(self):
        """Clear all calibration data"""
        self.calibrator.calibration_data.clear()
        self.calibrator._is_fitted = False
        self.calibrator.boundaries = []
        self.calibrator.calibrated_values = []
        
        # Clear ECE bins
        for bin in self.ece_bins:
            bin.predictions.clear()
            bin.outcomes.clear()


# Singleton instance
confidence_estimator = ConfidenceEstimator()
