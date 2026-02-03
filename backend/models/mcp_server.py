"""MCP server model for storing MCP server configurations."""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    
    # Server configuration
    transport = Column(String(50), nullable=False)  # "http" or "stdio"
    
    # HTTP transport configuration
    url = Column(String(500))  # For HTTP transport
    
    # stdio transport configuration
    command = Column(String(200))  # Command to run (e.g., "python")
    args = Column(JSON, default=lambda: [])  # Arguments for stdio transport
    
    # Authentication and headers
    headers = Column(JSON, default=lambda: {})  # Custom headers for HTTP
    auth_config = Column(JSON, default=lambda: {})  # Auth configuration
    
    # Server status
    is_active = Column(Boolean, default=True)
    is_enabled = Column(Boolean, default=True)  # User can enable/disable without deleting
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Last connection test
    last_connected_at = Column(DateTime(timezone=True))
    last_error = Column(Text)
    last_tool_count = Column(Integer)  # Number of tools found in last successful test
    
    # Relationships
    creator = relationship("User", back_populates="mcp_servers")
    
    def to_dict(self):
        """Convert MCP server to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "transport": self.transport,
            "url": self.url,
            "command": self.command,
            "args": self.args or [],
            "headers": self.headers or {},
            "auth_config": self.auth_config or {},
            "is_active": self.is_active,
            "is_enabled": self.is_enabled,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "last_error": self.last_error,
            "last_tool_count": self.last_tool_count
        }
    
    def to_mcp_config(self) -> dict:
        """Convert to MCP client configuration format."""
        # For HTTP transport, use "streamable-http" explicitly
        # This ensures SSE support and proper header handling
        transport_type = "streamable-http" if self.transport == "http" else self.transport
        
        config = {
            "transport": transport_type
        }
        
        if self.transport == "http":
            config["url"] = self.url
            # Set headers - ensure Accept header includes text/event-stream for SSE
            headers = self.headers.copy() if self.headers else {}
            # Always include Accept header for streamable HTTP
            if "Accept" not in headers:
                headers["Accept"] = "application/json, text/event-stream"
            elif "text/event-stream" not in headers.get("Accept", ""):
                # Add text/event-stream if not present
                accept_val = headers["Accept"]
                headers["Accept"] = f"{accept_val}, text/event-stream"
            config["headers"] = headers
            if self.auth_config:
                config["auth"] = self.auth_config
        elif self.transport == "stdio":
            config["command"] = self.command
            if self.args:
                config["args"] = self.args
        
        return config

