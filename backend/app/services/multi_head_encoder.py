"""
Multi-Head Decision State Encoder

Implements the patent specification's multi-head architecture for decision state encoding:

1. Commit Probability Head: P(commit | x)
2. Hazard-of-Commit Head: h(t|x)
3. Hesitation Score Head: η(x)
4. Uncertainty Estimation Head: σ(x)

The encoder takes a windowed interaction tensor X ∈ R^(T×D) and produces
predictions from all four heads simultaneously.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import time

from app.models import (
    DecisionState,
    EnhancedDecisionState,
    InteractionSignal,
    TelemetryEvent
)
from app.services.survival_model import hazard_model, SurvivalPrediction


@dataclass
class InteractionTensor:
    """
    Windowed interaction tensor X ∈ R^(T×D)
    
    T = number of time steps (default: 30 seconds at 1Hz = 30 steps)
    D = feature dimension per time step
    
    Features per step:
        - scroll_velocity (normalized)
        - dwell_time_delta (normalized)
        - focus_change (binary)
        - skip_event (binary)
        - replay_event (binary)
        - micro_pause_ratio
    """
    tensor: np.ndarray  # Shape: (T, D)
    timestamps: List[float]
    window_duration: float  # seconds
    
    @property
    def T(self) -> int:
        return self.tensor.shape[0]
    
    @property
    def D(self) -> int:
        return self.tensor.shape[1]


@dataclass
class MultiHeadPrediction:
    """Output from all four prediction heads"""
    # Head 1: Commit probability
    commit_probability: float
    
    # Head 2: Hazard rate
    hazard_rate: float
    survival_probability: float
    expected_time_to_commit: float
    
    # Head 3: Hesitation score
    hesitation_score: float
    
    # Head 4: Uncertainty
    epistemic_uncertainty: float
    
    # Derived
    optimal_set_size: int
    should_reduce_choices: bool
    intervention_type: Optional[str]
    
    # Confidence
    prediction_confidence: float


class MultiHeadDecisionEncoder:
    """
    Multi-head architecture for decision state encoding.
    
    Takes behavioral signals and produces predictions across four heads:
    1. Commit Probability - will user select content?
    2. Hazard-of-Commit - when will user commit?
    3. Hesitation Score - how ambivalent is user?
    4. Uncertainty Estimation - how confident is the model?
    
    In production, this would be a neural network (Transformer/GRU).
    Here we implement analytical approximations that capture the same dynamics.
    """
    
    # Feature dimensions
    FEATURE_DIM = 6
    WINDOW_DURATION = 30.0  # seconds
    SAMPLE_RATE = 1.0  # Hz
    
    # Hesitation weights (from behavioral proxies)
    ALPHA_SCROLL = 0.3    # High scroll velocity → hesitation
    BETA_FOCUS = 0.35     # Focus changes → hesitation
    GAMMA_DWELL_INV = 0.2  # Low dwell time → hesitation
    DELTA_REWRITE = 0.15   # Search rewrites → hesitation
    
    def __init__(
        self,
        # Commit probability model weights
        w_commit_dwell: float = 0.4,
        w_commit_engagement: float = 0.3,
        w_commit_hesitation: float = -0.5,
        
        # Number of ensemble members for uncertainty
        n_ensemble: int = 5
    ):
        self.w_commit_dwell = w_commit_dwell
        self.w_commit_engagement = w_commit_engagement
        self.w_commit_hesitation = w_commit_hesitation
        self.n_ensemble = n_ensemble
        
        # Signal buffer for windowed computation
        self._signal_buffer: Dict[str, List[TelemetryEvent]] = {}
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def encode_interaction_tensor(
        self,
        signals: List[TelemetryEvent],
        window_end: Optional[float] = None
    ) -> InteractionTensor:
        """
        Create windowed tensor X ∈ R^(T×D) from telemetry signals.
        
        Features per time step:
            0: scroll_velocity (normalized to [0,1])
            1: dwell_time_delta (normalized)
            2: focus_change (binary)
            3: skip_event (binary)
            4: replay_event (binary)
            5: micro_pause_ratio
        """
        if window_end is None:
            window_end = time.time() * 1000  # Current time in ms
        
        window_start = window_end - (self.WINDOW_DURATION * 1000)
        
        # Filter signals to window
        windowed_signals = [
            s for s in signals
            if window_start <= s.timestamp <= window_end
        ]
        
        # Create time bins
        n_bins = int(self.WINDOW_DURATION * self.SAMPLE_RATE)
        tensor = np.zeros((n_bins, self.FEATURE_DIM))
        timestamps = []
        
        for i in range(n_bins):
            bin_start = window_start + (i * 1000 / self.SAMPLE_RATE)
            bin_end = bin_start + (1000 / self.SAMPLE_RATE)
            timestamps.append(bin_start)
            
            bin_signals = [
                s for s in windowed_signals
                if bin_start <= s.timestamp < bin_end
            ]
            
            for signal in bin_signals:
                if signal.event_type == 'scroll':
                    tensor[i, 0] = min(signal.value / 1000, 1)  # Normalize
                elif signal.event_type == 'dwell':
                    tensor[i, 1] = min(signal.value / 5000, 1)  # 5s max
                elif signal.event_type == 'focus':
                    tensor[i, 2] = 1.0
                elif signal.event_type == 'skip':
                    tensor[i, 3] = 1.0
                elif signal.event_type == 'replay':
                    tensor[i, 4] = 1.0
                elif signal.event_type == 'micro_pause':
                    tensor[i, 5] = signal.value
        
        return InteractionTensor(
            tensor=tensor,
            timestamps=timestamps,
            window_duration=self.WINDOW_DURATION
        )
    
    def _head1_commit_probability(
        self,
        tensor: InteractionTensor,
        hesitation: float
    ) -> float:
        """
        Head 1: Commit Probability
        
        P(commit | x) = σ(w·x + b)
        
        High dwell time, low hesitation → high commit probability
        """
        if tensor.T == 0:
            return 0.5
        
        # Aggregate features
        avg_dwell = np.mean(tensor.tensor[:, 1])
        engagement = 1 - np.mean(tensor.tensor[:, 3])  # Low skips = high engagement
        
        # Linear combination
        logit = (
            self.w_commit_dwell * avg_dwell +
            self.w_commit_engagement * engagement +
            self.w_commit_hesitation * hesitation
        )
        
        return self._sigmoid(logit)
    
    def _head2_hazard(
        self,
        decision_state: DecisionState,
        time_in_session: float
    ) -> SurvivalPrediction:
        """
        Head 2: Hazard-of-Commit
        
        Uses the dedicated survival model for hazard rate computation.
        """
        return hazard_model.predict_time_to_commit(decision_state, time_in_session)
    
    def _head3_hesitation(
        self,
        tensor: InteractionTensor,
        decision_state: DecisionState
    ) -> float:
        """
        Head 3: Hesitation Score
        
        η = α·(scroll_velocity) + β·(focus_changes) + γ·(1/dwell_time) + δ·(search_rewrites)
        
        This quantifies explicit ambivalence based on behavioral proxies.
        """
        # From tensor: recent behavior
        if tensor.T > 0:
            avg_scroll = np.mean(tensor.tensor[:, 0])
            total_focus_changes = np.sum(tensor.tensor[:, 2])
            avg_dwell = np.mean(tensor.tensor[:, 1])
        else:
            avg_scroll = decision_state.scroll_velocity / 1000
            total_focus_changes = decision_state.focus_changes
            avg_dwell = decision_state.dwell_time / 5000
        
        # Inverse dwell (low dwell = high hesitation)
        inv_dwell = 1 - avg_dwell if avg_dwell > 0 else 1.0
        
        # Search rewrites from decision state
        search_factor = min(decision_state.search_rewrites / 5, 1)
        
        # Compute hesitation score
        hesitation = (
            self.ALPHA_SCROLL * avg_scroll +
            self.BETA_FOCUS * min(total_focus_changes / 5, 1) +
            self.GAMMA_DWELL_INV * inv_dwell +
            self.DELTA_REWRITE * search_factor
        )
        
        return max(0, min(1, hesitation))
    
    def _head4_uncertainty(
        self,
        tensor: InteractionTensor,
        predictions: List[float]
    ) -> float:
        """
        Head 4: Uncertainty Estimation
        
        σ(x) = epistemic uncertainty via ensemble disagreement
        
        In production: Use MC Dropout or ensemble of networks.
        Here: Use prediction variance + signal sparsity.
        """
        # Ensemble disagreement (variance of predictions with noise)
        if predictions:
            ensemble_preds = [
                p + np.random.randn() * 0.1 for p in predictions
                for _ in range(self.n_ensemble)
            ]
            ensemble_var = np.var(ensemble_preds)
        else:
            ensemble_var = 0.25  # High uncertainty default
        
        # Signal sparsity (sparse signals = high uncertainty)
        if tensor.T > 0:
            sparsity = 1 - (np.count_nonzero(tensor.tensor) / tensor.tensor.size)
        else:
            sparsity = 1.0
        
        # Combine sources of uncertainty
        uncertainty = 0.5 * np.sqrt(ensemble_var) + 0.5 * sparsity
        
        return max(0, min(1, uncertainty))
    
    def _compute_optimal_set_size(self, hesitation: float) -> int:
        """
        Compute cognitively optimal set size.
        
        n = max(2, min(5, round(5 - 3 * η)))
        
        High hesitation → fewer choices
        """
        raw_size = 5 - 3 * hesitation
        return max(2, min(5, round(raw_size)))
    
    def encode_and_predict(
        self,
        signals: List[TelemetryEvent],
        decision_state: DecisionState,
        time_in_session: float = 0.0
    ) -> MultiHeadPrediction:
        """
        Full multi-head encoding and prediction.
        
        Takes telemetry signals and produces all four head outputs.
        """
        # Encode interaction tensor
        tensor = self.encode_interaction_tensor(signals)
        
        # Head 3: Hesitation (needed for other heads)
        hesitation = self._head3_hesitation(tensor, decision_state)
        
        # Head 1: Commit probability
        commit_prob = self._head1_commit_probability(tensor, hesitation)
        
        # Head 2: Hazard model
        survival_pred = self._head2_hazard(decision_state, time_in_session)
        
        # Head 4: Uncertainty
        uncertainty = self._head4_uncertainty(
            tensor,
            [commit_prob, survival_pred.hazard_rate, hesitation]
        )
        
        # Derived metrics
        optimal_size = self._compute_optimal_set_size(hesitation)
        should_reduce = hesitation > 0.6
        
        # Determine intervention type
        intervention = None
        if should_reduce:
            intervention = "reduce_choices"
        elif uncertainty > 0.5:
            intervention = "simplify_ui"
        elif survival_pred.expected_time_to_commit > 90:
            intervention = "offer_help"
        
        # Overall confidence
        confidence = 1 - uncertainty
        
        return MultiHeadPrediction(
            commit_probability=commit_prob,
            hazard_rate=survival_pred.hazard_rate,
            survival_probability=survival_pred.survival_probability,
            expected_time_to_commit=survival_pred.expected_time_to_commit,
            hesitation_score=hesitation,
            epistemic_uncertainty=uncertainty,
            optimal_set_size=optimal_size,
            should_reduce_choices=should_reduce,
            intervention_type=intervention,
            prediction_confidence=confidence
        )
    
    def update_signal_buffer(
        self,
        user_id: str,
        events: List[TelemetryEvent]
    ):
        """Add new telemetry events to user's signal buffer."""
        if user_id not in self._signal_buffer:
            self._signal_buffer[user_id] = []
        
        self._signal_buffer[user_id].extend(events)
        
        # Keep only recent signals (last 60 seconds)
        cutoff = time.time() * 1000 - 60000
        self._signal_buffer[user_id] = [
            e for e in self._signal_buffer[user_id]
            if e.timestamp > cutoff
        ]
    
    def get_user_signals(self, user_id: str) -> List[TelemetryEvent]:
        """Get buffered signals for a user."""
        return self._signal_buffer.get(user_id, [])
    
    def create_enhanced_decision_state(
        self,
        base_state: DecisionState,
        signals: List[TelemetryEvent],
        time_in_session: float = 0.0
    ) -> EnhancedDecisionState:
        """
        Create full EnhancedDecisionState from base state and signals.
        
        This is the main interface for the recommendation engine.
        """
        # Get multi-head predictions
        prediction = self.encode_and_predict(signals, base_state, time_in_session)
        
        # Create interaction window (last 30 normalized signal values)
        tensor = self.encode_interaction_tensor(signals)
        if tensor.T > 0:
            # Flatten recent values
            window = tensor.tensor[-30:].flatten().tolist()[:30]
        else:
            window = [0.0] * 30
        
        return EnhancedDecisionState(
            # Core signals
            stress_level=base_state.stress_level,
            scroll_velocity=base_state.scroll_velocity,
            dwell_time=base_state.dwell_time,
            focus_changes=base_state.focus_changes,
            search_rewrites=base_state.search_rewrites,
            
            # Multi-head outputs
            commit_probability=prediction.commit_probability,
            hesitation_score=prediction.hesitation_score,
            hazard_rate=prediction.hazard_rate,
            survival_probability=prediction.survival_probability,
            epistemic_uncertainty=prediction.epistemic_uncertainty,
            
            # Temporal
            time_in_session=time_in_session,
            session_start_timestamp=time.time() * 1000 - time_in_session * 1000,
            
            # Window
            interaction_window=window,
            
            # Derived
            optimal_set_size=prediction.optimal_set_size,
            confidence_score=prediction.prediction_confidence,
            should_reduce_choices=prediction.should_reduce_choices,
            predicted_time_to_commit=prediction.expected_time_to_commit
        )


# Singleton instance
multi_head_encoder = MultiHeadDecisionEncoder()
