"""
Metrics Service for Patent Evaluation

Implements patent specification section 8.1-8.2:
- CCR: Commit Conversion Rate
- DLR: Decision Latency Reduction
- DI: Deferral Index
- SRR: Stress Reduction Ratio
- CTA: Confidence Trigger Accuracy
- DE: Diversity Exposure (Shannon entropy)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
import time
import math

from app.services.commitment_trigger import commitment_trigger
from app.services.stress_proxy import stress_proxy
from app.services.confidence_calibrator import confidence_estimator


@dataclass
class SessionMetrics:
    """Metrics for a single session"""
    session_id: str
    user_id: str
    start_time: float
    end_time: Optional[float] = None
    
    # Conversion
    committed: bool = False
    commit_at_nru: Optional[int] = None  # Which NRU (1-indexed)
    
    # Timing
    time_to_commit: Optional[float] = None  # seconds
    total_browse_time: float = 0.0
    
    # Stress
    initial_stress: float = 0.5
    final_stress: float = 0.5
    
    # Diversity
    genres_shown: List[str] = field(default_factory=list)
    
    # Trigger quality
    trigger_fired: bool = False
    trigger_successful: bool = False
    quick_cancelled: bool = False


@dataclass
class AggregateMetrics:
    """Aggregate metrics across sessions"""
    # Primary Metrics
    ccr_3: float  # Commit by 3rd NRU
    ccr_5: float  # Commit by 5th NRU
    ccr_7: float  # Commit by 7th NRU
    dlr: float    # Decision Latency Reduction
    di: float     # Deferral Index
    srr: float    # Stress Reduction Ratio
    cta: float    # Confidence Trigger Accuracy
    de: float     # Diversity Exposure
    
    # Counts
    total_sessions: int
    committed_sessions: int
    abandoned_sessions: int
    
    # Confidence intervals
    ccr_ci: Tuple[float, float]
    dlr_ci: Tuple[float, float]
    
    # Calibration
    ece: float  # Expected Calibration Error


class MetricsService:
    """
    Patent Metrics Tracking and Statistical Reporting
    
    Tracks all metrics defined in patent specification section 8:
    - CCR: Percentage of sessions with commit by 3rd/5th/7th NRU
    - DLR: (T_baseline - T_system) / T_baseline
    - DI: T_browse / T_total
    - SRR: (S_baseline - S_system) / S_baseline
    - CTA: commits without quick-cancel / total triggers
    - DE: -Σ p(g)·log(p(g)) - Shannon entropy
    """
    
    # Baseline values (from A/B testing or historical data)
    BASELINE_DECISION_TIME = 120.0  # seconds
    BASELINE_STRESS = 0.6  # Average stress without system
    
    def __init__(self):
        # Session tracking
        self._active_sessions: Dict[str, SessionMetrics] = {}
        self._completed_sessions: deque = deque(maxlen=10000)
        
        # Real-time metrics
        self._metrics_history: deque = deque(maxlen=1000)
        
        # Statistical accumulators
        self._ccr_3_successes = 0
        self._ccr_5_successes = 0
        self._ccr_7_successes = 0
        self._total_tracked = 0
    
    def start_session(
        self,
        session_id: str,
        user_id: str,
        initial_stress: float = 0.5
    ) -> SessionMetrics:
        """Start tracking a new session"""
        metrics = SessionMetrics(
            session_id=session_id,
            user_id=user_id,
            start_time=time.time(),
            initial_stress=initial_stress
        )
        self._active_sessions[session_id] = metrics
        return metrics
    
    def record_nru_view(
        self,
        session_id: str,
        nru_index: int,
        genres: List[str]
    ):
        """Record that user viewed an NRU"""
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        session.genres_shown.extend(genres)
    
    def record_commit(
        self,
        session_id: str,
        at_nru: int,
        final_stress: float
    ):
        """Record successful commit"""
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        session.committed = True
        session.commit_at_nru = at_nru
        session.end_time = time.time()
        session.time_to_commit = session.end_time - session.start_time
        session.final_stress = final_stress
        
        # Update CCR counters
        if at_nru <= 3:
            self._ccr_3_successes += 1
        if at_nru <= 5:
            self._ccr_5_successes += 1
        if at_nru <= 7:
            self._ccr_7_successes += 1
        self._total_tracked += 1
    
    def record_trigger(
        self,
        session_id: str,
        successful: bool,
        quick_cancelled: bool = False
    ):
        """Record trigger event"""
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions[session_id]
        session.trigger_fired = True
        session.trigger_successful = successful
        session.quick_cancelled = quick_cancelled
    
    def end_session(
        self,
        session_id: str,
        final_stress: Optional[float] = None
    ):
        """End session and move to completed"""
        if session_id not in self._active_sessions:
            return
        
        session = self._active_sessions.pop(session_id)
        
        # Only set end_time if not already set by record_commit
        if session.end_time is None:
            session.end_time = time.time()
        
        # For committed sessions, use the commit time as browse time
        # For abandoned sessions, calculate from current time
        if session.time_to_commit is not None:
            session.total_browse_time = session.time_to_commit
        else:
            session.total_browse_time = session.end_time - session.start_time
        
        if final_stress is not None:
            session.final_stress = final_stress
        
        if not session.committed:
            self._total_tracked += 1
        
        self._completed_sessions.append(session)
    
    def compute_ccr(self, by_nru: int) -> Tuple[float, Tuple[float, float]]:
        """
        Compute Commit Conversion Rate by NRU threshold.
        
        CCR_k = % of sessions with commit event by k-th NRU
        
        Returns (rate, (ci_lower, ci_upper)) using Wilson score interval.
        """
        if by_nru == 3:
            successes = self._ccr_3_successes
        elif by_nru == 5:
            successes = self._ccr_5_successes
        else:
            successes = self._ccr_7_successes
        
        n = self._total_tracked
        if n == 0:
            return 0.0, (0.0, 0.0)
        
        p = successes / n
        
        # Wilson score interval
        z = 1.96  # 95% confidence
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2*n)) / denominator
        margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
        
        ci_lower = max(0, center - margin)
        ci_upper = min(1, center + margin)
        
        return p, (ci_lower, ci_upper)
    
    def compute_dlr(self) -> Tuple[float, Tuple[float, float]]:
        """
        Compute Decision Latency Reduction.
        
        DLR = (T_baseline - T_system) / T_baseline
        
        Quantifies reduction in time-to-commit.
        """
        committed_sessions = [
            s for s in self._completed_sessions
            if s.committed and s.time_to_commit is not None
        ]
        
        if not committed_sessions:
            return 0.0, (0.0, 0.0)
        
        times = [s.time_to_commit for s in committed_sessions]
        t_system = np.mean(times)
        
        dlr = (self.BASELINE_DECISION_TIME - t_system) / self.BASELINE_DECISION_TIME
        
        # Bootstrap confidence interval
        if len(times) > 10:
            bootstrap_dlrs = []
            for _ in range(1000):
                sample = np.random.choice(times, len(times), replace=True)
                sample_mean = np.mean(sample)
                bootstrap_dlr = (self.BASELINE_DECISION_TIME - sample_mean) / self.BASELINE_DECISION_TIME
                bootstrap_dlrs.append(bootstrap_dlr)
            
            ci_lower = np.percentile(bootstrap_dlrs, 2.5)
            ci_upper = np.percentile(bootstrap_dlrs, 97.5)
        else:
            ci_lower = dlr - 0.1
            ci_upper = dlr + 0.1
        
        return dlr, (ci_lower, ci_upper)
    
    def compute_di(self) -> float:
        """
        Compute Deferral Index.
        
        DI = T_browse / T_total
        
        Measures fraction of session spent deferring (browsing without commit).
        """
        all_sessions = list(self._completed_sessions)
        if not all_sessions:
            return 0.0
        
        total_browse = sum(s.total_browse_time for s in all_sessions)
        total_time = sum(
            (s.time_to_commit or s.total_browse_time)
            for s in all_sessions
        )
        
        if total_time == 0:
            return 0.0
        
        return total_browse / total_time
    
    def compute_srr(self) -> float:
        """
        Compute Stress Reduction Ratio.
        
        SRR = (S_baseline - S_system) / S_baseline
        
        Uses micro-survey stress scales and stress proxy.
        """
        sessions_with_stress = [
            s for s in self._completed_sessions
            if s.final_stress is not None
        ]
        
        if not sessions_with_stress:
            return 0.0
        
        s_system = np.mean([s.final_stress for s in sessions_with_stress])
        
        return (self.BASELINE_STRESS - s_system) / self.BASELINE_STRESS
    
    def compute_cta(self) -> float:
        """
        Compute Confidence Trigger Accuracy.
        
        CTA = commits without quick-cancel / total triggers
        
        Measures confidence estimator quality.
        """
        triggered_sessions = [
            s for s in self._completed_sessions
            if s.trigger_fired
        ]
        
        if not triggered_sessions:
            return 0.0
        
        successful = sum(
            1 for s in triggered_sessions
            if s.trigger_successful and not s.quick_cancelled
        )
        
        return successful / len(triggered_sessions)
    
    def compute_de(self) -> float:
        """
        Compute Diversity Exposure (Shannon Entropy).
        
        DE = -Σ p(g)·log₂(p(g))
        
        Ensures recommendations don't narrow user horizons.
        """
        all_genres = []
        for session in self._completed_sessions:
            all_genres.extend(session.genres_shown)
        
        if not all_genres:
            return 0.0
        
        # Count frequencies
        genre_counts = {}
        for genre in all_genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        total = len(all_genres)
        
        # Shannon entropy
        entropy = 0.0
        for count in genre_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        # Normalize by max possible entropy
        max_entropy = math.log2(len(genre_counts)) if genre_counts else 1
        
        return entropy / max(max_entropy, 1)
    
    def get_aggregate_metrics(self) -> AggregateMetrics:
        """Compute all aggregate metrics"""
        ccr_3, ccr_3_ci = self.compute_ccr(3)
        ccr_5, _ = self.compute_ccr(5)
        ccr_7, _ = self.compute_ccr(7)
        dlr, dlr_ci = self.compute_dlr()
        
        committed = sum(1 for s in self._completed_sessions if s.committed)
        abandoned = len(self._completed_sessions) - committed
        
        return AggregateMetrics(
            ccr_3=ccr_3,
            ccr_5=ccr_5,
            ccr_7=ccr_7,
            dlr=dlr,
            di=self.compute_di(),
            srr=self.compute_srr(),
            cta=self.compute_cta(),
            de=self.compute_de(),
            total_sessions=len(self._completed_sessions),
            committed_sessions=committed,
            abandoned_sessions=abandoned,
            ccr_ci=ccr_3_ci,
            dlr_ci=dlr_ci,
            ece=confidence_estimator.compute_ece()
        )
    
    def get_real_time_metrics(self) -> Dict:
        """Get current real-time metrics"""
        active_count = len(self._active_sessions)
        
        # Recent session stats (last hour)
        one_hour_ago = time.time() - 3600
        recent_sessions = [
            s for s in self._completed_sessions
            if s.end_time and s.end_time > one_hour_ago
        ]
        
        recent_committed = sum(1 for s in recent_sessions if s.committed)
        recent_rate = recent_committed / len(recent_sessions) if recent_sessions else 0
        
        # Trigger quality from commitment_trigger
        trigger_quality = commitment_trigger.get_trigger_quality()
        
        # Stress trend
        stress_trend = stress_proxy.get_stress_trend()
        
        return {
            "active_sessions": active_count,
            "recent_conversion_rate": recent_rate,
            "recent_sessions_count": len(recent_sessions),
            "trigger_quality": trigger_quality,
            "stress_trend": stress_trend,
            "calibration_ece": confidence_estimator.compute_ece()
        }
    
    def export_for_analysis(self) -> List[Dict]:
        """Export session data for offline analysis"""
        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "committed": s.committed,
                "commit_at_nru": s.commit_at_nru,
                "time_to_commit": s.time_to_commit,
                "total_browse_time": s.total_browse_time,
                "initial_stress": s.initial_stress,
                "final_stress": s.final_stress,
                "genres_count": len(set(s.genres_shown)),
                "trigger_fired": s.trigger_fired,
                "trigger_successful": s.trigger_successful,
                "quick_cancelled": s.quick_cancelled
            }
            for s in self._completed_sessions
        ]


    def seed_demo_data(self):
        """Seed demo data for testing the analytics dashboard"""
        import random
        
        # Clear existing data
        self._completed_sessions.clear()
        self._ccr_3_successes = 0
        self._ccr_5_successes = 0
        self._ccr_7_successes = 0
        self._total_tracked = 0
        
        genres = ["Action", "Comedy", "Drama", "Sci-Fi", "Horror", "Romance", "Documentary", "Thriller"]
        
        # Generate 50 demo sessions
        for i in range(50):
            session_id = f"demo-session-{i}"
            user_id = f"demo-user-{i % 10}"
            
            # Randomize session outcomes
            committed = random.random() > 0.3  # 70% commit rate
            commit_at_nru = random.randint(1, 5) if committed else None
            
            # Start session
            session = SessionMetrics(
                session_id=session_id,
                user_id=user_id,
                start_time=time.time() - random.randint(60, 7200),
                initial_stress=random.uniform(0.3, 0.7)
            )
            
            # Add genres
            session.genres_shown = random.sample(genres, k=random.randint(2, 5))
            
            if committed:
                session.committed = True
                session.commit_at_nru = commit_at_nru
                session.time_to_commit = random.uniform(15, 90)  # 15-90 seconds
                session.final_stress = random.uniform(0.1, 0.4)  # Lower stress after commit
                
                # Update CCR counters
                if commit_at_nru <= 3:
                    self._ccr_3_successes += 1
                if commit_at_nru <= 5:
                    self._ccr_5_successes += 1
                if commit_at_nru <= 7:
                    self._ccr_7_successes += 1
            else:
                session.committed = False
                session.total_browse_time = random.uniform(30, 180)
                session.final_stress = random.uniform(0.4, 0.8)
            
            # Trigger events for some sessions
            if random.random() > 0.5:
                session.trigger_fired = True
                session.trigger_successful = committed
                session.quick_cancelled = not committed and random.random() > 0.7
            
            session.end_time = time.time() - random.randint(0, 3600)
            
            self._total_tracked += 1
            self._completed_sessions.append(session)
        
        return {"message": f"Seeded {len(self._completed_sessions)} demo sessions"}


# Singleton instance
metrics_service = MetricsService()
