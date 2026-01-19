"""
Decision State API Routes
Implements decision state encoding for reducing choice paralysis.
"""
from fastapi import APIRouter, HTTPException

from app.models import (
    DecisionStateUpdateRequest, DecisionStateResponse,
    InteractionLogRequest
)
from app.services import decision_state_service

router = APIRouter(prefix="/api/decision-state", tags=["Decision State"])


@router.post("/update", response_model=DecisionStateResponse)
async def update_decision_state(request: DecisionStateUpdateRequest):
    """
    Update user's decision state based on behavioral signals.
    
    This endpoint should be called periodically with:
    - scroll_velocity: How fast the user is scrolling
    - dwell_time: Time spent on current view (ms)
    - focus_changes: Number of back-and-forth navigations
    
    Returns:
    - Updated decision state
    - Optimal recommendation count
    - Whether intervention is needed
    - Intervention message if applicable
    """
    try:
        response = decision_state_service.update_decision_state(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=DecisionStateResponse)
async def get_decision_state(user_id: str):
    """
    Get current decision state for a user.
    
    The decision state includes:
    - stress_level: 0-1 indicating decision stress
    - scroll_velocity: Current scroll speed
    - dwell_time: Time on current view
    - focus_changes: Navigation back-and-forth count
    - confidence_score: System's confidence in recommendations
    """
    try:
        state = decision_state_service.get_decision_state(user_id)
        recommendation_count = decision_state_service._calculate_recommendation_count(state)
        
        return DecisionStateResponse(
            user_id=user_id,
            decision_state=state,
            recommendation_count=recommendation_count,
            should_intervene=state.stress_level > 0.7,
            intervention_message=decision_state_service._generate_intervention_message(state) 
                if state.stress_level > 0.7 else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-interaction")
async def log_interaction(request: InteractionLogRequest):
    """
    Log a user interaction for decision state analysis.
    
    Interaction types:
    - view: User viewed a recommendation
    - skip: User skipped to next
    - select: User selected to watch
    - dismiss: User dismissed without selection
    - replay: User replayed a recommendation
    """
    try:
        # Get current state and apply interaction adjustment
        update_request = DecisionStateUpdateRequest(
            user_id=request.user_id,
            scroll_velocity=0,
            dwell_time=request.view_duration * 1000,  # Convert to ms
            focus_changes=0,
            interaction_type=request.action
        )
        
        response = decision_state_service.update_decision_state(update_request)
        
        return {
            "status": "logged",
            "user_id": request.user_id,
            "action": request.action,
            "new_stress_level": response.decision_state.stress_level
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/summary")
async def get_session_summary(user_id: str):
    """
    Get a summary of the user's decision-making session.
    
    Returns:
    - Current stress level
    - Total interactions
    - Interaction breakdown by type
    - Recommendation quality assessment
    """
    try:
        summary = decision_state_service.get_session_summary(user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/reset")
async def reset_session(user_id: str):
    """Reset decision state for a new session"""
    try:
        decision_state_service.reset_session(user_id)
        return {"status": "reset", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/search-rewrite")
async def track_search_rewrite(user_id: str):
    """
    Track when user rewrites their search query.
    Multiple rewrites indicate confusion and increase stress.
    """
    try:
        decision_state_service.increment_search_rewrites(user_id)
        state = decision_state_service.get_decision_state(user_id)
        
        return {
            "status": "tracked",
            "user_id": user_id,
            "search_rewrites": state.search_rewrites,
            "stress_level": state.stress_level
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
