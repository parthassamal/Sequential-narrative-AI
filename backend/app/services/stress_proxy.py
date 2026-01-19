"""
Stress Proxy Model

Implements patent specification section 7.1:
- Trains stress proxy S(x) from interaction features
- Optional micro-survey integration
- Inputs: dwell time variance, rapid clicking, search rewrites
- Operationalizes AJPOR OTT study finding that choice deferral increases stress
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time

from app.models import DecisionState, EnhancedDecisionState


@dataclass
class StressFeatures:
    """Features used for stress prediction"""
    dwell_time_variance: float  # High variance = indecision
    click_rate: float  # Clicks per second (high = frustration)
    search_rewrites: int  # Query modifications
    scroll_reversal_rate: float  # Back-and-forth scrolling
    session_duration: float  # Longer sessions = more stress
    focus_changes: int  # Tab switches
    skip_velocity: float  # How fast user skips content
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for model"""
        return np.array([
            min(self.dwell_time_variance / 10000, 1),  # Normalize
            min(self.click_rate / 2, 1),  # 2 clicks/sec max
            min(self.search_rewrites / 5, 1),  # 5 rewrites max
            min(self.scroll_reversal_rate / 0.5, 1),  # 50% reversal max
            min(self.session_duration / 300, 1),  # 5 min max
            min(self.focus_changes / 10, 1),  # 10 changes max
            min(self.skip_velocity / 2, 1),  # 2 skips/sec max
        ])


@dataclass
class StressPrediction:
    """Output of stress proxy model"""
    stress_level: float  # S(x) ∈ [0, 1]
    confidence: float  # Model confidence
    contributing_factors: Dict[str, float]  # Feature contributions
    recommendation: str  # Action recommendation


@dataclass
class MicroSurveyResponse:
    """Optional micro-survey response for supervised learning"""
    user_id: str
    timestamp: float
    stress_rating: int  # 1-5 Likert scale
    features_at_time: StressFeatures


class StressProxyModel:
    """
    Stress Proxy Model S(x)
    
    Predicts user stress level from behavioral signals.
    Can be trained with optional micro-survey labels.
    
    The model learns:
    S(x) = σ(w · φ(x) + b)
    
    Where φ(x) includes:
    - Dwell time variance
    - Click rate (rapid clicking indicates frustration)
    - Search rewrites
    - Scroll reversals
    - Session duration
    - Focus changes
    """
    
    # Default weights (would be learned from micro-surveys in production)
    DEFAULT_WEIGHTS = np.array([
        0.15,   # dwell_time_variance
        0.25,   # click_rate (strong indicator)
        0.20,   # search_rewrites
        0.15,   # scroll_reversal_rate
        0.10,   # session_duration
        0.10,   # focus_changes
        0.05,   # skip_velocity
    ])
    
    BIAS = -0.3  # Start with moderate stress assumption
    
    FEATURE_NAMES = [
        "dwell_variance",
        "click_rate",
        "search_rewrites",
        "scroll_reversals",
        "session_duration",
        "focus_changes",
        "skip_velocity"
    ]
    
    def __init__(self):
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self.bias = self.BIAS
        
        # Training data from micro-surveys
        self._training_data: List[Tuple[np.ndarray, float]] = []
        
        # Running statistics for feature normalization
        self._feature_means = np.zeros(7)
        self._feature_stds = np.ones(7)
        self._sample_count = 0
        
        # Recent predictions for trend analysis
        self._prediction_history: deque = deque(maxlen=100)
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def extract_features(
        self,
        decision_state: DecisionState,
        session_interactions: Optional[List[Dict]] = None,
        session_start_time: Optional[float] = None
    ) -> StressFeatures:
        """
        Extract stress-related features from decision state and interactions
        """
        interactions = session_interactions or []
        
        # Dwell time variance
        dwell_times = [
            i.get('dwell_time', 0) for i in interactions
            if 'dwell_time' in i
        ]
        dwell_variance = np.var(dwell_times) if len(dwell_times) > 1 else 0
        
        # Click rate
        if interactions and session_start_time:
            session_duration = time.time() - session_start_time
            click_count = sum(1 for i in interactions if i.get('type') == 'click')
            click_rate = click_count / max(session_duration, 1)
        else:
            click_rate = 0
        
        # Search rewrites
        search_rewrites = decision_state.search_rewrites
        
        # Scroll reversal rate
        scroll_events = [
            i for i in interactions if i.get('type') == 'scroll'
        ]
        if len(scroll_events) > 1:
            reversals = sum(
                1 for i in range(1, len(scroll_events))
                if (scroll_events[i].get('direction', 1) * 
                    scroll_events[i-1].get('direction', 1)) < 0
            )
            scroll_reversal_rate = reversals / len(scroll_events)
        else:
            scroll_reversal_rate = 0
        
        # Session duration
        if session_start_time:
            session_duration = time.time() - session_start_time
        else:
            session_duration = getattr(
                decision_state, 'time_in_session', 0
            )
        
        # Focus changes
        focus_changes = decision_state.focus_changes
        
        # Skip velocity
        skip_events = [i for i in interactions if i.get('type') == 'skip']
        if skip_events and session_start_time:
            skip_velocity = len(skip_events) / max(session_duration, 1)
        else:
            skip_velocity = 0
        
        return StressFeatures(
            dwell_time_variance=dwell_variance,
            click_rate=click_rate,
            search_rewrites=search_rewrites,
            scroll_reversal_rate=scroll_reversal_rate,
            session_duration=session_duration,
            focus_changes=focus_changes,
            skip_velocity=skip_velocity
        )
    
    def predict(
        self,
        features: StressFeatures
    ) -> StressPrediction:
        """
        Predict stress level: S(x) = σ(w · φ(x) + b)
        """
        feature_vector = features.to_vector()
        
        # Linear combination
        logit = np.dot(self.weights, feature_vector) + self.bias
        stress_level = self._sigmoid(logit)
        
        # Compute feature contributions
        contributions = {}
        for i, (name, weight, value) in enumerate(zip(
            self.FEATURE_NAMES, self.weights, feature_vector
        )):
            contributions[name] = weight * value
        
        # Model confidence (based on feature magnitude)
        confidence = 1 - np.exp(-np.sum(feature_vector))
        confidence = min(0.95, max(0.3, confidence))
        
        # Generate recommendation
        if stress_level > 0.7:
            recommendation = "reduce_choices"
        elif stress_level > 0.5:
            recommendation = "slow_pacing"
        elif stress_level > 0.3:
            recommendation = "normal"
        else:
            recommendation = "allow_exploration"
        
        prediction = StressPrediction(
            stress_level=stress_level,
            confidence=confidence,
            contributing_factors=contributions,
            recommendation=recommendation
        )
        
        # Track prediction
        self._prediction_history.append({
            "timestamp": time.time(),
            "stress_level": stress_level,
            "features": feature_vector.tolist()
        })
        
        return prediction
    
    def predict_from_state(
        self,
        decision_state: DecisionState,
        session_interactions: Optional[List[Dict]] = None,
        session_start_time: Optional[float] = None
    ) -> StressPrediction:
        """Convenience method to predict directly from decision state"""
        features = self.extract_features(
            decision_state, session_interactions, session_start_time
        )
        return self.predict(features)
    
    def add_micro_survey_response(self, response: MicroSurveyResponse):
        """
        Add micro-survey response for supervised learning.
        
        "How stressed do you feel choosing right now?" (1-5 Likert)
        """
        feature_vector = response.features_at_time.to_vector()
        
        # Normalize stress rating to [0, 1]
        normalized_stress = (response.stress_rating - 1) / 4.0
        
        self._training_data.append((feature_vector, normalized_stress))
        
        # Retrain if we have enough data
        if len(self._training_data) >= 20:
            self._train()
    
    def _train(self):
        """
        Train model on micro-survey data using simple gradient descent.
        In production, would use proper ML framework.
        """
        if len(self._training_data) < 10:
            return
        
        X = np.array([d[0] for d in self._training_data])
        y = np.array([d[1] for d in self._training_data])
        
        # Simple gradient descent
        learning_rate = 0.1
        for _ in range(100):
            # Forward pass
            logits = X @ self.weights + self.bias
            predictions = 1 / (1 + np.exp(-np.clip(logits, -500, 500)))
            
            # Compute gradients (MSE loss)
            errors = predictions - y
            grad_w = (2 / len(y)) * (X.T @ errors)
            grad_b = (2 / len(y)) * np.sum(errors)
            
            # Update
            self.weights -= learning_rate * grad_w
            self.bias -= learning_rate * grad_b
        
        print(f"Stress proxy trained on {len(self._training_data)} samples")
    
    def get_stress_trend(self, window_seconds: float = 60) -> Dict:
        """Analyze recent stress trend"""
        current_time = time.time()
        recent = [
            p for p in self._prediction_history
            if current_time - p['timestamp'] < window_seconds
        ]
        
        if len(recent) < 2:
            return {
                "trend": "stable",
                "average": recent[0]['stress_level'] if recent else 0.5,
                "samples": len(recent)
            }
        
        stress_levels = [p['stress_level'] for p in recent]
        avg_stress = np.mean(stress_levels)
        
        # Linear regression for trend
        x = np.arange(len(stress_levels))
        slope = np.polyfit(x, stress_levels, 1)[0]
        
        if slope > 0.01:
            trend = "increasing"
        elif slope < -0.01:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": slope,
            "average": avg_stress,
            "min": min(stress_levels),
            "max": max(stress_levels),
            "samples": len(recent)
        }
    
    def get_model_stats(self) -> Dict:
        """Get model statistics"""
        return {
            "weights": dict(zip(self.FEATURE_NAMES, self.weights.tolist())),
            "bias": self.bias,
            "training_samples": len(self._training_data),
            "prediction_count": len(self._prediction_history),
            "recent_trend": self.get_stress_trend()
        }


# Singleton instance
stress_proxy = StressProxyModel()
