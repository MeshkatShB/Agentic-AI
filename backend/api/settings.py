"""Settings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from backend.models import get_db, User, TelegramPairing, MCPServer
from backend.auth import get_current_user
import secrets
import string
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


@router.get("/api-models/{provider}")
async def get_provider_models(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """Get available models for a specific provider."""
    import httpx
    import logging
    
    logger = logging.getLogger(__name__)
    
    prefs = current_user.preferences or {}
    api_config = prefs.get("api_config", {})
    
    # Get API key and endpoint from user config or environment
    from backend.config import settings as app_settings
    
    def get_api_key(key_name: str, env_key: str) -> Optional[str]:
        user_key = api_config.get(key_name)
        if user_key:
            return user_key
        return getattr(app_settings, env_key, None)
    
    try:
        if provider == "openai":
            api_key = get_api_key("openai_api_key", "OPENAI_API_KEY")
            api_endpoint = api_config.get("openai_api_endpoint", "https://api.openai.com/v1")
            
            if not api_key:
                return {
                    "error": "OpenAI API key not configured. Please set it in API Configuration.",
                    "models": []
                }
            
            # Fetch models from OpenAI API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{api_endpoint}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Filter for chat models (gpt-* models)
                    models = [
                        model["id"] for model in data.get("data", [])
                        if model["id"].startswith("gpt-") or model["id"].startswith("o1-")
                    ]
                    # Sort models (newer first, then alphabetically)
                    models.sort(reverse=True)
                    return {"models": models, "error": None}
                else:
                    return {
                        "error": f"Failed to fetch models: {response.text}",
                        "models": []
                    }
        
        elif provider == "deepseek":
            api_key = get_api_key("deepseek_api_key", "DEEPSEEK_API_KEY")
            api_endpoint = api_config.get("deepseek_api_endpoint", "https://api.deepseek.com/v1")
            
            if not api_key:
                return {
                    "error": "DeepSeek API key not configured. Please set it in API Configuration.",
                    "models": []
                }
            
            # DeepSeek uses OpenAI-compatible API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{api_endpoint}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = [
                        model["id"] for model in data.get("data", [])
                        if "deepseek" in model["id"].lower()
                    ]
                    models.sort(reverse=True)
                    return {"models": models, "error": None}
                else:
                    return {
                        "error": f"Failed to fetch models: {response.text}",
                        "models": []
                    }
        
        elif provider == "mistral":
            api_key = get_api_key("mistral_api_key", "MISTRAL_API_KEY")
            api_endpoint = api_config.get("mistral_api_endpoint", "https://api.mistral.ai/v1")
            
            if not api_key:
                return {
                    "error": "Mistral API key not configured. Please set it in API Configuration.",
                    "models": []
                }
            
            # Mistral uses OpenAI-compatible API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{api_endpoint}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = [
                        model["id"] for model in data.get("data", [])
                        if "mistral" in model["id"].lower()
                    ]
                    models.sort(reverse=True)
                    return {"models": models, "error": None}
                else:
                    return {
                        "error": f"Failed to fetch models: {response.text}",
                        "models": []
                    }
        
        elif provider == "gemini":
            api_key = get_api_key("gemini_api_key", "GEMINI_API_KEY")
            
            if not api_key:
                return {
                    "error": "Gemini API key not configured. Please set it in API Configuration.",
                    "models": []
                }
            
            # Google Gemini uses a different API endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Filter for chat models
                    models = [
                        model["name"].replace("models/", "") 
                        for model in data.get("models", [])
                        if "generateContent" in model.get("supportedGenerationMethods", [])
                    ]
                    models.sort(reverse=True)
                    return {"models": models, "error": None}
                else:
                    return {
                        "error": f"Failed to fetch models: {response.text}",
                        "models": []
                    }
        
        else:
            return {
                "error": f"Unknown provider: {provider}",
                "models": []
            }
    
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching models for {provider}")
        return {
            "error": "Request timeout. Please check your API endpoint and try again.",
            "models": []
        }
    except Exception as e:
        logger.error(f"Error fetching models for {provider}: {e}", exc_info=True)
        return {
            "error": f"Failed to fetch models: {str(e)}",
            "models": []
        }


# --- Telegram bot settings (pairing by username) ---
TELEGRAM_CODE_CHARS = string.ascii_uppercase + string.digits
TELEGRAM_CODE_LENGTH = 8


def _telegram_generate_pairing_code() -> str:
    return "".join(secrets.choice(TELEGRAM_CODE_CHARS) for _ in range(TELEGRAM_CODE_LENGTH))


class TelegramSettingsResponse(BaseModel):
    """Telegram bot and pairing status plus chat environment (tools, MCP)."""
    enabled: bool
    has_token: bool
    bot_username: Optional[str] = None
    pairing_code: Optional[str] = None
    is_paired: bool
    telegram_username: Optional[str] = None
    telegram_tools: Optional[List[str]] = None
    telegram_use_mcp: bool = True
    telegram_mcp_server_ids: Optional[List[int]] = None
    telegram_simple_agent: bool = False
    available_tools: List[str] = []
    mcp_servers: List[Dict] = []


class TelegramConfigUpdate(BaseModel):
    """Update Telegram chat environment (tools and MCP)."""
    telegram_tools: Optional[List[str]] = None
    telegram_use_mcp: Optional[bool] = None
    telegram_mcp_server_ids: Optional[List[int]] = None
    telegram_simple_agent: Optional[bool] = None


@router.get("/telegram", response_model=TelegramSettingsResponse)
async def get_telegram_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get Telegram bot status, pairing, and chat environment (tools/MCP) with available options."""
    enabled = getattr(app_settings, "ENABLE_TELEGRAM_BOT", False)
    token = (getattr(app_settings, "TELEGRAM_BOT_TOKEN", None) or "").strip()
    has_token = bool(token)

    pairing = db.query(TelegramPairing).filter(TelegramPairing.user_id == current_user.id).first()
    if not pairing:
        pairing = TelegramPairing(user_id=current_user.id, pairing_code=_telegram_generate_pairing_code())
        db.add(pairing)
        db.commit()
        db.refresh(pairing)
    is_paired = pairing.telegram_user_id is not None
    pairing_code = pairing.pairing_code if not is_paired else None
    telegram_username = pairing.telegram_username or None

    prefs = current_user.preferences or {}
    telegram_tools = prefs.get("telegram_tools")
    telegram_use_mcp = prefs.get("telegram_use_mcp", True)
    telegram_mcp_server_ids = prefs.get("telegram_mcp_server_ids")
    telegram_simple_agent = prefs.get("telegram_simple_agent", False)

    available_tools = list(current_user.allowed_tools or [])
    mcp_servers = [
        {"id": s.id, "name": s.name, "is_enabled": s.is_enabled}
        for s in db.query(MCPServer).filter(
            MCPServer.created_by == current_user.id,
            MCPServer.is_active == True
        ).all()
    ]

    return TelegramSettingsResponse(
        enabled=enabled and has_token,
        has_token=has_token,
        bot_username=None,
        pairing_code=pairing_code,
        is_paired=is_paired,
        telegram_username=telegram_username or None,
        telegram_tools=telegram_tools,
        telegram_use_mcp=telegram_use_mcp,
        telegram_mcp_server_ids=telegram_mcp_server_ids,
        telegram_simple_agent=telegram_simple_agent,
        available_tools=available_tools,
        mcp_servers=mcp_servers,
    )


@router.put("/telegram/config", response_model=TelegramSettingsResponse)
async def update_telegram_config(
    body: TelegramConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update Telegram chat environment: which tools and MCP servers to use, and simple agent mode."""
    from sqlalchemy.orm.attributes import flag_modified
    prefs = current_user.preferences or {}
    if body.telegram_tools is not None:
        prefs["telegram_tools"] = body.telegram_tools
    if body.telegram_use_mcp is not None:
        prefs["telegram_use_mcp"] = body.telegram_use_mcp
    if body.telegram_mcp_server_ids is not None:
        prefs["telegram_mcp_server_ids"] = body.telegram_mcp_server_ids
    if body.telegram_simple_agent is not None:
        prefs["telegram_simple_agent"] = body.telegram_simple_agent
    current_user.preferences = prefs
    flag_modified(current_user, "preferences")
    db.commit()
    db.refresh(current_user)
    return await get_telegram_settings(current_user=current_user, db=db)


@router.post("/telegram/pairing-code")
async def regenerate_telegram_pairing_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate or regenerate pairing code for the current user. Unpairs existing Telegram if any."""
    pairing = db.query(TelegramPairing).filter(TelegramPairing.user_id == current_user.id).first()
    new_code = _telegram_generate_pairing_code()
    if pairing:
        pairing.pairing_code = new_code
        pairing.telegram_user_id = None
        pairing.telegram_username = None
        pairing.paired_at = None
        db.commit()
        db.refresh(pairing)
    else:
        pairing = TelegramPairing(user_id=current_user.id, pairing_code=new_code)
        db.add(pairing)
        db.commit()
        db.refresh(pairing)
    return {"pairing_code": new_code}
