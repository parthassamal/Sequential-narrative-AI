"""
Hazard-of-Commit Survival Model

Implements discrete-time survival analysis for predicting when users will commit
to a content selection decision.

From patent specification:
    h(t|x) = probability of committing at time t given survival until t
    S(t) = exp(-∫h(s)ds) = survival function (probability of not having committed)

This modeling approach is borrowed from medical survival analysis (DeepSurv)
but applied to user choice dynamics in content recommendation.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from app.models import DecisionState, EnhancedDecisionState


@dataclass
class SurvivalPrediction:
    """Output of survival model prediction"""
    hazard_rate: float  # h(t|x) - instantaneous commit probability
    survival_probability: float  # S(t) - probability user hasn't committed
    expected_time_to_commit: float  # E[T|X] - expected remaining time
    commit_probability_by_time: List[float]  # P(T <= t) for t in [0, 30, 60, 90, 120]
    confidence_interval: Tuple[float, float]  # 95% CI for expected time


class HazardOfCommitModel:
    """
    Survival analysis model for predicting user commit behavior.
    
    Key concepts:
    - Hazard function h(t|x): Instantaneous probability of committing at time t
      given the user has not committed by time t
    - Survival function S(t): Probability that commit hasn't happened by time t
    - Cumulative hazard H(t): Integral of hazard function
    
    The model uses behavioral signals (scroll velocity, dwell time, focus changes)
    to estimate the hazard function, which varies over time during a session.
    """
    
    def __init__(
        self,
        # Learned weights (in production, these would be trained)
        w_scroll: float = -0.3,      # High scroll → lower hazard (user browsing)
        w_dwell: float = 0.4,        # High dwell → higher hazard (user engaged)
        w_focus: float = -0.2,       # Focus changes → lower hazard (user uncertain)
        w_time: float = -0.1,        # Time decay - hazard decreases over time (fatigue)
        w_stress: float = -0.25,     # High stress → lower hazard (analysis paralysis)
        baseline_hazard: float = 0.1,  # λ_0 - baseline hazard rate
        time_discretization: float = 5.0  # Seconds per discrete time step
    ):
        self.w_scroll = w_scroll
        self.w_dwell = w_dwell
        self.w_focus = w_focus
        self.w_time = w_time
        self.w_stress = w_stress
        self.baseline_hazard = baseline_hazard
        self.dt = time_discretization
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation for bounded outputs"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _normalize_features(self, decision_state: DecisionState) -> Dict[str, float]:
        """Normalize behavioral features to [0, 1] range"""
        return {
            'scroll': min(decision_state.scroll_velocity / 1000, 1),  # 1000 px/s max
            'dwell': min(decision_state.dwell_time / 30000, 1),  # 30s max
            'focus': min(decision_state.focus_changes / 10, 1),  # 10 changes max
            'stress': decision_state.stress_level,
        }
    
    def compute_hazard_rate(
        self,
        decision_state: DecisionState,
        time_t: float
    ) -> float:
        """
        Compute discrete-time hazard: P(commit at t | survived until t)
        
        h(t|x) = σ(w·x + w_t·t + b)
        
        Where:
            x = behavioral feature vector
            w = learned weights
            t = time in session
            σ = sigmoid function
        """
        features = self._normalize_features(decision_state)
        
        # Linear combination of features
        linear = (
            self.w_scroll * features['scroll'] +
            self.w_dwell * features['dwell'] +
            self.w_focus * features['focus'] +
            self.w_stress * features['stress'] +
            self.w_time * (time_t / 120)  # Normalize time to ~2 min sessions
        )
        
        # Apply sigmoid and scale by baseline hazard
        hazard = self.baseline_hazard * (1 + self._sigmoid(linear))
        
        return max(0.01, min(0.99, hazard))  # Clamp to avoid edge cases
    
    def compute_survival_probability(
        self,
        hazard_rates: List[float]
    ) -> float:
        """
        Compute survival probability at time T.
        
        S(T) = Π_{t<T} (1 - h(t))
        
        This is the discrete-time approximation of:
        S(t) = exp(-∫_0^t h(s)ds)
        """
        if not hazard_rates:
            return 1.0
        
        survival = 1.0
        for h in hazard_rates:
            survival *= (1 - h)
        
        return max(0.001, survival)  # Never exactly 0
    
    def compute_cumulative_hazard(
        self,
        hazard_rates: List[float]
    ) -> float:
        """
        Compute cumulative hazard function H(t) = -log(S(t))
        
        Also approximated as: H(t) ≈ Σ h(s) for discrete time
        """
        return sum(hazard_rates)
    
    def predict_survival_curve(
        self,
        decision_state: DecisionState,
        max_time: float = 120.0,  # 2 minute horizon
        start_time: float = 0.0
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Predict full survival curve over time horizon.
        
        Returns:
            times: Time points
            hazard_rates: h(t) at each time
            survival_probs: S(t) at each time
        """
        times = []
        hazard_rates = []
        survival_probs = []
        
        cumulative_hazards = []
        
        t = start_time
        while t <= max_time:
            h_t = self.compute_hazard_rate(decision_state, t)
            cumulative_hazards.append(h_t)
            s_t = self.compute_survival_probability(cumulative_hazards)
            
            times.append(t)
            hazard_rates.append(h_t)
            survival_probs.append(s_t)
            
            t += self.dt
        
        return times, hazard_rates, survival_probs
    
    def predict_time_to_commit(
        self,
        decision_state: DecisionState,
        time_in_session: float = 0.0
    ) -> SurvivalPrediction:
        """
        Predict expected time until user commits.
        
        E[T|X] = ∫_0^∞ S(t) dt
        
        In discrete time: E[T] ≈ Σ S(t) * Δt
        
        Also returns:
        - Current hazard rate
        - Current survival probability
        - Commit probability by time milestones
        """
        times, hazards, survivals = self.predict_survival_curve(
            decision_state,
            max_time=180.0,  # 3 minute max horizon
            start_time=time_in_session
        )
        
        # Current values
        current_hazard = hazards[0] if hazards else self.baseline_hazard
        current_survival = survivals[0] if survivals else 1.0
        
        # Expected time to commit (integral of survival function)
        expected_time = sum(s * self.dt for s in survivals)
        
        # Commit probability by milestone times
        milestones = [0, 30, 60, 90, 120]
        commit_by_time = []
        for milestone in milestones:
            idx = int((milestone - time_in_session) / self.dt)
            if 0 <= idx < len(survivals):
                commit_prob = 1 - survivals[idx]
            elif milestone <= time_in_session:
                commit_prob = 0.0
            else:
                commit_prob = 1 - survivals[-1] if survivals else 0.5
            commit_by_time.append(commit_prob)
        
        # Confidence interval (using simple variance estimation)
        # In production, this would use proper bootstrap or Bayesian inference
        variance_estimate = expected_time * 0.3  # Rough 30% CV assumption
        ci_lower = max(0, expected_time - 1.96 * variance_estimate)
        ci_upper = expected_time + 1.96 * variance_estimate
        
        return SurvivalPrediction(
            hazard_rate=current_hazard,
            survival_probability=current_survival,
            expected_time_to_commit=expected_time,
            commit_probability_by_time=commit_by_time,
            confidence_interval=(ci_lower, ci_upper)
        )
    
    def should_trigger_intervention(
        self,
        decision_state: DecisionState,
        time_in_session: float,
        uncertainty_threshold: float = 0.3
    ) -> Tuple[bool, str, float]:
        """
        Determine if system should intervene based on survival analysis.
        
        Intervention triggers:
        1. Very low hazard rate + high time → user stuck
        2. Decreasing survival + high stress → analysis paralysis
        3. High uncertainty about prediction → offer help
        
        Returns:
            should_intervene: bool
            intervention_type: str (reduce_choices, simplify_ui, offer_help)
            confidence: float
        """
        prediction = self.predict_time_to_commit(decision_state, time_in_session)
        
        # Check for intervention conditions
        
        # Condition 1: User stuck (low hazard, high time)
        if prediction.hazard_rate < 0.05 and time_in_session > 60:
            return True, "offer_help", 0.8
        
        # Condition 2: Analysis paralysis (high stress, low survival)
        if decision_state.stress_level > 0.6 and prediction.survival_probability < 0.3:
            return True, "reduce_choices", 0.75
        
        # Condition 3: High uncertainty (wide confidence interval)
        ci_width = prediction.confidence_interval[1] - prediction.confidence_interval[0]
        if ci_width > prediction.expected_time_to_commit * 0.5:
            return True, "simplify_ui", 0.6
        
        # Condition 4: Long expected time to commit
        if prediction.expected_time_to_commit > 90:
            return True, "reduce_choices", 0.7
        
        return False, "", 0.0


class MultiSessionSurvivalModel:
    """
    Extended survival model that learns from multiple sessions.
    
    Uses historical session data to improve hazard rate estimation
    and personalize predictions per user.
    """
    
    def __init__(self, base_model: Optional[HazardOfCommitModel] = None):
        self.base_model = base_model or HazardOfCommitModel()
        self.user_adjustments: Dict[str, Dict[str, float]] = {}
    
    def update_from_session(
        self,
        user_id: str,
        session_data: Dict,
        actual_commit_time: Optional[float]
    ):
        """
        Update model based on completed session.
        
        Uses online learning to adjust user-specific weights.
        """
        if user_id not in self.user_adjustments:
            self.user_adjustments[user_id] = {
                'hazard_bias': 0.0,
                'time_scale': 1.0,
                'session_count': 0
            }
        
        adj = self.user_adjustments[user_id]
        
        if actual_commit_time is not None:
            # User committed - adjust based on prediction error
            # This is a simplified online update
            predicted_time = session_data.get('predicted_commit_time', 60)
            error = actual_commit_time - predicted_time
            
            # Exponential moving average update
            alpha = 0.3
            adj['hazard_bias'] += alpha * (error / 60)  # Normalize by typical session
            adj['time_scale'] = adj['time_scale'] * (1 - alpha) + \
                               (actual_commit_time / max(1, predicted_time)) * alpha
        
        adj['session_count'] += 1
    
    def predict_for_user(
        self,
        user_id: str,
        decision_state: DecisionState,
        time_in_session: float
    ) -> SurvivalPrediction:
        """Get personalized survival prediction for a user."""
        base_prediction = self.base_model.predict_time_to_commit(
            decision_state, time_in_session
        )
        
        if user_id in self.user_adjustments:
            adj = self.user_adjustments[user_id]
            
            # Apply personalization
            adjusted_time = base_prediction.expected_time_to_commit * adj['time_scale']
            adjusted_hazard = base_prediction.hazard_rate * (1 + adj['hazard_bias'])
            
            return SurvivalPrediction(
                hazard_rate=max(0.01, min(0.99, adjusted_hazard)),
                survival_probability=base_prediction.survival_probability,
                expected_time_to_commit=max(5, adjusted_time),
                commit_probability_by_time=base_prediction.commit_probability_by_time,
                confidence_interval=base_prediction.confidence_interval
            )
        
        return base_prediction


# Singleton instances
hazard_model = HazardOfCommitModel()
multi_session_model = MultiSessionSurvivalModel(hazard_model)
