"""
Commitment and Metrics API Routes

Implements patent specification API endpoints for:
- Commitment trigger evaluation
- Quick cancel reporting
- Session metrics
- Aggregate metrics
- Stress estimation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import time

from app.models import DecisionState, EnhancedDecisionState
from app.services.commitment_trigger import commitment_trigger, TriggerResult
from app.services.confidence_calibrator import confidence_estimator
from app.services.stress_proxy import stress_proxy, StressFeatures
from app.services.metrics_service import metrics_service
from app.services.reward_engine import reward_engine, SessionOutcome


router = APIRouter(prefix="/api", tags=["Commitment & Metrics"])


# ========== Request/Response Models ==========

class TriggerEvaluationRequest(BaseModel):
    user_id: str
    session_id: str
    content_id: str
    exposure_time: float = Field(..., description="Time spent on current NRU (seconds)")
    time_in_session: float = Field(..., description="Total session time (seconds)")
    decision_state: DecisionState
    recent_interactions: Optional[List[Dict]] = None


class TriggerEvaluationResponse(BaseModel):
    should_trigger: bool
    result: str
    calibrated_confidence: float
    dynamic_threshold: float
    exposure_time: float
    min_exposure_time: float
    uncertainty: float
    max_uncertainty: float
    trigger_id: Optional[str]
    recommended_action: Dict


class QuickCancelRequest(BaseModel):
    trigger_id: str
    user_id: str
    cancel_timestamp: Optional[float] = None


class QuickCancelResponse(BaseModel):
    acknowledged: bool
    is_quick_cancel: bool
    time_to_cancel: float
    learning_signal: str


class SessionStartRequest(BaseModel):
    session_id: str
    user_id: str
    initial_stress: float = 0.5


class SessionCommitRequest(BaseModel):
    session_id: str
    at_nru: int
    final_stress: float


class SessionEndRequest(BaseModel):
    session_id: str
    final_stress: Optional[float] = None


class StressEstimateRequest(BaseModel):
    decision_state: DecisionState
    session_interactions: Optional[List[Dict]] = None
    session_start_time: Optional[float] = None


class StressEstimateResponse(BaseModel):
    stress_level: float
    confidence: float
    contributing_factors: Dict[str, float]
    recommendation: str
    trend: Dict


class MetricsResponse(BaseModel):
    ccr_3: float
    ccr_5: float
    ccr_7: float
    dlr: float
    di: float
    srr: float
    cta: float
    de: float
    total_sessions: int
    committed_sessions: int
    abandoned_sessions: int
    ece: float


# ========== Commitment Endpoints ==========

@router.post("/commitment/evaluate", response_model=TriggerEvaluationResponse)
async def evaluate_commitment_trigger(request: TriggerEvaluationRequest):
    """
    Evaluate whether commitment should be triggered.
    
    Three-way gate:
    1. C_cal(t|x) > τ(x) - Calibrated confidence > dynamic threshold
    2. t_expose > t_min - Minimum exposure time elapsed
    3. σ(x) < σ_max - Uncertainty below safety threshold
    """
    evaluation = commitment_trigger.evaluate_trigger(
        decision_state=request.decision_state,
        exposure_time=request.exposure_time,
        time_in_session=request.time_in_session,
        content_id=request.content_id,
        user_id=request.user_id,
        recent_interactions=request.recent_interactions
    )
    
    recommended_action = commitment_trigger.get_recommended_action(evaluation)
    
    return TriggerEvaluationResponse(
        should_trigger=evaluation.should_trigger,
        result=evaluation.result.value,
        calibrated_confidence=evaluation.calibrated_confidence,
        dynamic_threshold=evaluation.dynamic_threshold,
        exposure_time=evaluation.exposure_time,
        min_exposure_time=evaluation.min_exposure_time,
        uncertainty=evaluation.uncertainty,
        max_uncertainty=evaluation.max_uncertainty,
        trigger_id=evaluation.trigger_id,
        recommended_action=recommended_action
    )


@router.post("/commitment/cancel", response_model=QuickCancelResponse)
async def report_quick_cancel(request: QuickCancelRequest):
    """
    Report that a triggered commit was quickly cancelled.
    
    This is a negative learning signal: q(i) = -1
    """
    event = commitment_trigger.report_quick_cancel(
        trigger_id=request.trigger_id,
        cancel_timestamp=request.cancel_timestamp
    )
    
    if event is None:
        return QuickCancelResponse(
            acknowledged=False,
            is_quick_cancel=False,
            time_to_cancel=0,
            learning_signal="Trigger not found"
        )
    
    return QuickCancelResponse(
        acknowledged=True,
        is_quick_cancel=event.is_quick_cancel,
        time_to_cancel=event.time_to_cancel,
        learning_signal="negative" if event.is_quick_cancel else "neutral"
    )


@router.post("/commitment/success")
async def report_commit_success(trigger_id: str):
    """
    Report that a triggered commit was successful (not cancelled).
    Called after the quick cancel window expires.
    """
    success = commitment_trigger.report_commit_success(trigger_id)
    return {"acknowledged": success, "learning_signal": "positive" if success else "not_found"}


@router.get("/commitment/quality")
async def get_trigger_quality():
    """Get trigger quality metrics including CTA and calibration stats"""
    return commitment_trigger.get_trigger_quality()


# ========== Session Tracking Endpoints ==========

@router.post("/session/start")
async def start_session(request: SessionStartRequest):
    """Start tracking a new recommendation session"""
    session = metrics_service.start_session(
        session_id=request.session_id,
        user_id=request.user_id,
        initial_stress=request.initial_stress
    )
    return {"session_id": session.session_id, "started": True}


@router.post("/session/nru-view")
async def record_nru_view(session_id: str, nru_index: int, genres: List[str]):
    """Record that user viewed an NRU"""
    metrics_service.record_nru_view(session_id, nru_index, genres)
    return {"recorded": True}


@router.post("/session/commit")
async def record_commit(request: SessionCommitRequest):
    """Record successful commit"""
    metrics_service.record_commit(
        session_id=request.session_id,
        at_nru=request.at_nru,
        final_stress=request.final_stress
    )
    return {"recorded": True}


@router.post("/session/end")
async def end_session(request: SessionEndRequest):
    """End session and compute final metrics"""
    metrics_service.end_session(
        session_id=request.session_id,
        final_stress=request.final_stress
    )
    return {"ended": True}


# ========== Stress Estimation Endpoints ==========

@router.post("/stress/estimate", response_model=StressEstimateResponse)
async def estimate_stress(request: StressEstimateRequest):
    """
    Get stress proxy prediction from behavioral signals.
    
    S(x) = σ(w · φ(x) + b)
    """
    prediction = stress_proxy.predict_from_state(
        decision_state=request.decision_state,
        session_interactions=request.session_interactions,
        session_start_time=request.session_start_time
    )
    
    trend = stress_proxy.get_stress_trend()
    
    return StressEstimateResponse(
        stress_level=prediction.stress_level,
        confidence=prediction.confidence,
        contributing_factors=prediction.contributing_factors,
        recommendation=prediction.recommendation,
        trend=trend
    )


@router.get("/stress/stats")
async def get_stress_stats():
    """Get stress proxy model statistics"""
    return stress_proxy.get_model_stats()


# ========== Metrics Endpoints ==========

@router.get("/metrics/aggregate", response_model=MetricsResponse)
async def get_aggregate_metrics():
    """
    Get all aggregate patent metrics:
    - CCR: Commit Conversion Rate (by 3rd, 5th, 7th NRU)
    - DLR: Decision Latency Reduction
    - DI: Deferral Index
    - SRR: Stress Reduction Ratio
    - CTA: Confidence Trigger Accuracy
    - DE: Diversity Exposure
    """
    metrics = metrics_service.get_aggregate_metrics()
    
    return MetricsResponse(
        ccr_3=metrics.ccr_3,
        ccr_5=metrics.ccr_5,
        ccr_7=metrics.ccr_7,
        dlr=metrics.dlr,
        di=metrics.di,
        srr=metrics.srr,
        cta=metrics.cta,
        de=metrics.de,
        total_sessions=metrics.total_sessions,
        committed_sessions=metrics.committed_sessions,
        abandoned_sessions=metrics.abandoned_sessions,
        ece=metrics.ece
    )


@router.get("/metrics/realtime")
async def get_realtime_metrics():
    """Get real-time metrics for monitoring dashboard"""
    return metrics_service.get_real_time_metrics()


@router.get("/metrics/export")
async def export_metrics():
    """Export session data for offline analysis"""
    return metrics_service.export_for_analysis()


@router.get("/metrics/reward-stats")
async def get_reward_stats():
    """Get reward engine statistics"""
    return reward_engine.get_reward_statistics()


@router.get("/metrics/calibration")
async def get_calibration_stats():
    """Get confidence calibration statistics including ECE"""
    return confidence_estimator.get_calibration_stats()


commitment_router = router
