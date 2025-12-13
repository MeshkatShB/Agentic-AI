"""Custom tool model."""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class CustomTool(Base):
    __tablename__ = "custom_tools"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Tool configuration
    permission_level = Column(String(50), default="safe")  # safe, read_files, write_files, network, etc.
    is_active = Column(Boolean, default=True)
    
    # Tool implementation
    code = Column(Text, nullable=False)  # Python code for the tool
    parameters_schema = Column(JSON, default=lambda: {})  # JSON schema for parameters
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    
    # Relationships
    creator = relationship("User", back_populates="custom_tools")
    
    def to_dict(self):
        """Convert custom tool to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "permission_level": self.permission_level,
            "is_active": self.is_active,
            "code": self.code,
            "parameters_schema": self.parameters_schema,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count
        }
