"""Model factory for creating different LLM providers."""

from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from backend.agent.langchain_model import OllamaChatModel
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("langchain-openai not installed. OpenAI provider will not be available.")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("langchain-google-genai not installed. Gemini provider will not be available.")


def create_model(
    provider: str = "ollama",
    model_name: str = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    api_key: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a chat model based on the provider.
    
    Args:
        provider: One of "ollama", "openai", "deepseek", "mistral", "gemini"
        model_name: Model name to use
        temperature: Temperature setting
        max_tokens: Maximum tokens
        api_key: API key for the provider
        api_endpoint: API endpoint URL
        **kwargs: Additional provider-specific arguments
    
    Returns:
        BaseChatModel instance
    """
    # Get API config from user preferences or environment
    api_config = kwargs.get("api_config", {})
    
    # Determine provider and get API key/endpoint
    if provider == "ollama":
        model = model_name or settings.DEFAULT_MODEL
        return OllamaChatModel(
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=settings.OLLAMA_BASE_URL
        )
    
    elif provider == "openai":
        if not OPENAI_AVAILABLE:
            raise ImportError("langchain-openai is required for OpenAI provider. Install with: pip install langchain-openai")
        
        api_key = api_key or api_config.get("openai_api_key") or settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or configure in Settings.")
        
        base_url = api_endpoint or api_config.get("openai_api_endpoint") or "https://api.openai.com/v1"
        model = model_name or api_config.get("openai_model") or "gpt-4o-mini"
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url
        )
    
    elif provider == "deepseek":
        if not OPENAI_AVAILABLE:
            raise ImportError("langchain-openai is required for DeepSeek provider. Install with: pip install langchain-openai")
        
        # DeepSeek uses OpenAI-compatible API
        api_key = api_key or api_config.get("deepseek_api_key") or settings.DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable or configure in Settings.")
        
        base_url = api_endpoint or api_config.get("deepseek_api_endpoint") or "https://api.deepseek.com/v1"
        model = model_name or api_config.get("deepseek_model") or "deepseek-chat"
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url
        )
    
    elif provider == "mistral":
        if not OPENAI_AVAILABLE:
            raise ImportError("langchain-openai is required for Mistral provider. Install with: pip install langchain-openai")
        
        # Mistral uses OpenAI-compatible API
        api_key = api_key or api_config.get("mistral_api_key") or settings.MISTRAL_API_KEY
        if not api_key:
            raise ValueError("Mistral API key is required. Set MISTRAL_API_KEY environment variable or configure in Settings.")
        
        base_url = api_endpoint or api_config.get("mistral_api_endpoint") or "https://api.mistral.ai/v1"
        model = model_name or api_config.get("mistral_model") or "mistral-small"
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=base_url
        )
    
    elif provider == "gemini":
        if not GEMINI_AVAILABLE:
            raise ImportError("langchain-google-genai is required for Gemini provider. Install with: pip install langchain-google-genai")
        
        api_key = api_key or api_config.get("gemini_api_key") or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or configure in Settings.")
        
        model = model_name or api_config.get("gemini_model") or "gemini-pro"
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Supported providers: ollama, openai, deepseek, mistral, gemini")

