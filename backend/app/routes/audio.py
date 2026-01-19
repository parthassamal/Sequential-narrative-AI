"""
Audio API Routes
Handles text-to-speech generation for micro-pitches.
Supports multiple TTS backends: VoxCPM (high-quality), gTTS (fallback), Web Speech API (frontend)
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.models import AudioGenerationRequest, AudioGenerationResponse
from app.services import audio_service
from app.services.voxcpm_service import voxcpm_service

router = APIRouter(prefix="/api/audio", tags=["Audio"])


class VoxCPMRequest(BaseModel):
    """Request for VoxCPM synthesis"""
    text: str
    cfg_value: float = 2.0  # Higher = more expressive
    inference_timesteps: int = 10  # Higher = better quality, slower
    normalize: bool = True
    use_cache: bool = True


class VoiceReferenceRequest(BaseModel):
    """Request to set voice cloning reference"""
    audio_path: str
    transcript: str


@router.post("/generate", response_model=AudioGenerationResponse)
async def generate_audio(request: AudioGenerationRequest):
    """
    Generate audio narration from text.
    
    Args:
        text: Text to convert to speech
        voice: Voice selection (default, male, female, warm, professional)
        speed: Speech speed (0.5 to 2.0)
        
    Returns:
        Audio URL, duration, and text
    """
    try:
        result = await audio_service.generate_audio(
            text=request.text,
            voice=request.voice,
            speed=request.speed
        )
        
        if not result:
            raise HTTPException(
                status_code=503, 
                detail="Audio generation not available. TTS service may be disabled."
            )
        
        return AudioGenerationResponse(
            audio_url=result["audio_url"],
            duration_seconds=result["duration_seconds"],
            text=result["text"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{filename}")
async def get_audio_file(filename: str):
    """
    Serve a cached audio file.
    
    Args:
        filename: Audio file name (from generate response)
    """
    path = audio_service.get_audio_path(filename)
    
    if not path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        filename=filename
    )


@router.get("/stats")
async def get_audio_stats():
    """
    Get audio service statistics.
    
    Returns:
        Backend type, cache info, and service status
    """
    return audio_service.get_cache_stats()


@router.post("/clear-cache")
async def clear_audio_cache():
    """Clear all cached audio files"""
    audio_service.clear_cache()
    return {"status": "cleared"}


@router.post("/batch-generate")
async def batch_generate_audio(texts: list[str], voice: str = "default"):
    """
    Generate audio for multiple texts in batch.
    
    Useful for pre-generating audio for all recommendations.
    """
    results = []
    for text in texts:
        try:
            result = await audio_service.generate_audio(text=text, voice=voice)
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "text": text})
    
    return {
        "total": len(texts),
        "successful": len([r for r in results if "error" not in r]),
        "results": results
    }


# ========== VoxCPM High-Quality TTS ==========

@router.get("/voxcpm/status")
async def get_voxcpm_status():
    """
    Get VoxCPM service status.
    
    VoxCPM provides high-quality neural TTS with voice cloning.
    See: https://github.com/OpenBMB/VoxCPM
    """
    return voxcpm_service.get_status()


@router.post("/voxcpm/initialize")
async def initialize_voxcpm():
    """
    Initialize VoxCPM model.
    
    This may take a few minutes on first run as the model downloads.
    Requires ~4GB disk space and GPU recommended for fast inference.
    """
    if not voxcpm_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="VoxCPM not installed. Install with: pip install voxcpm"
        )
    
    success = await voxcpm_service.initialize()
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize VoxCPM model"
        )
    
    return {"status": "initialized", **voxcpm_service.get_status()}


@router.post("/voxcpm/synthesize")
async def voxcpm_synthesize(request: VoxCPMRequest):
    """
    Synthesize speech using VoxCPM (high-quality neural TTS).
    
    Returns WAV audio file.
    
    Args:
        text: Text to synthesize
        cfg_value: Classifier-free guidance (2.0 = balanced, higher = more expressive)
        inference_timesteps: Quality vs speed tradeoff (10 = fast, 25 = high quality)
        normalize: Normalize audio volume
        use_cache: Use cached audio if available
    """
    if not voxcpm_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="VoxCPM not available. Using browser speech synthesis instead."
        )
    
    audio_bytes = await voxcpm_service.synthesize(
        text=request.text,
        cfg_value=request.cfg_value,
        inference_timesteps=request.inference_timesteps,
        normalize=request.normalize,
        use_cache=request.use_cache
    )
    
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="Synthesis failed")
    
    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename=speech.wav"}
    )


@router.post("/voxcpm/stream")
async def voxcpm_stream(request: VoxCPMRequest):
    """
    Stream synthesized speech in chunks (for real-time playback).
    
    Ideal for narrating micro-pitches as they're being read.
    """
    if not voxcpm_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="VoxCPM not available"
        )
    
    async def audio_stream():
        async for chunk in voxcpm_service.synthesize_streaming(
            text=request.text,
            cfg_value=request.cfg_value,
            inference_timesteps=request.inference_timesteps
        ):
            yield chunk
    
    return StreamingResponse(
        audio_stream(),
        media_type="audio/wav"
    )


@router.post("/voxcpm/set-voice")
async def set_voxcpm_voice(request: VoiceReferenceRequest):
    """
    Set a reference voice for voice cloning.
    
    VoxCPM can clone any voice from a short audio sample.
    Perfect for creating a consistent narrator voice.
    
    Args:
        audio_path: Path to reference audio (3-10 seconds recommended)
        transcript: Exact transcript of what's said in the reference
    """
    if not voxcpm_service.is_available():
        raise HTTPException(status_code=503, detail="VoxCPM not available")
    
    voxcpm_service.set_voice_reference(
        audio_path=request.audio_path,
        transcript=request.transcript
    )
    
    return {
        "status": "voice_set",
        "audio_path": request.audio_path,
        "transcript": request.transcript
    }


@router.delete("/voxcpm/clear-voice")
async def clear_voxcpm_voice():
    """Clear voice cloning reference (use default voice)"""
    voxcpm_service.reference_audio_path = None
    voxcpm_service.reference_transcript = None
    return {"status": "voice_cleared"}
