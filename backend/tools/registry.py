"""Tool registry for managing available tools."""

from typing import Dict, List, Optional, Type
from .base import BaseTool, ToolPermission, ToolResult
import logging

logger = logging.getLogger(__name__)


class Tool:
    """Wrapper for a tool with metadata."""
    
    def __init__(self, tool_class: Type[BaseTool]):
        """Initialize tool wrapper."""
        self.tool_class = tool_class
        self.instance = tool_class()
        self.name = self.instance.name
        self.description = self.instance.description
        self.parameters = self.instance.parameters
        self.permission = self.instance.permission
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        return await self.instance.execute(**kwargs)
    
    def get_schema(self) -> Dict:
        """Get tool schema."""
        return self.instance.get_schema()


class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self):
        """Initialize the registry."""
        self.tools: Dict[str, Tool] = {}
        self._load_default_tools()
    
    def _load_default_tools(self):
        """Load default tools."""
        from .implementations import (
            SearchLocalFilesTool,
            ReadFileTool,
            ParseDocumentTool,
            WebSearchTool,
            WebScrapeTool,
            DatabaseQueryTool
        )
        from .implementations.langchain_rag import RAGTool, DocumentSummarizerTool
        from .implementations.advanced_tools import (
            SystemInfoTool,
            CodeAnalyzerTool,
            ImageAnalyzerTool,
            NetworkToolkit,
            HashCalculatorTool
        )
        
        default_tools = [
            # File and document tools
            SearchLocalFilesTool,
            ReadFileTool,
            ParseDocumentTool,
            DocumentSummarizerTool,
            
            # RAG and AI tools
            RAGTool,
            
            # Web tools
            WebSearchTool,
            WebScrapeTool,
            
            # System and analysis tools
            SystemInfoTool,
            CodeAnalyzerTool,
            ImageAnalyzerTool,
            HashCalculatorTool,
            
            # Network tools
            NetworkToolkit,
            
            # Database tools
            DatabaseQueryTool
        ]
        
        for tool_class in default_tools:
            self.register(tool_class)
    
    def register(self, tool_class: Type[BaseTool]) -> bool:
        """Register a new tool."""
        try:
            tool = Tool(tool_class)
            self.tools[tool.name] = tool
            logger.info(f"Registered tool: {tool.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool: {e}")
            return False
    
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_tools_for_user(self, allowed_tools: List[str]) -> List[Tool]:
        """Get tools available for a user."""
        user_tools = []
        for tool_name in allowed_tools:
            if tool_name in self.tools:
                user_tools.append(self.tools[tool_name])
        return user_tools
    
    def get_schemas_for_user(self, allowed_tools: List[str]) -> List[Dict]:
        """Get tool schemas for a user."""
        schemas = []
        for tool_name in allowed_tools:
            if tool_name in self.tools:
                schemas.append(self.tools[tool_name].get_schema())
        return schemas
    
    def check_permission(
        self,
        tool_name: str,
        user_permissions: List[ToolPermission]
    ) -> bool:
        """Check if user has permission to use a tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            return False
        
        # SAFE tools don't require permission
        if tool.permission == ToolPermission.SAFE:
            return True
        
        return tool.permission in user_permissions
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict,
        check_permission: bool = True,
        user_permissions: Optional[List[ToolPermission]] = None
    ) -> ToolResult:
        """Execute a tool."""
        
        # Get the tool
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{tool_name}' not found"
            )
        
        # Check permissions if required
        if check_permission and user_permissions is not None:
            if not self.check_permission(tool_name, user_permissions):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Permission denied for tool '{tool_name}'"
                )
        
        # Validate parameters
        if not tool.instance.validate_parameters(**parameters):
            return ToolResult(
                success=False,
                output=None,
                error="Invalid parameters"
            )
        
        # Execute the tool
        try:
            result = await tool.execute(**parameters)
            logger.info(f"Executed tool '{tool_name}' successfully")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


# Global registry instance
tool_registry = ToolRegistry()
