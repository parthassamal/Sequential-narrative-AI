"""
Streaming Service API Routes
Provides unified access to multiple streaming platforms.
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.streaming_apis import content_service

router = APIRouter(prefix="/api/streaming", tags=["Streaming Services"])
logger = logging.getLogger(__name__)


def _validate_provider(provider: Optional[str]) -> Optional[str]:
    if provider is None:
        return None

    normalized = provider.lower()
    if normalized not in content_service.providers:
        valid = ", ".join(sorted(content_service.providers.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Valid providers: {valid}."
        )
    return normalized


@router.get("/providers")
async def list_providers():
    """
    List all available streaming providers and their status.
    
    Returns information about:
    - TMDb (Movies & TV Database)
    - YouTube (Video Platform)
    - Paramount+ (Enterprise - Demo Mode)
    """
    try:
        providers = content_service.get_available_providers()
        return {
            "providers": providers,
            "total": len(content_service.providers)
        }
    except Exception:
        logger.exception("Failed to list streaming providers")
        raise HTTPException(status_code=500, detail="Failed to load streaming providers.")


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
    normalized_provider = _validate_provider(provider)

    try:
        if normalized_provider:
            results = await content_service.search_provider(normalized_provider, q, limit)
            return {
                "query": q,
                "provider": normalized_provider,
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
    except HTTPException:
        raise
    except Exception:
        logger.exception("Streaming search failed", extra={"provider": normalized_provider, "query": q})
        raise HTTPException(status_code=502, detail="Streaming search failed. Please try again.")


@router.get("/trending")
async def get_trending(
    provider: Optional[str] = Query(None, description="Specific provider"),
    limit: int = Query(20, ge=1, le=50, description="Results per provider")
):
    """
    Get trending content from streaming platforms.
    
    Returns currently popular movies, shows, and videos.
    """
    normalized_provider = _validate_provider(provider)

    try:
        if normalized_provider:
            results = await content_service.providers[normalized_provider].get_trending(limit)
            return {
                "provider": normalized_provider,
                "results": results,
                "total": len(results)
            }

        results = await content_service.get_trending_all(limit)
        return {
            "provider": "all",
            "results": results,
            "total": len(results)
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch trending streaming content", extra={"provider": normalized_provider})
        raise HTTPException(status_code=502, detail="Failed to fetch trending content.")


@router.get("/content/{content_id}")
async def get_content_details(content_id: str):
    """
    Get detailed information about specific content.
    
    Content ID format:
    - TMDb: tmdb_movie_123 or tmdb_tv_456
    - YouTube: youtube_abcdefg
    - Paramount: paramount_123
    """
    if content_id.startswith("tmdb_"):
        provider_id = "tmdb"
    elif content_id.startswith("youtube_"):
        provider_id = "youtube"
    elif content_id.startswith("paramount_"):
        provider_id = "paramount"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unknown content ID format. Expected tmdb_, youtube_, or paramount_ prefix."
        )

    try:
        result = await content_service.providers[provider_id].get_details(content_id)
    except Exception:
        logger.exception("Failed to fetch content details", extra={"provider": provider_id, "content_id": content_id})
        raise HTTPException(status_code=502, detail="Failed to fetch content details from streaming provider.")

    if not result:
        raise HTTPException(status_code=404, detail="Content not found.")

    return result


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
