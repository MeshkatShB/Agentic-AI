"""Base tool classes and structures."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ToolPermission(str, Enum):
    """Tool permission levels."""
    SAFE = "safe"  # No permission needed
    READ_FILES = "read_files"  # Can read local files
    WRITE_FILES = "write_files"  # Can write local files
    NETWORK = "network"  # Can access network
    WEB_ACCESS = "web_access"  # Can access web/internet
    DATABASE_READ = "database_read"  # Can read from database
    DATABASE_WRITE = "database_write"  # Can write to database
    SYSTEM = "system"  # Can execute system commands
    SYSTEM_READ = "system_read"  # Can read system information


class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Base class for all tools."""
    
    def __init__(self):
        """Initialize the tool."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema."""
        pass
    
    @property
    @abstractmethod
    def permission(self) -> ToolPermission:
        """Required permission level."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema for LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "permission": self.permission.value
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """Validate tool parameters."""
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # Check required parameters
        for param in required:
            if param not in kwargs:
                return False
        
        # Check parameter types (basic validation)
        for param, value in kwargs.items():
            if param not in properties:
                continue
            
            expected_type = properties[param].get("type")
            if expected_type:
                if expected_type == "string" and not isinstance(value, str):
                    return False
                elif expected_type == "integer" and not isinstance(value, int):
                    return False
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False
                elif expected_type == "array" and not isinstance(value, list):
                    return False
                elif expected_type == "object" and not isinstance(value, dict):
                    return False
        
        return True
    
    def format_output(self, output: Any) -> str:
        """Format tool output for display."""
        if isinstance(output, dict):
            import json
            return json.dumps(output, indent=2)
        elif isinstance(output, list):
            return "\n".join(str(item) for item in output)
        else:
            return str(output)
