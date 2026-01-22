"""
Metrics API Routes

Provides endpoints for analytics dashboard:
- Aggregate metrics (CCR, DLR, DI, SRR, CTA, DE)
- Real-time metrics
- Calibration data
- Session recording
- Demo data seeding
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.services.metrics_service import metrics_service
from app.services.confidence_calibrator import confidence_estimator


router = APIRouter(prefix="/api/metrics", tags=["Metrics"])


# Request model for session recording
class SessionRecord(BaseModel):
    session_id: str
    user_id: str = "anonymous"
    committed: bool
    commit_at_nru: Optional[int] = None
    time_to_commit_ms: Optional[float] = None
    total_browse_time_ms: float
    initial_stress: float = 0.5
    final_stress: float = 0.5
    genres_shown: List[str] = []
    cards_viewed: int = 0


@router.post("/session")
async def record_session(session: SessionRecord):
    """
    Record a completed session from the frontend.
    
    Called when user either commits (selects content) or abandons (closes reel).
    """
    import time
    
    # Start session in metrics service
    metrics_session = metrics_service.start_session(
        session_id=session.session_id,
        user_id=session.user_id,
        initial_stress=session.initial_stress
    )
    
    # Record genres viewed
    if session.genres_shown:
        metrics_service.record_nru_view(
            session.session_id,
            session.cards_viewed,
            session.genres_shown
        )
    
    # Record outcome
    if session.committed and session.commit_at_nru:
        metrics_service.record_commit(
            session.session_id,
            at_nru=session.commit_at_nru,
            final_stress=session.final_stress
        )
        # Also end the session to move it to completed
        metrics_service.end_session(
            session.session_id,
            final_stress=session.final_stress
        )
        # Record calibration point for commit
        confidence_estimator.record_calibration_point(
            1.0 - session.final_stress,  # Use inverse stress as confidence proxy
            1  # Committed
        )
    else:
        # End as abandoned
        metrics_service.end_session(
            session.session_id,
            final_stress=session.final_stress
        )
        # Record calibration point for abandon
        confidence_estimator.record_calibration_point(
            1.0 - session.final_stress,
            0  # Did not commit
        )
    
    # Try to fit calibrator if we have enough data
    if len(confidence_estimator.get_calibration_data()) >= 10:
        confidence_estimator.fit_calibrator()
    
    return {
        "status": "recorded",
        "session_id": session.session_id,
        "committed": session.committed,
        "total_sessions": len(metrics_service._completed_sessions) + len(metrics_service._active_sessions)
    }


@router.get("/aggregate")
async def get_aggregate_metrics():
    """
    Get aggregate metrics for the analytics dashboard.
    
    Returns CCR (Commit Conversion Rate), DLR (Decision Latency Reduction),
    DI (Deferral Index), SRR (Stress Reduction Ratio), CTA (Confidence Trigger Accuracy),
    DE (Diversity Exposure), and ECE (Expected Calibration Error).
    """
    metrics = metrics_service.get_aggregate_metrics()
    
    return {
        "ccr_3": metrics.ccr_3,
        "ccr_5": metrics.ccr_5,
        "ccr_7": metrics.ccr_7,
        "dlr": metrics.dlr,
        "di": metrics.di,
        "srr": metrics.srr,
        "cta": metrics.cta,
        "de": metrics.de,
        "total_sessions": metrics.total_sessions,
        "committed_sessions": metrics.committed_sessions,
        "abandoned_sessions": metrics.abandoned_sessions,
        "ece": metrics.ece
    }


@router.get("/realtime")
async def get_realtime_metrics():
    """
    Get real-time metrics for live dashboard updates.
    
    Includes active sessions, recent conversion rate, trigger quality,
    stress trend, and calibration ECE.
    """
    return metrics_service.get_real_time_metrics()


@router.get("/calibration")
async def get_calibration_stats():
    """
    Get confidence calibration statistics.
    
    Returns ECE (Expected Calibration Error), number of calibration points,
    whether the calibrator is fitted, and bin statistics.
    """
    # Ensure calibrator is fitted if we have enough data
    if len(confidence_estimator.get_calibration_data()) >= 10:
        confidence_estimator.fit_calibrator()
    
    # Generate bins for reliability diagram
    bins = []
    num_bins = 10
    
    for i in range(num_bins):
        bin_lower = i / num_bins
        bin_upper = (i + 1) / num_bins
        bin_center = (bin_lower + bin_upper) / 2
        
        # Get samples in this bin
        calibration_data = confidence_estimator.get_calibration_data()
        
        bin_samples = [
            (conf, outcome) 
            for conf, outcome in calibration_data
            if bin_lower <= conf < bin_upper
        ]
        
        if bin_samples:
            accuracy = sum(o for _, o in bin_samples) / len(bin_samples)
            mean_conf = sum(c for c, _ in bin_samples) / len(bin_samples)
        else:
            accuracy = bin_center  # Perfect calibration default
            mean_conf = bin_center
        
        bins.append({
            "accuracy": accuracy,
            "mean_confidence": mean_conf,
            "count": len(bin_samples)
        })
    
    return {
        "ece": confidence_estimator.compute_ece(),
        "num_calibration_points": len(confidence_estimator.get_calibration_data()),
        "is_calibrator_fitted": confidence_estimator.is_fitted,
        "bins": bins
    }


@router.post("/seed-demo")
async def seed_demo_data():
    """
    Seed the metrics service with demo data.
    
    This populates the analytics dashboard with sample sessions
    for demonstration purposes.
    """
    result = metrics_service.seed_demo_data()
    
    # Also seed some calibration data
    import random
    for _ in range(100):
        confidence = random.random()
        # Simulate imperfect calibration - outcome is biased by confidence
        outcome = 1 if random.random() < (confidence * 0.8 + 0.1) else 0
        confidence_estimator.record_calibration_point(confidence, outcome)
    
    confidence_estimator.fit_calibrator()
    
    return {
        **result,
        "calibration_points": len(confidence_estimator.get_calibration_data()),
        "calibrator_fitted": confidence_estimator.is_fitted
    }


@router.delete("/clear")
async def clear_metrics():
    """Clear all metrics data"""
    metrics_service._completed_sessions.clear()
    metrics_service._ccr_3_successes = 0
    metrics_service._ccr_5_successes = 0
    metrics_service._ccr_7_successes = 0
    metrics_service._total_tracked = 0
    confidence_estimator.clear_calibration_data()
    
    return {"message": "All metrics cleared"}


metrics_router = router
