"""
Privacy, Compliance, and Governance Service

Implements patent specification Section 12:
- Privacy-preserving social cues (k-anonymity)
- GDPR/CCPA compliance
- User control settings
- Child safety mode
- Transparency notifications
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import time


class ConsentType(Enum):
    """Types of user consent"""
    PERSONALIZATION = "personalization"
    MICRO_SURVEYS = "micro_surveys"
    SOCIAL_CUES = "social_cues"
    AUTO_TRIGGERS = "auto_triggers"
    DATA_RETENTION_EXTENDED = "data_retention_extended"


class AgeGroup(Enum):
    """User age groups for content restrictions"""
    CHILD = "child"  # Under 13
    TEEN = "teen"  # 13-17
    ADULT = "adult"  # 18+
    UNKNOWN = "unknown"


@dataclass
class UserPrivacySettings:
    """User-specific privacy and control settings"""
    user_id: str
    
    # Consent flags
    consents: Dict[ConsentType, bool] = field(default_factory=lambda: {
        ConsentType.PERSONALIZATION: True,
        ConsentType.MICRO_SURVEYS: False,
        ConsentType.SOCIAL_CUES: True,
        ConsentType.AUTO_TRIGGERS: True,
        ConsentType.DATA_RETENTION_EXTENDED: False,
    })
    
    # Age and safety
    age_group: AgeGroup = AgeGroup.UNKNOWN
    child_safety_mode: bool = False
    
    # Trigger controls
    disable_auto_commit: bool = False
    custom_confidence_threshold: Optional[float] = None  # User-set threshold
    require_explicit_confirmation: bool = False
    
    # Data retention
    retention_days: int = 90  # Default 90 days per GDPR
    
    # Transparency
    show_confidence_indicators: bool = True
    show_why_recommended: bool = True
    
    # Timestamps
    consent_updated_at: float = field(default_factory=time.time)
    settings_updated_at: float = field(default_factory=time.time)


@dataclass
class SocialCueData:
    """Aggregated social cue data with privacy guarantees"""
    content_id: str
    total_viewers: int
    similar_taste_viewers: int
    k_threshold: int  # Minimum users for display
    
    @property
    def can_display(self) -> bool:
        """Check if k-anonymity threshold is met"""
        return self.similar_taste_viewers >= self.k_threshold
    
    def get_display_text(self) -> Optional[str]:
        """Get privacy-safe display text"""
        if not self.can_display:
            return None
        
        # Round to avoid precise identification
        if self.similar_taste_viewers >= 10000:
            viewers_text = f"{self.similar_taste_viewers // 1000}K+"
        elif self.similar_taste_viewers >= 1000:
            viewers_text = f"{(self.similar_taste_viewers // 100) * 100}+"
        else:
            viewers_text = f"{(self.similar_taste_viewers // 10) * 10}+"
        
        return f"People with your taste are watching this ({viewers_text})"


@dataclass 
class TransparencyNotification:
    """Notification for user about system actions"""
    notification_type: str
    message: str
    timestamp: float
    action_taken: str
    user_can_undo: bool = False
    undo_window_seconds: float = 30.0


class PrivacyComplianceService:
    """
    Privacy and Compliance Management
    
    Implements:
    - K-anonymity for social cues
    - GDPR/CCPA data handling
    - User control over triggers
    - Child safety features
    - Transparency notifications
    """
    
    # K-anonymity thresholds
    DEFAULT_K_THRESHOLD = 100
    LIVE_STREAMING_K_THRESHOLD = 50
    
    # Data retention
    DEFAULT_RETENTION_DAYS = 90
    EXTENDED_RETENTION_DAYS = 365
    
    def __init__(self):
        # User settings storage
        self._user_settings: Dict[str, UserPrivacySettings] = {}
        
        # Aggregated viewing data (content_id -> count)
        self._content_view_counts: Dict[str, int] = {}
        
        # Taste cluster counts (cluster_id -> content_id -> count)
        self._taste_cluster_counts: Dict[str, Dict[str, int]] = {}
        
        # Pending notifications
        self._user_notifications: Dict[str, List[TransparencyNotification]] = {}
        
        # Data scheduled for deletion
        self._deletion_queue: List[tuple] = []
    
    def get_user_settings(self, user_id: str) -> UserPrivacySettings:
        """Get or create user privacy settings"""
        if user_id not in self._user_settings:
            self._user_settings[user_id] = UserPrivacySettings(user_id=user_id)
        return self._user_settings[user_id]
    
    def update_user_settings(
        self,
        user_id: str,
        **kwargs
    ) -> UserPrivacySettings:
        """Update user privacy settings"""
        settings = self.get_user_settings(user_id)
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.settings_updated_at = time.time()
        return settings
    
    def update_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool
    ) -> UserPrivacySettings:
        """Update specific consent"""
        settings = self.get_user_settings(user_id)
        settings.consents[consent_type] = granted
        settings.consent_updated_at = time.time()
        return settings
    
    def has_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has granted specific consent"""
        settings = self.get_user_settings(user_id)
        return settings.consents.get(consent_type, False)
    
    def enable_child_safety_mode(self, user_id: str) -> UserPrivacySettings:
        """
        Enable child safety mode (Section 12.3):
        - Disable automated triggers
        - Require explicit confirmation
        """
        settings = self.get_user_settings(user_id)
        settings.child_safety_mode = True
        settings.age_group = AgeGroup.CHILD
        settings.disable_auto_commit = True
        settings.require_explicit_confirmation = True
        settings.consents[ConsentType.AUTO_TRIGGERS] = False
        settings.settings_updated_at = time.time()
        return settings
    
    def can_auto_trigger(self, user_id: str) -> bool:
        """Check if auto-commit triggers are allowed for user"""
        settings = self.get_user_settings(user_id)
        
        # Child safety mode disables triggers
        if settings.child_safety_mode:
            return False
        
        # User explicitly disabled
        if settings.disable_auto_commit:
            return False
        
        # Check consent
        return settings.consents.get(ConsentType.AUTO_TRIGGERS, True)
    
    def get_confidence_threshold(self, user_id: str, default: float = 0.7) -> float:
        """Get user's confidence threshold (custom or default)"""
        settings = self.get_user_settings(user_id)
        
        # Child safety mode uses very high threshold
        if settings.child_safety_mode:
            return 0.99
        
        return settings.custom_confidence_threshold or default
    
    # ========== Social Cues (K-Anonymity) ==========
    
    def record_content_view(
        self,
        content_id: str,
        taste_cluster_id: Optional[str] = None
    ):
        """Record a content view for social cue aggregation"""
        # Global view count
        self._content_view_counts[content_id] = \
            self._content_view_counts.get(content_id, 0) + 1
        
        # Taste cluster count
        if taste_cluster_id:
            if taste_cluster_id not in self._taste_cluster_counts:
                self._taste_cluster_counts[taste_cluster_id] = {}
            
            cluster_counts = self._taste_cluster_counts[taste_cluster_id]
            cluster_counts[content_id] = cluster_counts.get(content_id, 0) + 1
    
    def get_social_cue(
        self,
        content_id: str,
        taste_cluster_id: Optional[str] = None,
        k_threshold: int = None
    ) -> Optional[SocialCueData]:
        """
        Get privacy-preserving social cue for content.
        
        Only returns data if k-anonymity threshold is met.
        """
        k = k_threshold or self.DEFAULT_K_THRESHOLD
        
        total_viewers = self._content_view_counts.get(content_id, 0)
        
        similar_viewers = 0
        if taste_cluster_id and taste_cluster_id in self._taste_cluster_counts:
            similar_viewers = self._taste_cluster_counts[taste_cluster_id].get(content_id, 0)
        
        return SocialCueData(
            content_id=content_id,
            total_viewers=total_viewers,
            similar_taste_viewers=similar_viewers,
            k_threshold=k
        )
    
    def should_show_social_cue(
        self,
        user_id: str,
        content_id: str,
        taste_cluster_id: Optional[str] = None
    ) -> bool:
        """Check if social cue should be shown to user"""
        # Check consent
        if not self.has_consent(user_id, ConsentType.SOCIAL_CUES):
            return False
        
        # Check k-anonymity
        cue = self.get_social_cue(content_id, taste_cluster_id)
        return cue is not None and cue.can_display
    
    # ========== Transparency Notifications ==========
    
    def add_notification(
        self,
        user_id: str,
        notification_type: str,
        message: str,
        action_taken: str,
        can_undo: bool = False
    ):
        """Add transparency notification for user"""
        if user_id not in self._user_notifications:
            self._user_notifications[user_id] = []
        
        notification = TransparencyNotification(
            notification_type=notification_type,
            message=message,
            timestamp=time.time(),
            action_taken=action_taken,
            user_can_undo=can_undo
        )
        
        self._user_notifications[user_id].append(notification)
        
        # Keep only last 50 notifications
        self._user_notifications[user_id] = \
            self._user_notifications[user_id][-50:]
    
    def notify_auto_trigger(
        self,
        user_id: str,
        content_title: str,
        confidence: float
    ):
        """Notify user when confidence triggers autoplay"""
        message = (
            f"Starting playback of '{content_title}' based on your browsing patterns. "
            f"Confidence: {confidence*100:.0f}%. "
            "You can undo this in the next 30 seconds."
        )
        self.add_notification(
            user_id=user_id,
            notification_type="auto_trigger",
            message=message,
            action_taken="playback_started",
            can_undo=True
        )
    
    def notify_stress_detection(self, user_id: str, stress_level: float):
        """Notify user when high stress is detected"""
        if stress_level > 0.7:
            message = (
                "We noticed you might be having trouble deciding. "
                "We've reduced the options to help."
            )
            self.add_notification(
                user_id=user_id,
                notification_type="stress_adaptation",
                message=message,
                action_taken="options_reduced"
            )
    
    def get_user_notifications(
        self,
        user_id: str,
        since_timestamp: Optional[float] = None
    ) -> List[TransparencyNotification]:
        """Get notifications for user"""
        notifications = self._user_notifications.get(user_id, [])
        
        if since_timestamp:
            notifications = [n for n in notifications if n.timestamp > since_timestamp]
        
        return notifications
    
    # ========== Data Retention (GDPR/CCPA) ==========
    
    def pseudonymize_user_id(self, user_id: str) -> str:
        """
        Create pseudonymized ID for storage.
        Original ID stored separately with access controls.
        """
        salt = "sequential_narrative_ai_v1"
        return hashlib.sha256(f"{salt}{user_id}".encode()).hexdigest()[:32]
    
    def schedule_data_deletion(
        self,
        user_id: str,
        deletion_date: Optional[datetime] = None
    ):
        """Schedule user data for deletion (right to deletion)"""
        if deletion_date is None:
            settings = self.get_user_settings(user_id)
            deletion_date = datetime.now() + timedelta(days=settings.retention_days)
        
        self._deletion_queue.append((user_id, deletion_date))
    
    def process_deletion_queue(self):
        """Process pending data deletions"""
        now = datetime.now()
        remaining = []
        
        for user_id, deletion_date in self._deletion_queue:
            if deletion_date <= now:
                self._delete_user_data(user_id)
            else:
                remaining.append((user_id, deletion_date))
        
        self._deletion_queue = remaining
    
    def _delete_user_data(self, user_id: str):
        """Delete all data for user"""
        if user_id in self._user_settings:
            del self._user_settings[user_id]
        if user_id in self._user_notifications:
            del self._user_notifications[user_id]
        # In production, would also delete from database
        print(f"Deleted data for user: {self.pseudonymize_user_id(user_id)}")
    
    def handle_opt_out_request(self, user_id: str):
        """Handle CCPA opt-out request"""
        settings = self.get_user_settings(user_id)
        
        # Disable all optional processing
        settings.consents[ConsentType.PERSONALIZATION] = False
        settings.consents[ConsentType.MICRO_SURVEYS] = False
        settings.consents[ConsentType.SOCIAL_CUES] = False
        settings.consents[ConsentType.AUTO_TRIGGERS] = False
        
        settings.consent_updated_at = time.time()
    
    def get_data_export(self, user_id: str) -> Dict:
        """Export user data (right to access)"""
        settings = self.get_user_settings(user_id)
        notifications = self.get_user_notifications(user_id)
        
        return {
            "user_id_pseudonymized": self.pseudonymize_user_id(user_id),
            "settings": {
                "consents": {k.value: v for k, v in settings.consents.items()},
                "age_group": settings.age_group.value,
                "child_safety_mode": settings.child_safety_mode,
                "retention_days": settings.retention_days,
                "consent_updated_at": settings.consent_updated_at,
            },
            "notifications_count": len(notifications),
            "export_timestamp": time.time()
        }


# Singleton instance
privacy_service = PrivacyComplianceService()
