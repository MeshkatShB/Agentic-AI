"""Application configuration and settings."""

from typing import List, Optional
from pathlib import Path


class Settings:
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
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Better for Persian
    EMBEDDING_DIMENSION: int = 384  # Dimension for the multilingual model
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 200  # Overlap between chunks
    MAX_RETRIEVAL_RESULTS: int = 10  # Maximum results to retrieve
    
    # File Access
    ALLOWED_FILE_PATHS: List[str] = ["./data", "./documents"]
    BLOCKED_FILE_PATHS: List[str] = ["/etc", "/system32", "/Windows/System32"]
    MAX_FILE_SIZE_MB: int = 100
    
    # Agent Settings
    MAX_STEPS_PER_REQUEST: int = 10
    MAX_TOKENS_PER_STEP: int = 2000
    STEP_TIMEOUT_SECONDS: int = 30
    REQUIRE_TOOL_CONFIRMATION: bool = True
    
    # Web Search (Optional)
    ENABLE_WEB_SEARCH: bool = True
    SEARXNG_URL: Optional[str] = "http://localhost:8888/"
    WEB_SEARCH_TIMEOUT: int = 10
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
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
