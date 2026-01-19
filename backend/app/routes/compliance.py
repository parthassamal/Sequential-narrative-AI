"""
Compliance, Privacy, and Deployment API Routes

Implements patent specification Sections 9, 12, 13:
- Platform configuration
- Privacy settings and consent
- Social cues (k-anonymity)
- Deployment monitoring and guardrails
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

from app.services.platform_config import (
    platform_config, 
    PlatformType, 
    PlatformSettings,
    PLATFORM_CONFIGS
)
from app.services.privacy_compliance import (
    privacy_service,
    ConsentType,
    AgeGroup,
    UserPrivacySettings
)
from app.services.deployment_monitor import (
    deployment_monitor,
    DeploymentPhase
)


router = APIRouter(prefix="/api", tags=["Compliance & Monitoring"])


# ========== Request/Response Models ==========

class PlatformTypeEnum(str, Enum):
    netflix_style = "netflix_style"
    live_streaming = "live_streaming"
    niche_content = "niche_content"
    educational = "educational"


class ConsentUpdateRequest(BaseModel):
    user_id: str
    consent_type: str  # ConsentType value
    granted: bool


class PrivacySettingsRequest(BaseModel):
    user_id: str
    disable_auto_commit: Optional[bool] = None
    custom_confidence_threshold: Optional[float] = None
    require_explicit_confirmation: Optional[bool] = None
    show_confidence_indicators: Optional[bool] = None


class ChildSafetyRequest(BaseModel):
    user_id: str
    enable: bool


class SocialCueRequest(BaseModel):
    user_id: str
    content_id: str
    taste_cluster_id: Optional[str] = None


class DeploymentPhaseRequest(BaseModel):
    phase: str  # DeploymentPhase value
    cohort_percentage: float = Field(5.0, ge=0, le=100)


class RemediationRequest(BaseModel):
    action: str


# ========== Platform Configuration ==========

@router.get("/platform/configs")
async def list_platform_configs():
    """List all available platform configurations"""
    return {
        platform.value: {
            "name": config.name,
            "commit_event": {
                "action": config.commit_event.primary_action,
                "threshold_seconds": config.commit_event.engagement_threshold_seconds,
            },
            "nru": {
                "snippet_duration": f"{config.nru_config.snippet_duration_min}-{config.nru_config.snippet_duration_max}s",
                "narrative_words": f"{config.nru_config.micro_narrative_word_min}-{config.nru_config.micro_narrative_word_max}",
            },
            "presentation": {
                "set_size": f"{config.presentation.bounded_set_min}-{config.presentation.bounded_set_max}",
                "base_exposure": config.presentation.base_exposure_time,
            },
            "hesitation_sensitivity": config.hesitation_sensitivity,
            "diversity_bonus": config.diversity_bonus,
        }
        for platform, config in PLATFORM_CONFIGS.items()
    }


@router.post("/platform/user/{user_id}")
async def set_user_platform(user_id: str, platform_type: PlatformTypeEnum):
    """Set platform type for a specific user"""
    platform = PlatformType(platform_type.value)
    platform_config.set_user_platform(user_id, platform)
    return {"user_id": user_id, "platform": platform_type.value}


@router.get("/platform/user/{user_id}/config")
async def get_user_platform_config(user_id: str):
    """Get platform configuration for a user"""
    config = platform_config.get_user_config(user_id)
    return {
        "platform": config.platform_type.value,
        "name": config.name,
        "commit_threshold_seconds": config.commit_event.engagement_threshold_seconds,
        "bounded_set_min": config.presentation.bounded_set_min,
        "bounded_set_max": config.presentation.bounded_set_max,
        "base_exposure_time": config.presentation.base_exposure_time,
    }


@router.get("/platform/user/{user_id}/bounded-set-size")
async def get_bounded_set_size(user_id: str, hesitation_score: float = 0.5):
    """Calculate optimal set size for user given hesitation"""
    size = platform_config.get_bounded_set_size(user_id, hesitation_score)
    return {"user_id": user_id, "hesitation_score": hesitation_score, "optimal_set_size": size}


# ========== Privacy & Consent ==========

@router.get("/privacy/settings/{user_id}")
async def get_privacy_settings(user_id: str):
    """Get user privacy settings"""
    settings = privacy_service.get_user_settings(user_id)
    return {
        "user_id": user_id,
        "consents": {k.value: v for k, v in settings.consents.items()},
        "age_group": settings.age_group.value,
        "child_safety_mode": settings.child_safety_mode,
        "disable_auto_commit": settings.disable_auto_commit,
        "custom_confidence_threshold": settings.custom_confidence_threshold,
        "require_explicit_confirmation": settings.require_explicit_confirmation,
        "show_confidence_indicators": settings.show_confidence_indicators,
        "retention_days": settings.retention_days,
    }


@router.post("/privacy/consent")
async def update_consent(request: ConsentUpdateRequest):
    """Update specific consent for user"""
    try:
        consent_type = ConsentType(request.consent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid consent type: {request.consent_type}")
    
    settings = privacy_service.update_consent(request.user_id, consent_type, request.granted)
    return {
        "user_id": request.user_id,
        "consent_type": request.consent_type,
        "granted": request.granted,
        "updated_at": settings.consent_updated_at
    }


@router.post("/privacy/settings")
async def update_privacy_settings(request: PrivacySettingsRequest):
    """Update privacy settings for user"""
    kwargs = {k: v for k, v in request.dict().items() if k != "user_id" and v is not None}
    settings = privacy_service.update_user_settings(request.user_id, **kwargs)
    return {"user_id": request.user_id, "updated": True}


@router.post("/privacy/child-safety")
async def toggle_child_safety(request: ChildSafetyRequest):
    """Enable or disable child safety mode"""
    if request.enable:
        settings = privacy_service.enable_child_safety_mode(request.user_id)
        return {
            "user_id": request.user_id,
            "child_safety_mode": True,
            "auto_triggers_disabled": True,
            "explicit_confirmation_required": True
        }
    else:
        settings = privacy_service.update_user_settings(
            request.user_id,
            child_safety_mode=False,
            disable_auto_commit=False,
            require_explicit_confirmation=False
        )
        return {"user_id": request.user_id, "child_safety_mode": False}


@router.get("/privacy/can-auto-trigger/{user_id}")
async def check_auto_trigger_allowed(user_id: str):
    """Check if auto-commit triggers are allowed for user"""
    can_trigger = privacy_service.can_auto_trigger(user_id)
    threshold = privacy_service.get_confidence_threshold(user_id)
    return {
        "user_id": user_id,
        "can_auto_trigger": can_trigger,
        "confidence_threshold": threshold
    }


@router.post("/privacy/opt-out/{user_id}")
async def handle_opt_out(user_id: str):
    """Handle CCPA opt-out request"""
    privacy_service.handle_opt_out_request(user_id)
    return {"user_id": user_id, "opted_out": True}


@router.get("/privacy/export/{user_id}")
async def export_user_data(user_id: str):
    """Export user data (GDPR right to access)"""
    return privacy_service.get_data_export(user_id)


@router.delete("/privacy/data/{user_id}")
async def request_data_deletion(user_id: str):
    """Request data deletion (GDPR right to deletion)"""
    privacy_service.schedule_data_deletion(user_id)
    return {"user_id": user_id, "deletion_scheduled": True}


# ========== Social Cues ==========

@router.post("/social-cue")
async def get_social_cue(request: SocialCueRequest):
    """Get privacy-preserving social cue for content"""
    # Check if user allows social cues
    if not privacy_service.has_consent(request.user_id, ConsentType.SOCIAL_CUES):
        return {"show_cue": False, "reason": "consent_not_granted"}
    
    cue = privacy_service.get_social_cue(
        request.content_id, 
        request.taste_cluster_id
    )
    
    if cue and cue.can_display:
        return {
            "show_cue": True,
            "text": cue.get_display_text(),
            "total_viewers": cue.total_viewers,
            "similar_viewers_bucket": f"{(cue.similar_taste_viewers // 10) * 10}+",
        }
    
    return {"show_cue": False, "reason": "k_anonymity_not_met"}


@router.post("/social-cue/record-view")
async def record_content_view(content_id: str, taste_cluster_id: Optional[str] = None):
    """Record a content view for social cue aggregation"""
    privacy_service.record_content_view(content_id, taste_cluster_id)
    return {"recorded": True}


# ========== Transparency Notifications ==========

@router.get("/notifications/{user_id}")
async def get_user_notifications(user_id: str, since: Optional[float] = None):
    """Get transparency notifications for user"""
    notifications = privacy_service.get_user_notifications(user_id, since)
    return {
        "user_id": user_id,
        "notifications": [
            {
                "type": n.notification_type,
                "message": n.message,
                "timestamp": n.timestamp,
                "action": n.action_taken,
                "can_undo": n.user_can_undo,
            }
            for n in notifications
        ]
    }


# ========== Deployment Monitoring ==========

@router.get("/deployment/health")
async def get_deployment_health():
    """Get system health status"""
    return deployment_monitor.get_health_status()


@router.get("/deployment/alerts")
async def get_active_alerts():
    """Get all active alerts"""
    return {"alerts": deployment_monitor.get_active_alerts()}


@router.post("/deployment/phase")
async def set_deployment_phase(request: DeploymentPhaseRequest):
    """Set deployment phase (for phased rollout)"""
    try:
        phase = DeploymentPhase(request.phase)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid phase: {request.phase}")
    
    deployment_monitor.set_deployment_phase(phase, request.cohort_percentage)
    return {
        "phase": phase.value,
        "cohort_percentage": request.cohort_percentage,
        "enabled_features": deployment_monitor.deployment_config.enabled_features
    }


@router.get("/deployment/phase")
async def get_deployment_phase():
    """Get current deployment phase"""
    config = deployment_monitor.deployment_config
    return {
        "phase": deployment_monitor.current_phase.value,
        "cohort_percentage": config.user_cohort_percentage if config else 0,
        "enabled_features": config.enabled_features if config else {},
    }


@router.get("/deployment/feature/{feature_name}")
async def check_feature_enabled(feature_name: str):
    """Check if a feature is enabled in current phase"""
    return {
        "feature": feature_name,
        "enabled": deployment_monitor.is_feature_enabled(feature_name)
    }


@router.get("/deployment/user-cohort/{user_id}")
async def check_user_cohort(user_id: str):
    """Check if user should use baseline or experiment"""
    use_baseline = deployment_monitor.should_use_baseline(user_id)
    return {
        "user_id": user_id,
        "use_baseline": use_baseline,
        "in_experiment": not use_baseline
    }


@router.post("/deployment/remediation")
async def execute_remediation(request: RemediationRequest):
    """Execute automatic remediation action"""
    result = deployment_monitor.execute_remediation(request.action)
    return result


@router.get("/deployment/remediation-actions")
async def get_remediation_actions():
    """Get list of recommended remediation actions"""
    return {"actions": deployment_monitor.get_remediation_actions()}


compliance_router = router
