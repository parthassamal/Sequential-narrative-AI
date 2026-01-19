"""
Streaming Service API Routes
Provides unified access to multiple streaming platforms.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.streaming_apis import content_service

router = APIRouter(prefix="/api/streaming", tags=["Streaming Services"])


@router.get("/providers")
async def list_providers():
    """
    List all available streaming providers and their status.
    
    Returns information about:
    - TMDb (Movies & TV Database)
    - YouTube (Video Platform)
    - Paramount+ (Enterprise - Demo Mode)
    """
    return {
        "providers": content_service.get_available_providers(),
        "total": len(content_service.providers)
    }


@router.get("/search")
async def search_content(
    q: str = Query(..., description="Search query"),
    provider: Optional[str] = Query(None, description="Specific provider (tmdb, youtube, paramount)"),
    limit: int = Query(10, ge=1, le=50, description="Results per provider")
):
    """
    Search for content across streaming platforms.
    
    - **q**: Search query (e.g., "action movies", "comedy series")
    - **provider**: Optional - search specific provider only
    - **limit**: Max results per provider (default: 10)
    """
    if provider:
        results = await content_service.search_provider(provider, q, limit)
        return {
            "query": q,
            "provider": provider,
            "results": results,
            "total": len(results)
        }
    
    results = await content_service.search_all(q, limit)
    return {
        "query": q,
        "provider": "all",
        "results": results,
        "total": len(results)
    }


@router.get("/trending")
async def get_trending(
    provider: Optional[str] = Query(None, description="Specific provider"),
    limit: int = Query(20, ge=1, le=50, description="Results per provider")
):
    """
    Get trending content from streaming platforms.
    
    Returns currently popular movies, shows, and videos.
    """
    if provider and provider in content_service.providers:
        results = await content_service.providers[provider].get_trending(limit)
        return {
            "provider": provider,
            "results": results,
            "total": len(results)
        }
    
    results = await content_service.get_trending_all(limit)
    return {
        "provider": "all",
        "results": results,
        "total": len(results)
    }


@router.get("/content/{content_id}")
async def get_content_details(content_id: str):
    """
    Get detailed information about specific content.
    
    Content ID format:
    - TMDb: tmdb_movie_123 or tmdb_tv_456
    - YouTube: youtube_abcdefg
    - Paramount: paramount_123
    """
    # Determine provider from ID prefix
    if content_id.startswith("tmdb_"):
        result = await content_service.providers["tmdb"].get_details(content_id)
    elif content_id.startswith("youtube_"):
        result = await content_service.providers["youtube"].get_details(content_id)
    elif content_id.startswith("paramount_"):
        result = await content_service.providers["paramount"].get_details(content_id)
    else:
        return {"error": "Unknown content ID format"}
    
    if result:
        return result
    return {"error": "Content not found"}


@router.get("/paramount/status")
async def paramount_integration_status():
    """
    Check Paramount+ API integration status.
    
    Provides information about:
    - Current integration mode (demo/live)
    - Required steps for enterprise access
    - Available endpoints when connected
    """
    import os
    has_credentials = bool(os.getenv("PARAMOUNT_API_KEY"))
    
    return {
        "status": "live" if has_credentials else "demo_mode",
        "message": "Paramount+ API requires enterprise partnership" if not has_credentials else "Connected to Paramount+ API",
        "demo_content_available": True,
        "enterprise_integration": {
            "required_credentials": [
                "PARAMOUNT_API_KEY",
                "PARAMOUNT_CLIENT_ID", 
                "PARAMOUNT_CLIENT_SECRET"
            ],
            "contact": "https://www.paramount.com/partner",
            "capabilities_when_connected": [
                "Full catalog access (10,000+ titles)",
                "User watch history sync",
                "Personalized recommendations",
                "Deep linking to content",
                "Real-time availability data"
            ]
        },
        "available_endpoints": [
            "/api/streaming/search?provider=paramount",
            "/api/streaming/trending?provider=paramount",
            "/api/streaming/content/{paramount_id}"
        ]
    }
