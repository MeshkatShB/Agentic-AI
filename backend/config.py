"""Application configuration and settings."""

from typing import List, Optional, Union, Any
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Don't try to parse these fields as JSON from env vars
        env_parse_enums=False
    )
    
    # App
    APP_NAME: str = "Local AI Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./local_agent.db"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    DEFAULT_MODEL: str = "qwen3:latest"
    MODEL_TEMPERATURE: float = 0.7
    MODEL_MAX_TOKENS: int = 2000
    
    # Vector Storage
    VECTOR_STORE: str = "chroma"  # "chroma" or "qdrant"
    CHROMA_PATH: str = "./chroma_db"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "agent_memory"
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"  # Qwen3-0.6B model for better Persian support
    EMBEDDING_DIMENSION: int = 1024  # Dimension for the multilingual model
    EMBEDDING_DEVICE: str = "auto"  # "auto", "cpu", "cuda", "mps" (auto detects GPU, defaults to CPU if unavailable)
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 200  # Overlap between chunks
    MAX_RETRIEVAL_RESULTS: int = 10  # Maximum results to retrieve
    
    # File Access
    # Note: These are Union[str, List[str]] to allow comma-separated values from .env
    # The validator will convert them to List[str]
    ALLOWED_FILE_PATHS: Union[str, List[str]] = ["./data", "./documents"]
    BLOCKED_FILE_PATHS: Union[str, List[str]] = ["/etc", "/system32", "/Windows/System32"]
    MAX_FILE_SIZE_MB: int = 100
    
    # Agent Settings
    MAX_STEPS_PER_REQUEST: int = 10
    MAX_TOKENS_PER_STEP: int = 2000
    STEP_TIMEOUT_SECONDS: int = 30
    REQUIRE_TOOL_CONFIRMATION: bool = True
    USE_LANGGRAPH: bool = False  # Deprecated
    REASONING_MODE: str = "simple"  # Deprecated
    AGENT_TYPE: str = "simple"  # Only base Agent is used
    
    # Web Search (Optional)
    ENABLE_WEB_SEARCH: bool = True
    SEARXNG_URL: Optional[str] = "http://localhost:8888/"
    WEB_SEARCH_TIMEOUT: int = 10
    
    # CORS
    # Chrome extensions use chrome-extension:// protocol, which needs special handling
    # Use "*" to allow all origins (less secure) or specify exact origins
    # CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8080"]
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    
    # External API Keys (Optional - can be set via environment variables)
    # These are used as fallbacks if not configured per-user in the database
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    @field_validator('ALLOWED_FILE_PATHS', 'BLOCKED_FILE_PATHS', 'CORS_ORIGINS', mode='before')
    @classmethod
    def parse_comma_separated(cls, v: Any) -> List[str]:
        """Parse comma-separated strings from .env file into lists."""
        if v is None:
            return []
        if isinstance(v, str):
            if not v.strip():
                return []
            return [item.strip() for item in v.split(',') if item.strip()]
        if isinstance(v, list):
            return v
        return []
        
    def get_allowed_paths(self) -> List[Path]:
        """Get resolved allowed file paths."""
        return [Path(p).resolve() for p in self.ALLOWED_FILE_PATHS]
    
    def get_blocked_paths(self) -> List[Path]:
        """Get resolved blocked file paths."""
        return [Path(p).resolve() for p in self.BLOCKED_FILE_PATHS]
    
    def is_path_allowed(self, path: Path) -> bool:
        """Check if a path is allowed for access."""
        resolved_path = path.resolve()
        
        # Check blocked paths first
        for blocked in self.get_blocked_paths():
            try:
                resolved_path.relative_to(blocked)
                return False  # Path is under a blocked directory
            except ValueError:
                pass
        
        # Check if path is under allowed directories
        for allowed in self.get_allowed_paths():
            try:
                resolved_path.relative_to(allowed)
                return True
            except ValueError:
                pass
        
        return False  # Not in allowed paths


settings = Settings()
