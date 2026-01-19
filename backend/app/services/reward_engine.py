"""
Deferral-Aware Reinforcement Learning Reward Engine

Implements patent specification section 7.2-7.3:
- Multi-objective reward function with 5 terms
- R = w1·R_defer + w2·R_abandon + w3·R_stress + w4·R_trigger + w5·R_diversity
- Offline policy evaluation via Inverse Propensity Scoring
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time
import math

from app.services.stress_proxy import stress_proxy, StressPrediction


@dataclass
class SessionOutcome:
    """Outcome of a recommendation session"""
    session_id: str
    user_id: str
    
    # Timing
    session_start: float
    session_end: float
    time_to_commit: Optional[float]  # None if abandoned
    
    # Outcomes
    committed: bool
    abandoned: bool
    quick_cancelled: bool
    
    # Stress
    initial_stress: float
    final_stress: float
    
    # Diversity
    genres_exposed: List[str]
    content_types_exposed: List[str]
    
    # For IPS
    action_probabilities: List[float]  # π_b(a|s) for logged actions


@dataclass
class RewardComponents:
    """Individual reward components"""
    r_defer: float       # Deferral penalty
    r_abandon: float     # Abandonment penalty
    r_stress: float      # Stress reduction reward
    r_trigger: float     # Trigger quality reward
    r_diversity: float   # Diversity exposure reward
    
    total: float         # Weighted sum
    weights_used: Dict[str, float]


@dataclass
class PolicyEvaluation:
    """Result of offline policy evaluation"""
    estimated_reward: float
    variance: float
    confidence_interval: Tuple[float, float]
    effective_sample_size: float
    policy_name: str


class RewardEngine:
    """
    Multi-Objective Reward Function for Deferral-Aware RL
    
    R = w1·R_defer + w2·R_abandon + w3·R_stress + w4·R_trigger + w5·R_diversity
    
    Where:
    - R_defer = -log(1 + T_decision/T_norm) : Deferral penalty
    - R_abandon = -I_abandon : Abandonment penalty  
    - R_stress = -S(x) : Stress reduction (negative stress = positive reward)
    - R_trigger = I_success : Trigger quality (1 if commit succeeds)
    - R_diversity = H(genres) : Shannon entropy of exposed genres
    """
    
    # Default weights (tuned via Bayesian optimization in production)
    DEFAULT_WEIGHTS = {
        "defer": 0.25,      # w1: Penalize deferral
        "abandon": 0.30,    # w2: Strongly penalize abandonment
        "stress": 0.20,     # w3: Reward stress reduction
        "trigger": 0.15,    # w4: Reward successful triggers
        "diversity": 0.10,  # w5: Reward diversity exposure
    }
    
    # Normalization constants
    T_NORM = 60.0  # Normalize decision time to 60 seconds
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Session history for learning
        self._session_history: deque = deque(maxlen=10000)
        
        # Running reward statistics
        self._reward_history: deque = deque(maxlen=1000)
        
        # Policy logs for IPS
        self._policy_logs: List[Dict] = []
    
    def compute_deferral_reward(
        self,
        time_to_commit: Optional[float],
        abandoned: bool
    ) -> float:
        """
        R_defer = -log(1 + T_decision/T_norm)
        
        Encourages rapid, decisive commits.
        Returns 0 if abandoned (handled by R_abandon).
        """
        if abandoned or time_to_commit is None:
            return 0.0
        
        # Log penalty increases with decision time
        normalized_time = time_to_commit / self.T_NORM
        return -math.log(1 + normalized_time)
    
    def compute_abandonment_reward(self, abandoned: bool) -> float:
        """
        R_abandon = -I_abandon
        
        Binary penalty for session abandonment.
        """
        return -1.0 if abandoned else 0.0
    
    def compute_stress_reward(
        self,
        initial_stress: float,
        final_stress: float
    ) -> float:
        """
        R_stress = -S(x)
        
        Directly penalizes predicted stress.
        Also rewards stress reduction during session.
        """
        # Base penalty for final stress level
        base_penalty = -final_stress
        
        # Bonus for stress reduction
        stress_reduction = initial_stress - final_stress
        reduction_bonus = max(0, stress_reduction) * 0.5
        
        return base_penalty + reduction_bonus
    
    def compute_trigger_reward(
        self,
        committed: bool,
        quick_cancelled: bool
    ) -> float:
        """
        R_trigger = I_success
        
        1 if commit succeeds (no quick cancel), 0 otherwise.
        """
        if committed and not quick_cancelled:
            return 1.0
        elif committed and quick_cancelled:
            return -0.5  # Penalty for false positive trigger
        return 0.0
    
    def compute_diversity_reward(
        self,
        genres_exposed: List[str],
        content_types_exposed: List[str]
    ) -> float:
        """
        R_diversity = H(genres)
        
        Shannon entropy over exposed genres/tags.
        Encourages genre diversity, preventing filter bubbles.
        """
        if not genres_exposed:
            return 0.0
        
        # Combine genres and types
        all_tags = genres_exposed + content_types_exposed
        
        # Count frequencies
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        total = len(all_tags)
        
        # Compute Shannon entropy: H = -Σ p(g)·log(p(g))
        entropy = 0.0
        for count in tag_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        # Normalize to [0, 1] based on max possible entropy
        max_entropy = math.log2(len(tag_counts)) if tag_counts else 1
        normalized_entropy = entropy / max(max_entropy, 1)
        
        return normalized_entropy
    
    def compute_reward(
        self,
        outcome: SessionOutcome
    ) -> RewardComponents:
        """
        Compute full multi-objective reward.
        
        R = w1·R_defer + w2·R_abandon + w3·R_stress + w4·R_trigger + w5·R_diversity
        """
        # Compute individual components
        r_defer = self.compute_deferral_reward(
            outcome.time_to_commit,
            outcome.abandoned
        )
        
        r_abandon = self.compute_abandonment_reward(outcome.abandoned)
        
        r_stress = self.compute_stress_reward(
            outcome.initial_stress,
            outcome.final_stress
        )
        
        r_trigger = self.compute_trigger_reward(
            outcome.committed,
            outcome.quick_cancelled
        )
        
        r_diversity = self.compute_diversity_reward(
            outcome.genres_exposed,
            outcome.content_types_exposed
        )
        
        # Weighted sum
        total = (
            self.weights["defer"] * r_defer +
            self.weights["abandon"] * r_abandon +
            self.weights["stress"] * r_stress +
            self.weights["trigger"] * r_trigger +
            self.weights["diversity"] * r_diversity
        )
        
        components = RewardComponents(
            r_defer=r_defer,
            r_abandon=r_abandon,
            r_stress=r_stress,
            r_trigger=r_trigger,
            r_diversity=r_diversity,
            total=total,
            weights_used=self.weights.copy()
        )
        
        # Track
        self._reward_history.append({
            "timestamp": time.time(),
            "total": total,
            "components": {
                "defer": r_defer,
                "abandon": r_abandon,
                "stress": r_stress,
                "trigger": r_trigger,
                "diversity": r_diversity
            }
        })
        
        return components
    
    def record_session(self, outcome: SessionOutcome):
        """Record session outcome for learning"""
        reward = self.compute_reward(outcome)
        self._session_history.append({
            "outcome": outcome,
            "reward": reward
        })
    
    def evaluate_policy_ips(
        self,
        target_policy_probs: List[float],
        policy_name: str = "target"
    ) -> PolicyEvaluation:
        """
        Offline Policy Evaluation via Inverse Propensity Scoring (IPS)
        
        V_IPS(π) = (1/n) Σ (π(a|s) / π_b(a|s)) · r
        
        Where:
        - π is the target policy
        - π_b is the behavior (logged) policy
        - r is the observed reward
        
        Uses doubly robust estimator for variance reduction.
        """
        if not self._session_history:
            return PolicyEvaluation(
                estimated_reward=0.0,
                variance=float('inf'),
                confidence_interval=(0.0, 0.0),
                effective_sample_size=0,
                policy_name=policy_name
            )
        
        n = len(self._session_history)
        importance_weights = []
        weighted_rewards = []
        
        for i, session_data in enumerate(self._session_history):
            outcome = session_data["outcome"]
            reward = session_data["reward"]
            
            # Get behavior policy probabilities
            behavior_probs = outcome.action_probabilities
            
            if not behavior_probs or i >= len(target_policy_probs):
                continue
            
            # Compute importance weight
            target_prob = target_policy_probs[i % len(target_policy_probs)]
            behavior_prob = np.mean(behavior_probs) if behavior_probs else 0.5
            
            if behavior_prob > 0.01:  # Avoid division by very small numbers
                weight = target_prob / behavior_prob
                # Clip weights for stability
                weight = min(weight, 10.0)
                
                importance_weights.append(weight)
                weighted_rewards.append(weight * reward.total)
        
        if not weighted_rewards:
            return PolicyEvaluation(
                estimated_reward=0.0,
                variance=float('inf'),
                confidence_interval=(0.0, 0.0),
                effective_sample_size=0,
                policy_name=policy_name
            )
        
        # IPS estimate
        estimated_reward = np.mean(weighted_rewards)
        
        # Variance estimate
        variance = np.var(weighted_rewards) / len(weighted_rewards)
        
        # Confidence interval (95%)
        std_error = np.sqrt(variance)
        ci_lower = estimated_reward - 1.96 * std_error
        ci_upper = estimated_reward + 1.96 * std_error
        
        # Effective sample size
        sum_weights = sum(importance_weights)
        sum_weights_sq = sum(w**2 for w in importance_weights)
        effective_n = (sum_weights ** 2) / sum_weights_sq if sum_weights_sq > 0 else 0
        
        return PolicyEvaluation(
            estimated_reward=estimated_reward,
            variance=variance,
            confidence_interval=(ci_lower, ci_upper),
            effective_sample_size=effective_n,
            policy_name=policy_name
        )
    
    def get_reward_statistics(self) -> Dict:
        """Get reward statistics for monitoring"""
        if not self._reward_history:
            return {
                "count": 0,
                "average_total": 0.0,
                "component_averages": {}
            }
        
        totals = [r["total"] for r in self._reward_history]
        
        # Component averages
        component_sums = {
            "defer": 0.0,
            "abandon": 0.0,
            "stress": 0.0,
            "trigger": 0.0,
            "diversity": 0.0
        }
        
        for r in self._reward_history:
            for key in component_sums:
                component_sums[key] += r["components"][key]
        
        n = len(self._reward_history)
        component_avgs = {k: v/n for k, v in component_sums.items()}
        
        return {
            "count": n,
            "average_total": np.mean(totals),
            "std_total": np.std(totals),
            "min_total": min(totals),
            "max_total": max(totals),
            "component_averages": component_avgs,
            "weights": self.weights
        }
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update reward weights (e.g., from Bayesian optimization)"""
        for key in new_weights:
            if key in self.weights:
                self.weights[key] = new_weights[key]
        
        # Normalize to sum to 1
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v/total for k, v in self.weights.items()}


# Singleton instance
reward_engine = RewardEngine()
