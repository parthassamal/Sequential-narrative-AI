"""API Routes for Sequential Narrative AI"""
from app.routes.recommendations import router as recommendations_router
from app.routes.decision_state import router as decision_state_router
from app.routes.audio import router as audio_router
from app.routes.streaming import router as streaming_router
from app.routes.telemetry import telemetry_router
from app.routes.commitment import commitment_router
from app.routes.compliance import compliance_router
from app.routes.metrics import metrics_router

__all__ = [
    "recommendations_router",
    "decision_state_router",
    "audio_router",
    "streaming_router",
    "telemetry_router",
    "commitment_router",
    "compliance_router",
    "metrics_router"
]
