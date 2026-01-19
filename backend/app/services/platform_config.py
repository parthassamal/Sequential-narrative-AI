"""
Streaming Platform Configuration

Implements patent specification Section 9:
- Platform-specific commit events and NRU configurations
- Netflix/Prime Video: 90-second engagement threshold
- Live Streaming (Twitch/YouTube Live): 30-second stay
- Niche Content: Longer narratives, fewer options
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class PlatformType(Enum):
    """Supported streaming platform types"""
    NETFLIX_STYLE = "netflix_style"  # Netflix, Prime Video, Disney+, HBO Max
    LIVE_STREAMING = "live_streaming"  # Twitch, YouTube Live
    NICHE_CONTENT = "niche_content"  # Film festivals, arthouse, documentaries
    EDUCATIONAL = "educational"  # Coursera, Udemy, Khan Academy
    ECOMMERCE = "ecommerce"  # Product recommendations
    APP_DISCOVERY = "app_discovery"  # App stores


@dataclass
class CommitEventConfig:
    """Configuration for what constitutes a "commit" event"""
    primary_action: str  # e.g., "playback_start"
    engagement_threshold_seconds: float  # Time user must stay engaged
    secondary_signals: List[str] = field(default_factory=list)  # Additional signals
    
    def is_valid_commit(self, action: str, engagement_time: float) -> bool:
        """Check if user action + engagement time constitutes a valid commit"""
        return (
            action == self.primary_action and 
            engagement_time >= self.engagement_threshold_seconds
        )


@dataclass
class NRUConfig:
    """Narrative Recommendation Unit configuration"""
    snippet_duration_min: float  # Minimum snippet duration (seconds)
    snippet_duration_max: float  # Maximum snippet duration (seconds)
    metadata_word_limit: int  # Max words for metadata summary
    micro_narrative_word_min: int  # Min words for micro-narrative
    micro_narrative_word_max: int  # Max words for micro-narrative
    include_social_cues: bool  # Show "People with your taste..." messages
    social_cue_min_users: int  # Minimum users for privacy (k-anonymity)


@dataclass
class PresentationConfig:
    """Sequential presentation configuration"""
    bounded_set_min: int  # Minimum items in recommendation set
    bounded_set_max: int  # Maximum items in recommendation set
    base_exposure_time: float  # Base time per NRU (seconds)
    auto_advance_enabled: bool  # Whether to auto-advance between NRUs
    

@dataclass
class PlatformSettings:
    """Complete platform-specific configuration"""
    platform_type: PlatformType
    name: str
    commit_event: CommitEventConfig
    nru_config: NRUConfig
    presentation: PresentationConfig
    
    # Behavioral adjustments
    hesitation_sensitivity: float = 1.0  # Multiplier for hesitation detection
    diversity_bonus: float = 1.0  # Multiplier for diversity reward
    stress_weight: float = 1.0  # Weight for stress in reward function
    

# ========== Platform Presets ==========

NETFLIX_STYLE_CONFIG = PlatformSettings(
    platform_type=PlatformType.NETFLIX_STYLE,
    name="Netflix/Prime Style",
    commit_event=CommitEventConfig(
        primary_action="playback_start",
        engagement_threshold_seconds=90.0,  # Must watch 90+ seconds
        secondary_signals=["completion_rate", "rewind", "pause_resume"]
    ),
    nru_config=NRUConfig(
        snippet_duration_min=6.0,
        snippet_duration_max=12.0,
        metadata_word_limit=100,
        micro_narrative_word_min=30,
        micro_narrative_word_max=45,
        include_social_cues=True,
        social_cue_min_users=100  # k-anonymity threshold
    ),
    presentation=PresentationConfig(
        bounded_set_min=3,
        bounded_set_max=7,
        base_exposure_time=10.0,
        auto_advance_enabled=True
    ),
    hesitation_sensitivity=1.0,
    diversity_bonus=1.0,
    stress_weight=1.0
)


LIVE_STREAMING_CONFIG = PlatformSettings(
    platform_type=PlatformType.LIVE_STREAMING,
    name="Live Streaming (Twitch/YouTube Live)",
    commit_event=CommitEventConfig(
        primary_action="stream_join",
        engagement_threshold_seconds=30.0,  # Shorter threshold for live
        secondary_signals=["chat_interaction", "follow", "subscribe"]
    ),
    nru_config=NRUConfig(
        snippet_duration_min=8.0,
        snippet_duration_max=15.0,  # Longer for live context
        metadata_word_limit=50,  # Shorter, more urgent
        micro_narrative_word_min=15,
        micro_narrative_word_max=25,  # "Popular streamer. 50K viewers."
        include_social_cues=True,
        social_cue_min_users=50  # Lower threshold for live popularity
    ),
    presentation=PresentationConfig(
        bounded_set_min=2,
        bounded_set_max=5,  # Fewer options (live content is time-sensitive)
        base_exposure_time=8.0,
        auto_advance_enabled=True
    ),
    hesitation_sensitivity=0.8,  # Less sensitive (users expect quick decisions)
    diversity_bonus=0.8,  # Less diversity needed
    stress_weight=0.7  # Live browsing less stressful (FOMO-driven)
)


NICHE_CONTENT_CONFIG = PlatformSettings(
    platform_type=PlatformType.NICHE_CONTENT,
    name="Niche/Arthouse Content",
    commit_event=CommitEventConfig(
        primary_action="playback_start",
        engagement_threshold_seconds=120.0,  # Longer engagement for arthouse
        secondary_signals=["completion_rate", "add_to_list", "share"]
    ),
    nru_config=NRUConfig(
        snippet_duration_min=10.0,
        snippet_duration_max=20.0,  # Longer, more atmospheric snippets
        metadata_word_limit=150,  # More context for unfamiliar content
        micro_narrative_word_min=45,
        micro_narrative_word_max=70,  # Longer, more descriptive
        include_social_cues=True,
        social_cue_min_users=100
    ),
    presentation=PresentationConfig(
        bounded_set_min=2,
        bounded_set_max=4,  # Fewer options (high cognitive load)
        base_exposure_time=15.0,  # More time to consider
        auto_advance_enabled=False  # Manual control preferred
    ),
    hesitation_sensitivity=1.5,  # High sensitivity (users hesitate more)
    diversity_bonus=1.5,  # Encourage cross-cultural exposure
    stress_weight=1.3  # Higher weight (stress more common)
)


EDUCATIONAL_CONFIG = PlatformSettings(
    platform_type=PlatformType.EDUCATIONAL,
    name="Educational Content",
    commit_event=CommitEventConfig(
        primary_action="course_start",
        engagement_threshold_seconds=180.0,  # Complete intro lesson
        secondary_signals=["quiz_attempt", "notes_taken", "bookmark"]
    ),
    nru_config=NRUConfig(
        snippet_duration_min=15.0,
        snippet_duration_max=30.0,  # Preview lecture content
        metadata_word_limit=120,
        micro_narrative_word_min=40,
        micro_narrative_word_max=60,
        include_social_cues=True,
        social_cue_min_users=200
    ),
    presentation=PresentationConfig(
        bounded_set_min=3,
        bounded_set_max=6,
        base_exposure_time=12.0,
        auto_advance_enabled=False
    ),
    hesitation_sensitivity=1.2,
    diversity_bonus=1.0,
    stress_weight=1.2
)


# Platform registry
PLATFORM_CONFIGS: Dict[PlatformType, PlatformSettings] = {
    PlatformType.NETFLIX_STYLE: NETFLIX_STYLE_CONFIG,
    PlatformType.LIVE_STREAMING: LIVE_STREAMING_CONFIG,
    PlatformType.NICHE_CONTENT: NICHE_CONTENT_CONFIG,
    PlatformType.EDUCATIONAL: EDUCATIONAL_CONFIG,
}


class PlatformConfigManager:
    """
    Manages platform-specific configurations for the recommendation system.
    """
    
    def __init__(self, default_platform: PlatformType = PlatformType.NETFLIX_STYLE):
        self.default_platform = default_platform
        self.user_platform_overrides: Dict[str, PlatformType] = {}
    
    def get_config(self, platform_type: Optional[PlatformType] = None) -> PlatformSettings:
        """Get configuration for specified platform or default"""
        platform = platform_type or self.default_platform
        return PLATFORM_CONFIGS.get(platform, NETFLIX_STYLE_CONFIG)
    
    def set_user_platform(self, user_id: str, platform_type: PlatformType):
        """Set platform preference for a specific user"""
        self.user_platform_overrides[user_id] = platform_type
    
    def get_user_config(self, user_id: str) -> PlatformSettings:
        """Get configuration for a specific user"""
        platform = self.user_platform_overrides.get(user_id, self.default_platform)
        return self.get_config(platform)
    
    def is_valid_commit(
        self,
        user_id: str,
        action: str,
        engagement_time: float
    ) -> bool:
        """Check if action constitutes a valid commit for user's platform"""
        config = self.get_user_config(user_id)
        return config.commit_event.is_valid_commit(action, engagement_time)
    
    def get_bounded_set_size(
        self,
        user_id: str,
        hesitation_score: float
    ) -> int:
        """
        Compute platform-adjusted bounded set size.
        
        n = max(n_min, min(n_max, round(n_max - γ × sensitivity × η)))
        """
        config = self.get_user_config(user_id)
        sensitivity = config.hesitation_sensitivity
        
        raw_size = config.presentation.bounded_set_max - 3 * sensitivity * hesitation_score
        return max(
            config.presentation.bounded_set_min,
            min(config.presentation.bounded_set_max, round(raw_size))
        )
    
    def get_adjusted_reward_weights(
        self,
        user_id: str
    ) -> Dict[str, float]:
        """Get platform-adjusted reward weights"""
        config = self.get_user_config(user_id)
        
        # Base weights from reward_engine
        base_weights = {
            "defer": 0.25,
            "abandon": 0.30,
            "stress": 0.20,
            "trigger": 0.15,
            "diversity": 0.10,
        }
        
        # Apply platform adjustments
        adjusted = base_weights.copy()
        adjusted["stress"] *= config.stress_weight
        adjusted["diversity"] *= config.diversity_bonus
        
        # Renormalize
        total = sum(adjusted.values())
        return {k: v/total for k, v in adjusted.items()}


# Singleton instance
platform_config = PlatformConfigManager()
