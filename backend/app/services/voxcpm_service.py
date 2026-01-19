"""
VoxCPM Text-to-Speech Service
High-quality neural TTS with voice cloning support
https://github.com/OpenBMB/VoxCPM
"""
import asyncio
import hashlib
import io
import os
from pathlib import Path
from typing import Optional, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# Check if VoxCPM is available
VOXCPM_AVAILABLE = False
try:
    from voxcpm import VoxCPM
    import numpy as np
    import soundfile as sf
    VOXCPM_AVAILABLE = True
    logger.info("✅ VoxCPM is available for high-quality TTS")
except ImportError:
    logger.warning("⚠️ VoxCPM not installed. Using fallback TTS. Install with: pip install voxcpm")


class VoxCPMService:
    """
    Neural Text-to-Speech service using VoxCPM
    Provides high-quality, natural-sounding speech synthesis
    with optional voice cloning capabilities.
    """
    
    def __init__(
        self,
        model_id: str = "openbmb/VoxCPM1.5",
        cache_dir: Optional[str] = None,
        device: str = "auto"
    ):
        self.model_id = model_id
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/voxcpm")
        self.device = device
        self.model: Optional["VoxCPM"] = None
        self.sample_rate = 24000  # VoxCPM default, will update on init
        
        # Audio cache for generated speech
        self.audio_cache_dir = Path(__file__).parent.parent.parent / "data" / "voxcpm_cache"
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Voice cloning reference (optional)
        self.reference_audio_path: Optional[str] = None
        self.reference_transcript: Optional[str] = None
        
    def is_available(self) -> bool:
        """Check if VoxCPM is available"""
        return VOXCPM_AVAILABLE
    
    async def initialize(self) -> bool:
        """
        Initialize VoxCPM model.
        This is async to not block the event loop during model loading.
        """
        if not VOXCPM_AVAILABLE:
            logger.warning("VoxCPM not available - skipping initialization")
            return False
            
        if self.model is not None:
            return True
            
        try:
            logger.info(f"Loading VoxCPM model: {self.model_id}")
            
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: VoxCPM(
                    model=self.model_id,
                    cache_dir=self.cache_dir,
                    device=self.device
                )
            )
            
            self.sample_rate = self.model.tts_model.sample_rate
            logger.info(f"✅ VoxCPM initialized (sample_rate: {self.sample_rate})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize VoxCPM: {e}")
            self.model = None
            return False
    
    def set_voice_reference(
        self,
        audio_path: str,
        transcript: str
    ) -> None:
        """
        Set reference audio for voice cloning.
        
        Args:
            audio_path: Path to reference audio file
            transcript: Transcript of what is said in the reference audio
        """
        self.reference_audio_path = audio_path
        self.reference_transcript = transcript
        logger.info(f"Voice reference set: {audio_path}")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        content = f"{text}:{self.reference_audio_path or 'default'}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_audio(self, cache_key: str) -> Optional[bytes]:
        """Get cached audio if exists"""
        cache_path = self.audio_cache_dir / f"{cache_key}.wav"
        if cache_path.exists():
            return cache_path.read_bytes()
        return None
    
    def _save_to_cache(self, cache_key: str, audio_data: bytes) -> None:
        """Save audio to cache"""
        cache_path = self.audio_cache_dir / f"{cache_key}.wav"
        cache_path.write_bytes(audio_data)
    
    async def synthesize(
        self,
        text: str,
        use_cache: bool = True,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        normalize: bool = True
    ) -> Optional[bytes]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            use_cache: Whether to use cached audio
            cfg_value: Classifier-free guidance value (higher = more expressive)
            inference_timesteps: Number of diffusion steps (higher = better quality)
            normalize: Whether to normalize audio volume
            
        Returns:
            WAV audio bytes or None if synthesis fails
        """
        if not self.model:
            if not await self.initialize():
                return None
        
        # Check cache
        cache_key = self._get_cache_key(text)
        if use_cache:
            cached = self._get_cached_audio(cache_key)
            if cached:
                logger.debug(f"Cache hit for: {text[:50]}...")
                return cached
        
        try:
            loop = asyncio.get_event_loop()
            
            # Prepare generation kwargs
            gen_kwargs = {
                "text": text,
                "cfg_value": cfg_value,
                "inference_timesteps": inference_timesteps,
                "normalize": normalize,
            }
            
            # Add voice cloning reference if set
            if self.reference_audio_path and self.reference_transcript:
                gen_kwargs["prompt_audio"] = self.reference_audio_path
                gen_kwargs["prompt_text"] = self.reference_transcript
            
            # Generate audio in thread pool
            wav = await loop.run_in_executor(
                None,
                lambda: self.model.generate(**gen_kwargs)
            )
            
            # Convert to WAV bytes
            buffer = io.BytesIO()
            sf.write(buffer, wav, self.sample_rate, format='WAV')
            audio_bytes = buffer.getvalue()
            
            # Cache the result
            if use_cache:
                self._save_to_cache(cache_key, audio_bytes)
            
            logger.debug(f"Synthesized: {text[:50]}... ({len(audio_bytes)} bytes)")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"VoxCPM synthesis error: {e}")
            return None
    
    async def synthesize_streaming(
        self,
        text: str,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech chunks.
        Ideal for real-time narration in the reel viewer.
        
        Args:
            text: Text to synthesize
            cfg_value: Classifier-free guidance value
            inference_timesteps: Number of diffusion steps
            
        Yields:
            WAV audio chunks
        """
        if not self.model:
            if not await self.initialize():
                return
        
        try:
            loop = asyncio.get_event_loop()
            
            # Prepare generation kwargs
            gen_kwargs = {
                "text": text,
                "cfg_value": cfg_value,
                "inference_timesteps": inference_timesteps,
            }
            
            # Add voice cloning reference if set
            if self.reference_audio_path and self.reference_transcript:
                gen_kwargs["prompt_audio"] = self.reference_audio_path
                gen_kwargs["prompt_text"] = self.reference_transcript
            
            # Get streaming generator
            def get_chunks():
                return list(self.model.generate_streaming(**gen_kwargs))
            
            chunks = await loop.run_in_executor(None, get_chunks)
            
            for chunk in chunks:
                # Convert chunk to WAV bytes
                buffer = io.BytesIO()
                sf.write(buffer, chunk, self.sample_rate, format='WAV')
                yield buffer.getvalue()
                
        except Exception as e:
            logger.error(f"VoxCPM streaming error: {e}")
    
    def get_status(self) -> dict:
        """Get service status"""
        return {
            "available": VOXCPM_AVAILABLE,
            "initialized": self.model is not None,
            "model_id": self.model_id,
            "sample_rate": self.sample_rate,
            "has_voice_reference": self.reference_audio_path is not None,
            "cache_dir": str(self.audio_cache_dir),
        }


# Singleton instance
voxcpm_service = VoxCPMService()
