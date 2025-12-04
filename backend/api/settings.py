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


@router.get("/user", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):
    """Get user settings."""
    
    prefs = current_user.preferences or {}
    
    return UserSettings(
        theme=prefs.get("theme", "dark"),
        model=prefs.get("model", app_settings.DEFAULT_MODEL),
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
    
    # Update preferences
    current_user.preferences = settings.model_dump()
    db.commit()
    
    # Clear agent to apply new settings
    from backend.agent import agent_executor
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
