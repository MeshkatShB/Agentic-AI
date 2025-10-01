"""Ollama client for LLM interactions."""

import httpx
import json
from typing import Dict, List, Optional, AsyncGenerator, Any
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        # Use a more generous timeout; align with app step timeout when available
        default_timeout = getattr(settings, "STEP_TIMEOUT_SECONDS", 30)
        # Add a buffer since model generation may approach the step timeout
        self.client = httpx.AsyncClient(timeout=float(default_timeout) + 10.0)
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        format: Optional[str] = None,
        tools: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Generate text from the model."""
        
        # Build the request
        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            data["system"] = system
        
        if format:
            data["format"] = format
        
        if tools:
            # For Qwen models, tools are passed in a specific format
            data["tools"] = tools
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=data
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk
                        
                        if not stream and chunk.get("done"):
                            break
        
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            yield {"error": str(e)}
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        tools: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Chat with the model using conversation format."""
        
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if tools:
            data["tools"] = tools
        
        try:
            # First try /api/chat endpoint
            try:
                async with self.client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            yield chunk
                            
                            if not stream and chunk.get("done"):
                                break
                    return
            except httpx.HTTPError as chat_error:
                logger.warning(f"Chat API failed, falling back to generate: {chat_error}")
            
            # Fallback to /api/generate endpoint
            # Convert messages to prompt
            prompt = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in messages
            ])
            
            async for chunk in self.generate(
                model=model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                tools=tools
            ):
                if "error" in chunk:
                    yield chunk
                else:
                    # Convert generate response to chat format
                    yield {
                        "message": {
                            "role": "assistant",
                            "content": chunk.get("response", "")
                        },
                        "done": chunk.get("done", False)
                    }
        
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            yield {"error": str(e)}
    
    async def embeddings(self, model: str, prompt: str) -> Optional[List[float]]:
        """Generate embeddings for text."""
        
        data = {
            "model": model,
            "prompt": prompt
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            return result.get("embedding")
        
        except httpx.HTTPError as e:
            logger.error(f"Ollama embeddings error: {e}")
            return None
    
    async def list_models(self) -> List[Dict]:
        """List available models."""
        
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            result = response.json()
            return result.get("models", [])
        
        except httpx.HTTPError as e:
            logger.error(f"Ollama list models error: {e}")
            return []
    
    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry."""
        
        data = {"name": model}
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json=data,
                timeout=300.0  # Model downloads can take time
            )
            response.raise_for_status()
            return True
        
        except httpx.HTTPError as e:
            logger.error(f"Ollama pull model error: {e}")
            return False
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()