"""
Decision State Service for Sequential Narrative AI
Implements decision state encoding for reducing choice paralysis.
Monitors user behavior to detect decision stress and provide support.
"""
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.models import (
    DecisionState, DecisionStateResponse, 
    DecisionStateUpdateRequest, InteractionType
)
from app.config import settings


class DecisionStateService:
    """
    Service for managing user decision states.
    
    Design concept:
    "The Decision State Encoder uses a sequence model (Transformer or GRU)
    to produce a latent decision state vector. This state vector is the
    computational heart of the system."
    
    Key signals:
    - Scroll velocity (fast scrolling = indecision)
    - Dwell time (low dwell = overwhelmed)
    - Focus changes (back-and-forth = uncertainty)
    - Search rewrites (modifications = unclear intent)
    """
    
    def __init__(self):
        # In-memory state store (use Redis/DB in production)
        self._user_states: Dict[str, DecisionState] = {}
        self._interaction_history: Dict[str, list] = {}
    
    def get_decision_state(self, user_id: str) -> DecisionState:
        """Get current decision state for a user"""
        if user_id not in self._user_states:
            self._user_states[user_id] = DecisionState()
        return self._user_states[user_id]
    
    def update_decision_state(
        self, 
        request: DecisionStateUpdateRequest
    ) -> DecisionStateResponse:
        """
        Update decision state based on behavioral signals.
        
        The stress level is computed as a weighted combination of:
        - Scroll velocity factor (0.3 weight)
        - Dwell time factor (0.3 weight)  
        - Focus changes factor (0.4 weight)
        """
        current_state = self.get_decision_state(request.user_id)
        
        # Calculate stress components
        velocity_factor = self._calculate_velocity_factor(request.scroll_velocity)
        dwell_factor = self._calculate_dwell_factor(request.dwell_time)
        focus_factor = self._calculate_focus_factor(request.focus_changes)
        
        # Weighted stress calculation
        new_stress_level = (
            velocity_factor * 0.3 +
            dwell_factor * 0.3 +
            focus_factor * 0.4
        )
        
        # Apply smoothing (don't change too abruptly)
        smoothed_stress = (
            current_state.stress_level * 0.7 + 
            new_stress_level * 0.3
        )
        
        # Update state
        updated_state = DecisionState(
            stress_level=round(smoothed_stress, 3),
            scroll_velocity=request.scroll_velocity,
            dwell_time=request.dwell_time,
            focus_changes=request.focus_changes,
            search_rewrites=current_state.search_rewrites,
            confidence_score=self._calculate_confidence(smoothed_stress)
        )
        
        # Record interaction if provided
        if request.interaction_type:
            self._record_interaction(
                request.user_id, 
                request.interaction_type
            )
            # Update based on interaction
            updated_state = self._adjust_for_interaction(
                updated_state, 
                request.interaction_type
            )
        
        self._user_states[request.user_id] = updated_state
        
        # Determine optimal recommendation count
        recommendation_count = self._calculate_recommendation_count(updated_state)
        
        # Check if intervention is needed
        should_intervene = updated_state.stress_level > settings.INTERVENTION_THRESHOLD
        intervention_message = None
        
        if should_intervene:
            intervention_message = self._generate_intervention_message(updated_state)
        
        return DecisionStateResponse(
            user_id=request.user_id,
            decision_state=updated_state,
            recommendation_count=recommendation_count,
            should_intervene=should_intervene,
            intervention_message=intervention_message
        )
    
    def _calculate_velocity_factor(self, scroll_velocity: float) -> float:
        """
        Calculate stress factor from scroll velocity.
        High velocity = user is frantically searching = high stress
        """
        # Normalize: 0 = calm browsing, 1000+ = frantic scrolling
        normalized = min(scroll_velocity / 1000, 1.0)
        return normalized
    
    def _calculate_dwell_factor(self, dwell_time: float) -> float:
        """
        Calculate stress factor from dwell time.
        Very low dwell time = user not engaging = overwhelmed
        Very high dwell time = user stuck = indecisive
        """
        # Optimal dwell time is 3-8 seconds
        if dwell_time < 2000:  # Less than 2s
            return 0.8  # High stress - not engaging
        elif dwell_time < 5000:  # 2-5s
            return 0.3  # Moderate - quick decisions
        elif dwell_time < 10000:  # 5-10s
            return 0.1  # Low - engaged but decisive
        else:  # Over 10s
            return 0.5  # Moderate - might be stuck
    
    def _calculate_focus_factor(self, focus_changes: int) -> float:
        """
        Calculate stress factor from focus changes.
        Many back-and-forth navigations = uncertainty
        """
        # Normalize: 0-2 = normal, 10+ = very uncertain
        normalized = min(focus_changes / 10, 1.0)
        return normalized
    
    def _calculate_confidence(self, stress_level: float) -> float:
        """Calculate system confidence (inverse of stress)"""
        return round(1 - (stress_level * 0.5), 2)
    
    def _calculate_recommendation_count(self, state: DecisionState) -> int:
        """
        Determine optimal number of recommendations.
        High stress = fewer choices to reduce paralysis.
        """
        if state.stress_level > settings.STRESS_HIGH_THRESHOLD:
            return settings.MIN_RECOMMENDATIONS
        elif state.stress_level > settings.STRESS_LOW_THRESHOLD:
            return 3
        else:
            return settings.DEFAULT_RECOMMENDATIONS
    
    def _record_interaction(self, user_id: str, interaction_type: InteractionType):
        """Record user interaction for pattern analysis"""
        if user_id not in self._interaction_history:
            self._interaction_history[user_id] = []
        
        self._interaction_history[user_id].append({
            "type": interaction_type,
            "timestamp": datetime.now()
        })
        
        # Keep only last 50 interactions
        self._interaction_history[user_id] = self._interaction_history[user_id][-50:]
    
    def _adjust_for_interaction(
        self, 
        state: DecisionState, 
        interaction_type: InteractionType
    ) -> DecisionState:
        """Adjust state based on interaction type"""
        stress_adjustment = 0
        
        if interaction_type == InteractionType.SELECT:
            # User made a decision - reduce stress
            stress_adjustment = -0.1
        elif interaction_type == InteractionType.SKIP:
            # Skip is neutral to slightly positive
            stress_adjustment = 0.02
        elif interaction_type == InteractionType.DISMISS:
            # Dismissing without selection - slight stress increase
            stress_adjustment = 0.05
        elif interaction_type == InteractionType.REPLAY:
            # Replaying suggests engagement
            stress_adjustment = -0.05
        
        new_stress = max(0, min(1, state.stress_level + stress_adjustment))
        
        return DecisionState(
            stress_level=round(new_stress, 3),
            scroll_velocity=state.scroll_velocity,
            dwell_time=state.dwell_time,
            focus_changes=state.focus_changes,
            search_rewrites=state.search_rewrites,
            confidence_score=self._calculate_confidence(new_stress)
        )
    
    def _generate_intervention_message(self, state: DecisionState) -> str:
        """Generate helpful intervention message based on state"""
        messages = {
            "high_velocity": "Slow down! Let me help narrow things down for you.",
            "low_dwell": "Feeling overwhelmed? Try asking me what you're in the mood for.",
            "many_focus_changes": "Can't decide? Tell me what you liked recently and I'll find similar picks.",
            "general": "Let me simplify your choices. What's one thing you're looking for right now?"
        }
        
        if state.scroll_velocity > 500:
            return messages["high_velocity"]
        elif state.dwell_time < 2000:
            return messages["low_dwell"]
        elif state.focus_changes > 5:
            return messages["many_focus_changes"]
        return messages["general"]
    
    def increment_search_rewrites(self, user_id: str):
        """Track when user rewrites their search query"""
        state = self.get_decision_state(user_id)
        state.search_rewrites += 1
        
        # High search rewrites indicate confusion
        if state.search_rewrites > 3:
            state.stress_level = min(1, state.stress_level + 0.1)
        
        self._user_states[user_id] = state
    
    def reset_session(self, user_id: str):
        """Reset decision state for new session"""
        self._user_states[user_id] = DecisionState()
        self._interaction_history[user_id] = []
    
    def get_session_summary(self, user_id: str) -> dict:
        """Get summary of user's decision-making session"""
        state = self.get_decision_state(user_id)
        history = self._interaction_history.get(user_id, [])
        
        # Count interaction types
        interaction_counts = {}
        for interaction in history:
            itype = interaction["type"].value
            interaction_counts[itype] = interaction_counts.get(itype, 0) + 1
        
        return {
            "user_id": user_id,
            "current_stress_level": state.stress_level,
            "total_interactions": len(history),
            "interaction_breakdown": interaction_counts,
            "recommendation_quality": "high" if state.stress_level < 0.3 else "medium" if state.stress_level < 0.6 else "needs_improvement"
        }


# Singleton instance
decision_state_service = DecisionStateService()
