"""
Pydantic models for Sequential Narrative AI API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# Enums
class ContentType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"
    DOCUMENTARY = "documentary"
    VIDEO = "video"


class ContentMood(str, Enum):
    THRILLING = "thrilling"
    HEARTWARMING = "heartwarming"
    THOUGHT_PROVOKING = "thought-provoking"
    RELAXING = "relaxing"
    EXCITING = "exciting"
    DARK = "dark"
    UPLIFTING = "uplifting"
    MYSTERIOUS = "mysterious"
    ROMANTIC = "romantic"
    COMEDIC = "comedic"
    INTENSE = "intense"
    ESCAPIST = "escapist"
    COZY = "cozy"


class IntentAction(str, Enum):
    RECOMMEND = "recommend"
    SEARCH = "search"
    EXPLORE = "explore"
    CONTINUE = "continue"


class InteractionType(str, Enum):
    VIEW = "view"
    SKIP = "skip"
    SELECT = "select"
    DISMISS = "dismiss"
    REPLAY = "replay"


# Content Models
class Content(BaseModel):
    id: str
    title: str
    type: ContentType
    genre: List[str]
    year: int
    rating: float
    duration: str
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    description: str
    cast: List[str] = []
    director: str = ""
    themes: List[str] = []
    mood: List[ContentMood] = []
    standout_scenes: List[str] = []
    fun_facts: List[str] = []
    trailer_url: Optional[str] = None
    streaming_url: Optional[str] = None
    provider: Optional[str] = None


# User Models
class ViewingRecord(BaseModel):
    content_id: str
    watched_at: datetime
    completion_rate: float = Field(ge=0, le=1)
    rewatched: bool = False
    rating: Optional[float] = Field(None, ge=0, le=5)
    engagement_score: float = Field(ge=0, le=1)


class UserPreferences(BaseModel):
    favorite_genres: List[str] = []
    disliked_genres: List[str] = []
    preferred_moods: List[ContentMood] = []
    preferred_duration: str = "medium"
    maturity_rating: str = "R"


class InteractionSignal(BaseModel):
    """Single interaction signal in the telemetry stream"""
    timestamp: float = Field(..., description="Unix timestamp in ms")
    signal_type: str = Field(..., description="Type: scroll, dwell, focus, skip, replay")
    value: float = Field(..., description="Signal value")
    metadata: Optional[dict] = None


class DecisionState(BaseModel):
    """
    Decision state vector for reducing choice deferral.
    Encodes behavioral signals that indicate decision stress.
    """
    stress_level: float = Field(0.3, ge=0, le=1, description="Derived from browsing patterns")
    scroll_velocity: float = Field(0, ge=0, description="How fast user is scrolling")
    dwell_time: float = Field(0, ge=0, description="Time spent on current view (ms)")
    focus_changes: int = Field(0, ge=0, description="Number of back-and-forth navigations")
    search_rewrites: int = Field(0, ge=0, description="How many times search was modified")
    confidence_score: float = Field(0.7, ge=0, le=1, description="System's confidence in recommendations")


class EnhancedDecisionState(BaseModel):
    """
    Enhanced decision state vector with patent-aligned fields.
    Implements multi-head prediction architecture outputs.
    """
    # Core behavioral signals (from base DecisionState)
    stress_level: float = Field(0.3, ge=0, le=1, description="Derived from browsing patterns")
    scroll_velocity: float = Field(0, ge=0, description="How fast user is scrolling (px/s)")
    dwell_time: float = Field(0, ge=0, description="Time spent on current view (ms)")
    focus_changes: int = Field(0, ge=0, description="Number of back-and-forth navigations")
    search_rewrites: int = Field(0, ge=0, description="How many times search was modified")
    
    # Multi-head encoder outputs
    commit_probability: float = Field(0.5, ge=0, le=1, description="P(commit|x) - likelihood user will select content")
    hesitation_score: float = Field(0.3, ge=0, le=1, description="η(x) - explicit ambivalence measure")
    hazard_rate: float = Field(0.1, ge=0, le=1, description="h(t|x) - instantaneous commit probability")
    survival_probability: float = Field(0.9, ge=0, le=1, description="S(t) - probability user hasn't committed yet")
    epistemic_uncertainty: float = Field(0.2, ge=0, le=1, description="σ(x) - model uncertainty estimate")
    
    # Temporal context
    time_in_session: float = Field(0, ge=0, description="Seconds since session start")
    session_start_timestamp: float = Field(0, description="Unix timestamp of session start")
    
    # Windowed interaction tensor (last 30 seconds normalized)
    interaction_window: List[float] = Field(default_factory=list, description="Last 30s of normalized signals")
    
    # Derived metrics
    optimal_set_size: int = Field(4, ge=2, le=5, description="n = f(hesitation) - cognitive load aware")
    confidence_score: float = Field(0.7, ge=0, le=1, description="System's confidence in recommendations")
    should_reduce_choices: bool = Field(False, description="Flag when hesitation is high")
    predicted_time_to_commit: float = Field(30.0, ge=0, description="Expected seconds until user commits")


class ContextualSignals(BaseModel):
    time_of_day: str = "evening"
    day_of_week: str = "Saturday"
    device: str = "desktop"
    session_duration: float = 0
    previous_sessions: int = 0


class UserProfile(BaseModel):
    id: str
    viewing_history: List[ViewingRecord] = []
    preferences: UserPreferences = UserPreferences()
    decision_state: DecisionState = DecisionState()
    contextual_signals: ContextualSignals = ContextualSignals()


# NLP Models
class NLPIntent(BaseModel):
    """Parsed intent from natural language query"""
    action: IntentAction = IntentAction.RECOMMEND
    context: str = "general"
    preferences: List[str] = []
    mood: Optional[ContentMood] = None
    urgency: str = "normal"
    constraints: List[str] = []
    raw_query: str = ""
    confidence: float = Field(0.8, ge=0, le=1)


# Micro-Pitch Models
class MicroPitch(BaseModel):
    """7-10 second narrative pitch for a recommendation"""
    script: str = Field(..., description="Full narration script")
    headline: str
    hook: str
    personalized_reason: str
    standout_moment: str
    fun_fact: str
    call_to_action: str
    estimated_duration_seconds: float = Field(8.0, ge=0)  # Removed upper limit for flexibility


# Recommendation Models
class Recommendation(BaseModel):
    content: Content
    match_score: float = Field(..., ge=0, le=100)
    reasoning: str
    micro_pitch: MicroPitch
    sequence_position: int
    diversity_contribution: float
    
    # DPP kernel outputs
    quality_score: float = Field(0.0, ge=0, le=1, description="q_i from DPP L-matrix")
    dpp_marginal: float = Field(0.0, ge=0, le=1, description="Marginal inclusion probability from DPP")
    
    # Confidence uplift
    confidence_uplift: float = Field(0.0, description="Expected confidence gain from showing this item")


# Request/Response Models
class RecommendationRequest(BaseModel):
    query: Optional[str] = None
    user_profile: UserProfile
    constraints: Optional[dict] = None


class RecommendationResponse(BaseModel):
    recommendations: List[Recommendation]
    processing_time_ms: float
    confidence: float
    diversity_score: float
    decision_support_score: float
    narrative_intro: str
    
    # Patent-aligned metrics
    dpp_log_det: float = Field(0.0, description="log det(L_S) - DPP diversity measure")
    hesitation_adjusted: bool = Field(False, description="Whether set size was adjusted for hesitation")
    optimal_set_size_used: int = Field(4, ge=2, le=5, description="Actual set size used")
    hazard_rate_at_generation: float = Field(0.1, ge=0, le=1, description="Hazard rate when generated")
    predicted_commit_probability: float = Field(0.5, ge=0, le=1, description="Expected P(commit)")


class NLPProcessRequest(BaseModel):
    query: str
    user_context: Optional[dict] = None


class NLPProcessResponse(BaseModel):
    intent: NLPIntent
    narrative: str
    suggested_prompts: List[str]


class DecisionStateUpdateRequest(BaseModel):
    user_id: str
    scroll_velocity: float
    dwell_time: float
    focus_changes: int
    interaction_type: Optional[InteractionType] = None


class TelemetryEvent(BaseModel):
    """Real-time telemetry event from frontend"""
    user_id: str
    timestamp: float = Field(..., description="Unix timestamp in ms")
    event_type: str = Field(..., description="scroll, dwell, focus, skip, replay, micro_pause")
    value: float = Field(..., description="Event value")
    content_id: Optional[str] = None
    metadata: Optional[dict] = None


class TelemetryBatch(BaseModel):
    """Batch of telemetry events for WebSocket transmission"""
    user_id: str
    session_id: str
    events: List[TelemetryEvent]
    window_start: float = Field(..., description="Start of telemetry window (Unix ms)")
    window_end: float = Field(..., description="End of telemetry window (Unix ms)")


class DecisionStateResponse(BaseModel):
    user_id: str
    decision_state: DecisionState
    recommendation_count: int = Field(..., description="Optimal number of recommendations based on stress")
    should_intervene: bool = Field(..., description="Whether to proactively help user")
    intervention_message: Optional[str] = None


class EnhancedDecisionStateResponse(BaseModel):
    """Response with full patent-aligned decision state"""
    user_id: str
    decision_state: EnhancedDecisionState
    
    # DPP-based recommendations
    optimal_set_size: int = Field(..., description="Cognitively optimal number of recommendations")
    diversity_requirement: float = Field(..., ge=0, le=1, description="Required diversity based on hesitation")
    
    # Hazard model outputs
    hazard_rate: float = Field(..., ge=0, le=1, description="Current instantaneous commit probability")
    survival_probability: float = Field(..., ge=0, le=1, description="Probability user hasn't committed")
    predicted_time_to_commit: float = Field(..., ge=0, description="Expected seconds until commit")
    
    # Intervention guidance
    should_intervene: bool = Field(..., description="Whether to proactively help user")
    intervention_type: Optional[str] = Field(None, description="reduce_choices, simplify_ui, offer_help")
    intervention_message: Optional[str] = None
    
    # Confidence metrics
    model_confidence: float = Field(..., ge=0, le=1, description="Confidence in predictions")
    uncertainty_band: List[float] = Field(default_factory=list, description="[lower, upper] confidence interval")


class AudioGenerationRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = Field(1.0, ge=0.5, le=2.0)


class AudioGenerationResponse(BaseModel):
    audio_url: str
    duration_seconds: float
    text: str


class InteractionLogRequest(BaseModel):
    user_id: str
    content_id: str
    action: InteractionType
    view_duration: float = 0
    timestamp: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict
