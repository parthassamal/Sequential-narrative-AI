"""
AI Client for Sequential Narrative AI
Supports multiple backends: OpenRouter, Groq, Cerebras with automatic fallback.
"""
import httpx
from typing import Optional, Dict, Any, List
import json
import os

from app.config import settings


class AIProvider:
    """Base class for AI providers"""
    name: str = "base"
    base_url: str = ""
    default_model: str = ""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_payload(self, messages: List[Dict], max_tokens: int, temperature: float, model: str = None) -> Dict:
        return {
            "model": model or self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }


class GroqProvider(AIProvider):
    """Groq - Ultra-fast inference"""
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"  # Fast and capable
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }


class CerebrasProvider(AIProvider):
    """Cerebras - High-speed AI inference"""
    name = "cerebras"
    base_url = "https://api.cerebras.ai/v1"
    default_model = "llama3.1-8b"  # Fast Llama model
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }


class OpenRouterProvider(AIProvider):
    """OpenRouter - Access to multiple models"""
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "anthropic/claude-3.5-sonnet"
    fallback_model = "meta-llama/llama-3.1-8b-instruct:free"
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Sequential Narrative AI",
            "Content-Type": "application/json"
        }


class AIClient:
    """
    Unified AI client with automatic fallback across providers.
    Priority: Groq -> Cerebras -> OpenRouter
    """
    
    def __init__(self):
        self.providers: List[AIProvider] = []
        self._init_providers()
        
    def _init_providers(self):
        """Initialize available providers in priority order"""
        # Groq - fastest, most reliable free tier
        groq_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if groq_key:
            self.providers.append(GroqProvider(groq_key))
            print(f"✅ Groq AI enabled (model: {GroqProvider.default_model})")
        
        # Cerebras - fast inference
        cerebras_key = settings.CEREBRAS_API_KEY or os.getenv("CEREBRAS_API_KEY", "")
        if cerebras_key:
            self.providers.append(CerebrasProvider(cerebras_key))
            print(f"✅ Cerebras AI enabled (model: {CerebrasProvider.default_model})")
        
        # OpenRouter - fallback with multiple models
        openrouter_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            self.providers.append(OpenRouterProvider(openrouter_key))
            print(f"✅ OpenRouter AI enabled (model: {OpenRouterProvider.default_model})")
        
        if not self.providers:
            print("⚠️ No AI providers configured - using template fallbacks")
    
    @property
    def is_available(self) -> bool:
        return len(self.providers) > 0
    
    @property
    def active_provider(self) -> Optional[AIProvider]:
        return self.providers[0] if self.providers else None
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        json_response: bool = False,
    ) -> Optional[str]:
        """
        Send a chat completion request with automatic fallback.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Creativity (0-1)
            json_response: Whether to request JSON output
            
        Returns:
            Response text or None if all providers failed
        """
        if not self.is_available:
            return None
        
        # Try each provider in order
        for provider in self.providers:
            result = await self._try_provider(
                provider, messages, max_tokens, temperature, json_response
            )
            if result:
                return result
        
        print("❌ All AI providers failed")
        return None
    
    async def _try_provider(
        self,
        provider: AIProvider,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        json_response: bool
    ) -> Optional[str]:
        """Try a single provider"""
        url = f"{provider.base_url}/chat/completions"
        
        payload = provider.get_payload(messages, max_tokens, temperature)
        
        if json_response:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    url,
                    headers=provider.get_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return content
                else:
                    error_detail = response.text[:200]
                    print(f"⚠️ {provider.name} error ({response.status_code}): {error_detail}")
                    return None
                    
        except Exception as e:
            print(f"⚠️ {provider.name} request failed: {e}")
            return None
    
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500
    ) -> Optional[Dict]:
        """
        Generate a JSON response.
        
        Args:
            system_prompt: System instructions
            user_prompt: User request
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON dict or None
        """
        response = await self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            json_response=True
        )
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start >= 0 and end > start:
                        return json.loads(response[start:end])
                except:
                    pass
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "available": self.is_available,
            "providers": [
                {
                    "name": p.name,
                    "model": p.default_model,
                    "priority": idx + 1
                }
                for idx, p in enumerate(self.providers)
            ],
            "active_provider": self.active_provider.name if self.active_provider else None,
            "active_model": self.active_provider.default_model if self.active_provider else None
        }


# Singleton instance
ai_client = AIClient()
