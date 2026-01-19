"""
Audio Service for Sequential Narrative AI
Handles text-to-speech generation for micro-pitches.
"""
import os
import hashlib
from typing import Optional
from pathlib import Path

from app.config import settings


class AudioService:
    """
    Service for generating audio narration.
    Supports multiple TTS backends:
    - gTTS (Google Text-to-Speech) - free, requires internet
    - pyttsx3 - offline, lower quality
    - OpenAI TTS - high quality, paid
    """
    
    def __init__(self):
        self.cache_dir = Path(settings.TTS_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._backend = self._detect_backend()
    
    def _detect_backend(self) -> str:
        """Detect available TTS backend"""
        # Check for OpenAI
        if settings.OPENAI_API_KEY:
            return "openai"
        
        # Check for gTTS
        try:
            from gtts import gTTS
            return "gtts"
        except ImportError:
            pass
        
        # Fallback to pyttsx3
        try:
            import pyttsx3
            return "pyttsx3"
        except ImportError:
            pass
        
        return "none"
    
    def _get_cache_path(self, text: str, voice: str) -> Path:
        """Generate cache file path for text"""
        text_hash = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.mp3"
    
    async def generate_audio(
        self, 
        text: str, 
        voice: str = "default",
        speed: float = 1.0
    ) -> Optional[dict]:
        """
        Generate audio from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice selection (depends on backend)
            speed: Speech speed (0.5 to 2.0)
            
        Returns:
            Dict with audio_url and duration, or None if failed
        """
        if not settings.TTS_ENABLED or self._backend == "none":
            return None
        
        # Check cache
        cache_path = self._get_cache_path(text, voice)
        if cache_path.exists():
            return {
                "audio_url": f"/audio/{cache_path.name}",
                "duration_seconds": self._estimate_duration(text),
                "text": text,
                "cached": True
            }
        
        # Generate based on backend
        try:
            if self._backend == "openai":
                return await self._generate_openai(text, voice, speed, cache_path)
            elif self._backend == "gtts":
                return await self._generate_gtts(text, voice, cache_path)
            elif self._backend == "pyttsx3":
                return await self._generate_pyttsx3(text, voice, speed, cache_path)
        except Exception as e:
            print(f"Audio generation error: {e}")
            return None
        
        return None
    
    async def _generate_openai(
        self, 
        text: str, 
        voice: str, 
        speed: float,
        cache_path: Path
    ) -> dict:
        """Generate audio using OpenAI TTS"""
        import openai
        
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Map voice names to OpenAI voices
        voice_map = {
            "default": "alloy",
            "male": "onyx",
            "female": "nova",
            "warm": "shimmer",
            "professional": "echo",
        }
        openai_voice = voice_map.get(voice, "alloy")
        
        response = await client.audio.speech.create(
            model="tts-1",
            voice=openai_voice,
            input=text,
            speed=speed
        )
        
        # Save to cache
        response.stream_to_file(str(cache_path))
        
        return {
            "audio_url": f"/audio/{cache_path.name}",
            "duration_seconds": self._estimate_duration(text),
            "text": text,
            "cached": False
        }
    
    async def _generate_gtts(
        self, 
        text: str, 
        voice: str,
        cache_path: Path
    ) -> dict:
        """Generate audio using Google TTS"""
        from gtts import gTTS
        import asyncio
        
        # gTTS is synchronous, run in executor
        def _generate():
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(str(cache_path))
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _generate)
        
        return {
            "audio_url": f"/audio/{cache_path.name}",
            "duration_seconds": self._estimate_duration(text),
            "text": text,
            "cached": False
        }
    
    async def _generate_pyttsx3(
        self, 
        text: str, 
        voice: str,
        speed: float,
        cache_path: Path
    ) -> dict:
        """Generate audio using pyttsx3 (offline)"""
        import pyttsx3
        import asyncio
        
        def _generate():
            engine = pyttsx3.init()
            
            # Set properties
            engine.setProperty('rate', int(150 * speed))
            
            # Save to file
            engine.save_to_file(text, str(cache_path))
            engine.runAndWait()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _generate)
        
        return {
            "audio_url": f"/audio/{cache_path.name}",
            "duration_seconds": self._estimate_duration(text),
            "text": text,
            "cached": False
        }
    
    def _estimate_duration(self, text: str) -> float:
        """Estimate speech duration based on text length"""
        words = len(text.split())
        # Average speaking rate: ~150 words per minute
        return round(words / 2.5, 1)
    
    def get_audio_path(self, filename: str) -> Optional[Path]:
        """Get full path to cached audio file"""
        path = self.cache_dir / filename
        if path.exists():
            return path
        return None
    
    def clear_cache(self):
        """Clear all cached audio files"""
        for file in self.cache_dir.glob("*.mp3"):
            file.unlink()
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        files = list(self.cache_dir.glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "backend": self._backend,
            "cache_dir": str(self.cache_dir),
            "cached_files": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "tts_enabled": settings.TTS_ENABLED
        }


# Singleton instance
audio_service = AudioService()
