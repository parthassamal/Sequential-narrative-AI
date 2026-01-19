"""
Recommendation API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models import (
    RecommendationRequest, RecommendationResponse,
    NLPProcessRequest, NLPProcessResponse,
    Content
)
from app.services import recommendation_engine, nlp_service
from app.data import get_all_content, get_content_by_id, search_content

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(request: RecommendationRequest):
    """
    Generate personalized recommendations based on user query and profile.
    
    This is the main recommendation endpoint that:
    1. Processes the natural language query (if provided)
    2. Scores all content against user profile
    3. Applies diversity optimization
    4. Generates micro-pitches for each recommendation
    5. Optimizes sequence for engagement
    """
    try:
        response = await recommendation_engine.generate_recommendations(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-query", response_model=NLPProcessResponse)
async def process_query(request: NLPProcessRequest):
    """
    Process a natural language query and return parsed intent.
    
    Use this endpoint to:
    - Understand what the user is looking for
    - Get suggested follow-up prompts
    - Generate an appropriate narrative intro
    """
    try:
        intent = await nlp_service.process_query(
            request.query, 
            request.user_context
        )
        narrative = nlp_service.generate_narrative_intro(intent)
        suggestions = nlp_service.get_suggested_prompts(intent)
        
        return NLPProcessResponse(
            intent=intent,
            narrative=narrative,
            suggested_prompts=suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content", response_model=list[Content])
async def get_content_catalog(
    genre: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
):
    """
    Get content catalog with optional filtering.
    
    Args:
        genre: Filter by genre
        search: Search query
        limit: Maximum results
    """
    content = get_all_content()
    
    if search:
        content = search_content(search)
    elif genre:
        content = [c for c in content if genre in c.genre]
    
    return content[:limit]


@router.get("/content/{content_id}", response_model=Content)
async def get_content_detail(content_id: str):
    """Get detailed information about a specific content item"""
    content = get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/content/{content_id}/pitch")
async def generate_content_pitch(content_id: str):
    """Generate a micro-pitch for a specific content item"""
    content = get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    pitch = await nlp_service.generate_micro_pitch(content)
    return pitch
