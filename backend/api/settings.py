"""Settings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from backend.models import get_db, User
from backend.auth import get_current_user
from backend.config import settings as app_settings
from backend.llm import OllamaClient

router = APIRouter()


class UserSettings(BaseModel):
    """User settings."""
    theme: str = "dark"
    model: str = app_settings.DEFAULT_MODEL
    embedding_model: str = app_settings.EMBEDDING_MODEL
    temperature: float = app_settings.MODEL_TEMPERATURE
    max_steps: int = app_settings.MAX_STEPS_PER_REQUEST
    max_tokens: int = app_settings.MODEL_MAX_TOKENS
    require_confirmation: bool = app_settings.REQUIRE_TOOL_CONFIRMATION


class SystemInfo(BaseModel):
    """System information."""
    app_name: str
    app_version: str
    ollama_url: str
    vector_store: str
    models_available: List[str]


class PathSettings(BaseModel):
    """Path settings."""
    allowed_paths: List[str]
    blocked_paths: List[str]


class APIConfigSettings(BaseModel):
    """External API configuration settings."""
    llm_provider: str = "ollama"  # "ollama", "openai", "deepseek", "mistral", "gemini"
    openai_api_key: Optional[str] = None
    openai_api_endpoint: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    deepseek_api_key: Optional[str] = None
    deepseek_api_endpoint: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    mistral_api_key: Optional[str] = None
    mistral_api_endpoint: str = "https://api.mistral.ai/v1"
    mistral_model: str = "mistral-small"
    gemini_api_key: Optional[str] = None
    gemini_api_endpoint: str = "https://generativelanguage.googleapis.com/v1"
    gemini_model: str = "gemini-pro"


@router.get("/user", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):
    """Get user settings."""
    
    prefs = current_user.preferences or {}
    
    return UserSettings(
        theme=prefs.get("theme", "dark"),
        model=prefs.get("model", app_settings.DEFAULT_MODEL),
        embedding_model=prefs.get("embedding_model", app_settings.EMBEDDING_MODEL),
        temperature=prefs.get("temperature", app_settings.MODEL_TEMPERATURE),
        max_steps=prefs.get("max_steps", app_settings.MAX_STEPS_PER_REQUEST),
        max_tokens=prefs.get("max_tokens", app_settings.MODEL_MAX_TOKENS),
        require_confirmation=prefs.get("require_confirmation", app_settings.REQUIRE_TOOL_CONFIRMATION)
    )


@router.put("/user", response_model=UserSettings)
async def update_user_settings(
    settings: UserSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings."""
    from sqlalchemy.orm.attributes import flag_modified
    from backend.agent import agent_executor
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Update preferences
    preferences_dict = settings.model_dump()
    logger.info(f"Updating settings for user {current_user.username}: {preferences_dict}")
    
    current_user.preferences = preferences_dict
    # Mark JSON field as modified so SQLAlchemy knows to update it
    flag_modified(current_user, "preferences")
    db.commit()
    # Refresh user object to ensure we have the latest data
    db.refresh(current_user)
    
    # Verify the update was saved correctly
    logger.info(f"Settings updated. User preferences after refresh: {current_user.preferences}")
    
    # Clear agent to apply new settings (forces new agent creation with updated preferences)
    agent_executor.clear_agent(current_user.id)
    
    return settings


@router.get("/system", response_model=SystemInfo)
async def get_system_info():
    """Get system information."""
    
    # Get available models from Ollama
    ollama_client = OllamaClient()
    models = []
    
    try:
        model_list = await ollama_client.list_models()
        models = [m.get("name", "") for m in model_list]
    except:
        models = [app_settings.DEFAULT_MODEL]
    
    return SystemInfo(
        app_name=app_settings.APP_NAME,
        app_version=app_settings.APP_VERSION,
        ollama_url=app_settings.OLLAMA_BASE_URL,
        vector_store=app_settings.VECTOR_STORE,
        models_available=models
    )


@router.get("/paths", response_model=PathSettings)
async def get_path_settings(
    current_user: User = Depends(get_current_user)
):
    """Get path settings for file access."""
    
    # Combine system and user paths
    allowed = app_settings.ALLOWED_FILE_PATHS.copy()
    blocked = app_settings.BLOCKED_FILE_PATHS.copy()
    
    if current_user.allowed_paths:
        allowed.extend(current_user.allowed_paths)
    
    if current_user.blocked_paths:
        blocked.extend(current_user.blocked_paths)
    
    return PathSettings(
        allowed_paths=allowed,
        blocked_paths=blocked
    )


@router.put("/paths", response_model=PathSettings)
async def update_path_settings(
    paths: PathSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's path settings."""
    
    # Update user paths (these are in addition to system paths)
    current_user.allowed_paths = paths.allowed_paths
    current_user.blocked_paths = paths.blocked_paths
    db.commit()
    
    return paths


@router.post("/test-ollama")
async def test_ollama_connection():
    """Test connection to Ollama."""
    
    ollama_client = OllamaClient()
    
    try:
        models = await ollama_client.list_models()
        
        if not models:
            return {
                "status": "error",
                "message": "Ollama is running but no models found. Please pull a model."
            }
        
        return {
            "status": "success",
            "message": "Ollama connection successful",
            "models": [m.get("name", "") for m in models]
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to Ollama: {str(e)}"
        }


@router.post("/pull-model")
async def pull_model(
    model_name: str,
    current_user: User = Depends(get_current_user)
):
    """Pull a model from Ollama registry."""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only admin users can pull models"
        )
    
    ollama_client = OllamaClient()
    
    try:
        success = await ollama_client.pull_model(model_name)
        
        if success:
            return {
                "status": "success",
                "message": f"Model {model_name} pulled successfully"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to pull model {model_name}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/api-config", response_model=APIConfigSettings)
async def get_api_config(
    current_user: User = Depends(get_current_user)
):
    """Get external API configuration."""
    from backend.config import settings as app_settings
    
    prefs = current_user.preferences or {}
    api_config = prefs.get("api_config", {})
    
    # Get API keys from user config, fallback to environment variables
    def get_api_key(key_name: str, env_key: str) -> Optional[str]:
        """Get API key from user config or environment variable."""
        user_key = api_config.get(key_name)
        if user_key:
            return user_key
        # Fallback to environment variable
        env_key_value = getattr(app_settings, env_key, None)
        if env_key_value:
            return env_key_value
        return None
    
    return APIConfigSettings(
        llm_provider=api_config.get("llm_provider", "ollama"),
        openai_api_key=get_api_key("openai_api_key", "OPENAI_API_KEY"),
        openai_api_endpoint=api_config.get("openai_api_endpoint", "https://api.openai.com/v1"),
        openai_model=api_config.get("openai_model", "gpt-4o-mini"),
        deepseek_api_key=get_api_key("deepseek_api_key", "DEEPSEEK_API_KEY"),
        deepseek_api_endpoint=api_config.get("deepseek_api_endpoint", "https://api.deepseek.com/v1"),
        deepseek_model=api_config.get("deepseek_model", "deepseek-chat"),
        mistral_api_key=get_api_key("mistral_api_key", "MISTRAL_API_KEY"),
        mistral_api_endpoint=api_config.get("mistral_api_endpoint", "https://api.mistral.ai/v1"),
        mistral_model=api_config.get("mistral_model", "mistral-small"),
        gemini_api_key=get_api_key("gemini_api_key", "GEMINI_API_KEY"),
        gemini_api_endpoint=api_config.get("gemini_api_endpoint", "https://generativelanguage.googleapis.com/v1"),
        gemini_model=api_config.get("gemini_model", "gemini-pro")
    )


@router.put("/api-config", response_model=APIConfigSettings)
async def update_api_config(
    config: APIConfigSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update external API configuration."""
    from sqlalchemy.orm.attributes import flag_modified
    
    # Get current preferences
    prefs = current_user.preferences or {}
    existing_api_config = prefs.get("api_config", {})
    
    # Get only fields that were explicitly set in the request
    provided_fields = config.model_dump(exclude_unset=True)
    
    # Start with existing config and update only provided fields
    api_config_dict = existing_api_config.copy()
    api_config_dict.update(provided_fields)
    
    # Handle API keys: if None was explicitly provided, clear it; if not provided, keep existing
    if "openai_api_key" in provided_fields:
        if provided_fields["openai_api_key"] is None or provided_fields["openai_api_key"] == "":
            api_config_dict["openai_api_key"] = None
        # else: use the provided value (already updated above)
    # else: keep existing (already in api_config_dict)
    
    if "deepseek_api_key" in provided_fields:
        if provided_fields["deepseek_api_key"] is None or provided_fields["deepseek_api_key"] == "":
            api_config_dict["deepseek_api_key"] = None
    
    if "mistral_api_key" in provided_fields:
        if provided_fields["mistral_api_key"] is None or provided_fields["mistral_api_key"] == "":
            api_config_dict["mistral_api_key"] = None
    
    if "gemini_api_key" in provided_fields:
        if provided_fields["gemini_api_key"] is None or provided_fields["gemini_api_key"] == "":
            api_config_dict["gemini_api_key"] = None
    
    prefs["api_config"] = api_config_dict
    current_user.preferences = prefs
    flag_modified(current_user, "preferences")
    db.commit()
    db.refresh(current_user)
    
    # Return config with masked keys for security
    # Also check environment variables for keys not in user config
    from backend.config import settings as app_settings
    
    response_dict = api_config_dict.copy()
    
    # Mask API keys (from user config or env)
    def mask_key(key_value: Optional[str]) -> Optional[str]:
        if not key_value:
            return None
        return "***" + key_value[-4:] if len(key_value) > 4 else "***"
    
    # Check user config first, then env vars
    response_dict["openai_api_key"] = mask_key(
        response_dict.get("openai_api_key") or app_settings.OPENAI_API_KEY
    )
    response_dict["deepseek_api_key"] = mask_key(
        response_dict.get("deepseek_api_key") or app_settings.DEEPSEEK_API_KEY
    )
    response_dict["mistral_api_key"] = mask_key(
        response_dict.get("mistral_api_key") or app_settings.MISTRAL_API_KEY
    )
    response_dict["gemini_api_key"] = mask_key(
        response_dict.get("gemini_api_key") or app_settings.GEMINI_API_KEY
    )
    
    return APIConfigSettings(**response_dict)
