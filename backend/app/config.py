"""
Configuration settings for Sequential Narrative AI Backend
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Settings
    APP_NAME: str = "Sequential Narrative AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8888
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://localhost:8888"]
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sequential_narrative.db"
    
    # AI Configuration (OpenRouter or OpenAI)
    OPENROUTER_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None  # Fallback to OpenAI if no OpenRouter
    
    # OpenRouter settings
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"  # Fast and capable
    OPENROUTER_FALLBACK_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"  # Free fallback
    
    # OpenAI fallback settings
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Streaming Service API Keys
    TMDB_API_KEY: Optional[str] = None  # Get from https://www.themoviedb.org/settings/api
    YOUTUBE_API_KEY: Optional[str] = None  # Get from https://console.cloud.google.com/apis
    
    # Paramount+ Enterprise API (Requires Partnership)
    PARAMOUNT_API_KEY: Optional[str] = None
    PARAMOUNT_CLIENT_ID: Optional[str] = None
    PARAMOUNT_CLIENT_SECRET: Optional[str] = None
    
    # Recommendation Engine Settings
    MAX_RECOMMENDATIONS: int = 5
    MIN_RECOMMENDATIONS: int = 2
    DEFAULT_RECOMMENDATIONS: int = 4
    
    # Decision State Thresholds
    STRESS_LOW_THRESHOLD: float = 0.3
    STRESS_HIGH_THRESHOLD: float = 0.6
    INTERVENTION_THRESHOLD: float = 0.7
    
    # Audio Settings
    TTS_ENABLED: bool = True
    TTS_CACHE_DIR: str = "./data/audio_cache"
    
    # Scoring Weights
    WEIGHT_GENRE_MATCH: float = 0.35
    WEIGHT_MOOD_MATCH: float = 0.25
    WEIGHT_RATING_BOOST: float = 0.15
    WEIGHT_RECENCY_BOOST: float = 0.10
    WEIGHT_DIVERSITY_PENALTY: float = 0.10
    WEIGHT_HISTORY_PENALTY: float = 0.05
    
    # Analytics
    TRACK_USER_DECISIONS: bool = True
    DECISION_METRICS_RETENTION_DAYS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# Ensure data directories exist
os.makedirs("./data", exist_ok=True)
os.makedirs(settings.TTS_CACHE_DIR, exist_ok=True)
