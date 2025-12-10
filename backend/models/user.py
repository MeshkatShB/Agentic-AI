"""User model and settings."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    
    # Profile
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Preferences (stored as JSON)
    preferences = Column(JSON, default=lambda: {
        "theme": "dark",
        "model": "qwen3:latest",
        "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
        "temperature": 0.7,
        "max_steps": 10,
        "max_tokens": 2000,
        "require_confirmation": True
    })
    
    # Allowed tools (stored as JSON array)
    allowed_tools = Column(JSON, default=lambda: [
        "calculator",
        "search_local_files",
        "read_file"
    ])
    
    # File access paths (stored as JSON)
    allowed_paths = Column(JSON, default=lambda: [])
    blocked_paths = Column(JSON, default=lambda: [])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    custom_tools = relationship("CustomTool", back_populates="creator")
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "preferences": self.preferences,
            "allowed_tools": self.allowed_tools,
            "allowed_paths": self.allowed_paths,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
