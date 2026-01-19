"""Data module for Sequential Narrative AI"""
from app.data.content_db import (
    get_all_content,
    get_content_by_id,
    get_content_by_genre,
    get_content_by_mood,
    get_content_by_type,
    search_content,
    CONTENT_DATABASE
)

__all__ = [
    "get_all_content",
    "get_content_by_id", 
    "get_content_by_genre",
    "get_content_by_mood",
    "get_content_by_type",
    "search_content",
    "CONTENT_DATABASE"
]
