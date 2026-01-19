"""
Sequential Narrative AI - Backend API
AI-Driven Sequential Narrative Recommendation System for Streaming Media

This FastAPI application provides:
- Natural Language Processing for query understanding
- AI-powered recommendation engine with diversity optimization
- Decision state encoding for reducing choice paralysis
- Text-to-speech audio generation for micro-pitches
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
from pathlib import Path

from app.config import settings
from app.models import HealthResponse
from fastapi import WebSocket, WebSocketDisconnect
from app.routes import (
    recommendations_router,
    decision_state_router,
    audio_router,
    streaming_router,
    telemetry_router,
    commitment_router,
    compliance_router,
    metrics_router
)
from app.routes.telemetry import session_store, telemetry_websocket_handler
from app.services import ai_client

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    AI-Driven Sequential Narrative Recommendation System for Streaming Media.
    
    ## Features
    
    - **Natural Language Processing**: Understand user queries and extract intent
    - **AI Recommendations**: Generate personalized content recommendations
    - **Diversity Optimization**: Ensure varied recommendations using DPP-inspired algorithms
    - **Decision State Encoding**: Monitor and reduce user decision stress
    - **Micro-Pitch Generation**: Create compelling 7-10 second narratives
    - **Audio Narration**: Text-to-speech for immersive experience
    
    ## Key Innovations
    
    - Decision state vector encoding
    - Determinantal diversity optimization
    - Deferral-aware recommendation limiting
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - allow all origins for audio files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
            "path": str(request.url)
        }
    )


# Include routers
app.include_router(recommendations_router)
app.include_router(decision_state_router)
app.include_router(audio_router)
app.include_router(streaming_router)
app.include_router(telemetry_router)
app.include_router(commitment_router)
app.include_router(compliance_router)
app.include_router(metrics_router)

# WebSocket endpoint - registered directly on app for proper handling
@app.websocket("/ws/telemetry/{user_id}")
async def websocket_telemetry(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time telemetry streaming"""
    await telemetry_websocket_handler(websocket, user_id)


# Mount static files for audio with CORS support
audio_cache_path = Path(settings.TTS_CACHE_DIR)
audio_cache_path.mkdir(parents=True, exist_ok=True)

# Custom middleware to add CORS headers to static audio files
from starlette.middleware.base import BaseHTTPMiddleware

class AudioCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/audio"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app.add_middleware(AudioCORSMiddleware)
app.mount("/audio", StaticFiles(directory=str(audio_cache_path)), name="audio")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns service status and version information.
    """
    ai_status = ai_client.get_status()
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        services={
            "nlp": "active",
            "recommendations": "active",
            "decision_state": "active",
            "audio": "active" if settings.TTS_ENABLED else "disabled",
            "ai_backend": ai_status.get("active_provider", "none"),
            "ai_model": ai_status.get("active_model", "none")
        }
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "AI-Driven Sequential Narrative Recommendation System",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "recommendations": "/api/recommendations",
            "decision_state": "/api/decision-state",
            "audio": "/api/audio"
        }
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📍 Server running at http://{settings.HOST}:{settings.PORT}")
    print(f"📚 Documentation at http://{settings.HOST}:{settings.PORT}/docs")
    
    ai_status = ai_client.get_status()
    if ai_status["available"]:
        print(f"✅ AI integration enabled ({ai_status['active_provider']})")
        print(f"   Active Model: {ai_status['active_model']}")
        if len(ai_status.get("providers", [])) > 1:
            print(f"   Fallback providers: {', '.join(p['name'] for p in ai_status['providers'][1:])}")
    else:
        print("⚠️  No AI configured - using local processing")
    
    if settings.TTS_ENABLED:
        print("🔊 Text-to-Speech enabled")
    else:
        print("🔇 Text-to-Speech disabled")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print(f"👋 Shutting down {settings.APP_NAME}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
