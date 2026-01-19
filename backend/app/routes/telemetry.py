"""
Telemetry Routes for Real-Time Behavioral Signal Processing

Implements WebSocket and HTTP endpoints for:
- Real-time telemetry ingestion
- Multi-head decision state updates
- Enhanced decision state responses
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Optional
import asyncio
import json
import time

from app.models import (
    TelemetryEvent,
    TelemetryBatch,
    DecisionState,
    EnhancedDecisionState,
    EnhancedDecisionStateResponse
)
from app.services.multi_head_encoder import multi_head_encoder
from app.services.survival_model import hazard_model
from app.services.dpp_kernel import dpp_selector

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


# In-memory session storage (in production, use Redis)
class SessionStore:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.websockets: Dict[str, WebSocket] = {}
    
    def get_session(self, user_id: str) -> Dict:
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'start_time': time.time(),
                'events': [],
                'decision_state': DecisionState(),
                'enhanced_state': None,
            }
        return self.sessions[user_id]
    
    def add_events(self, user_id: str, events: List[TelemetryEvent]):
        session = self.get_session(user_id)
        session['events'].extend(events)
        
        # Keep only last 60 seconds of events
        cutoff = time.time() * 1000 - 60000
        session['events'] = [e for e in session['events'] if e.timestamp > cutoff]
    
    def get_time_in_session(self, user_id: str) -> float:
        session = self.get_session(user_id)
        return time.time() - session['start_time']
    
    def update_decision_state(self, user_id: str, events: List[TelemetryEvent]) -> EnhancedDecisionState:
        session = self.get_session(user_id)
        
        # Aggregate events into base decision state
        base_state = self._aggregate_to_decision_state(events, session)
        
        # Get time in session
        time_in_session = self.get_time_in_session(user_id)
        
        # Create enhanced state using multi-head encoder
        enhanced_state = multi_head_encoder.create_enhanced_decision_state(
            base_state,
            events,
            time_in_session
        )
        
        session['decision_state'] = base_state
        session['enhanced_state'] = enhanced_state
        
        return enhanced_state
    
    def _aggregate_to_decision_state(
        self,
        events: List[TelemetryEvent],
        session: Dict
    ) -> DecisionState:
        """Aggregate telemetry events into base decision state"""
        if not events:
            return session.get('decision_state', DecisionState())
        
        # Calculate aggregates
        scroll_events = [e.value for e in events if e.event_type == 'scroll']
        dwell_events = [e.value for e in events if e.event_type == 'dwell']
        focus_events = [e for e in events if e.event_type == 'focus']
        
        avg_scroll = sum(scroll_events) / len(scroll_events) if scroll_events else 0
        avg_dwell = sum(dwell_events) / len(dwell_events) if dwell_events else 0
        focus_count = len(focus_events)
        
        # Calculate stress level
        scroll_factor = min(avg_scroll / 1000, 1) * 0.3
        dwell_factor = (1 - min(avg_dwell / 30000, 1)) * 0.3  # Low dwell = high stress
        focus_factor = min(focus_count / 10, 1) * 0.4
        stress_level = scroll_factor + dwell_factor + focus_factor
        
        return DecisionState(
            stress_level=stress_level,
            scroll_velocity=avg_scroll,
            dwell_time=avg_dwell,
            focus_changes=focus_count,
            search_rewrites=0,  # Would come from search events
            confidence_score=0.7
        )


session_store = SessionStore()


@router.post("/batch")
async def receive_telemetry_batch(batch: TelemetryBatch):
    """
    Receive batch of telemetry events via HTTP.
    
    Returns enhanced decision state computed from multi-head encoder.
    """
    # Store events
    session_store.add_events(batch.user_id, batch.events)
    
    # Get all recent events
    session = session_store.get_session(batch.user_id)
    all_events = session['events']
    
    # Update decision state
    enhanced_state = session_store.update_decision_state(batch.user_id, all_events)
    
    # Compute intervention guidance
    survival_pred = hazard_model.predict_time_to_commit(
        session['decision_state'],
        session_store.get_time_in_session(batch.user_id)
    )
    
    should_intervene, intervention_type, confidence = hazard_model.should_trigger_intervention(
        session['decision_state'],
        session_store.get_time_in_session(batch.user_id)
    )
    
    # Build response
    return {
        "user_id": batch.user_id,
        "enhanced_state": enhanced_state.model_dump(),
        "intervention": {
            "should_intervene": should_intervene,
            "type": intervention_type,
            "confidence": confidence
        },
        "survival_analysis": {
            "hazard_rate": survival_pred.hazard_rate,
            "survival_probability": survival_pred.survival_probability,
            "expected_time_to_commit": survival_pred.expected_time_to_commit
        }
    }


@router.get("/state/{user_id}", response_model=EnhancedDecisionStateResponse)
async def get_enhanced_decision_state(user_id: str):
    """
    Get current enhanced decision state for a user.
    """
    session = session_store.get_session(user_id)
    events = session['events']
    
    # Update state
    enhanced_state = session_store.update_decision_state(user_id, events)
    time_in_session = session_store.get_time_in_session(user_id)
    
    # Get survival prediction
    survival_pred = hazard_model.predict_time_to_commit(
        session['decision_state'],
        time_in_session
    )
    
    # Check intervention
    should_intervene, intervention_type, confidence = hazard_model.should_trigger_intervention(
        session['decision_state'],
        time_in_session
    )
    
    return EnhancedDecisionStateResponse(
        user_id=user_id,
        decision_state=enhanced_state,
        optimal_set_size=enhanced_state.optimal_set_size,
        diversity_requirement=0.5 + 0.3 * enhanced_state.hesitation_score,
        hazard_rate=survival_pred.hazard_rate,
        survival_probability=survival_pred.survival_probability,
        predicted_time_to_commit=survival_pred.expected_time_to_commit,
        should_intervene=should_intervene,
        intervention_type=intervention_type if should_intervene else None,
        intervention_message=_get_intervention_message(intervention_type) if should_intervene else None,
        model_confidence=enhanced_state.confidence_score,
        uncertainty_band=[
            survival_pred.confidence_interval[0],
            survival_pred.confidence_interval[1]
        ]
    )


def _get_intervention_message(intervention_type: str) -> str:
    """Get user-facing message for intervention type"""
    messages = {
        "reduce_choices": "Let me narrow down some options for you...",
        "simplify_ui": "How about we focus on just a few picks?",
        "offer_help": "Need some help deciding? I can suggest something perfect for right now."
    }
    return messages.get(intervention_type, "")


# WebSocket handler function (called from main.py)
async def telemetry_websocket_handler(websocket: WebSocket, user_id: str):
    """
    WebSocket handler for real-time telemetry streaming.
    
    Receives telemetry batches and returns enhanced decision state updates.
    """
    await websocket.accept()
    session_store.websockets[user_id] = websocket
    
    try:
        while True:
            # Receive telemetry batch
            data = await websocket.receive_text()
            
            try:
                batch_data = json.loads(data)
                
                # Parse events - handle both snake_case and camelCase
                events = [
                    TelemetryEvent(
                        user_id=batch_data.get('user_id') or batch_data.get('userId', user_id),
                        timestamp=e.get('timestamp', time.time() * 1000),
                        event_type=e.get('event_type') or e.get('eventType', 'unknown'),
                        value=e.get('value', 0),
                        content_id=e.get('content_id') or e.get('contentId'),
                        metadata=e.get('metadata')
                    )
                    for e in batch_data.get('events', [])
                ]
                
                # Store events
                session_store.add_events(user_id, events)
                
                # Update and get enhanced state
                session = session_store.get_session(user_id)
                all_events = session['events']
                enhanced_state = session_store.update_decision_state(user_id, all_events)
                
                # Send back enhanced state
                response = {
                    "type": "state_update",
                    "enhanced_state": enhanced_state.model_dump(),
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send_text(json.dumps(response))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
    
    except WebSocketDisconnect:
        if user_id in session_store.websockets:
            del session_store.websockets[user_id]
    except Exception:
        if user_id in session_store.websockets:
            del session_store.websockets[user_id]


# Periodic state broadcast (optional)
async def broadcast_state_updates():
    """Background task to periodically send state updates to connected clients"""
    while True:
        await asyncio.sleep(5)  # Every 5 seconds
        
        for user_id, websocket in list(session_store.websockets.items()):
            try:
                session = session_store.get_session(user_id)
                if session.get('enhanced_state'):
                    await websocket.send_text(json.dumps({
                        "type": "periodic_update",
                        "enhanced_state": session['enhanced_state'].model_dump(),
                        "timestamp": time.time() * 1000
                    }))
            except Exception:
                # Connection might be closed
                pass


telemetry_router = router
