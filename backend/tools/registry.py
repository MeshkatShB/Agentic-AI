"""Tool registry for managing available tools."""

from typing import Dict, List, Optional, Type, Any, Callable
from .base import BaseTool, ToolPermission, ToolResult
import logging
import asyncio

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
        # Track custom tool versions by name to allow refresh on update
        self._custom_versions: Dict[str, str] = {}
    
    def _load_default_tools(self):
        """Load default tools."""
        from .implementations import (
            SearchLocalFilesTool,
            ReadFileTool,
            ParseDocumentTool,
            WebSearchTool,
            WebScrapeTool,
            HttpRequestTool,
            DatabaseQueryTool,
            WeatherAPITool,
            CustomAPITool,
            ScheduleJobTool,
        )
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
            
            # Web tools
            WebSearchTool,
            WebScrapeTool,
            HttpRequestTool,
            
            # API tools
            WeatherAPITool,
            CustomAPITool,
            
            # System and analysis tools
            SystemInfoTool,
            CodeAnalyzerTool,
            ImageAnalyzerTool,
            HashCalculatorTool,
            
            # Network tools
            NetworkToolkit,
            
            # Database tools
            DatabaseQueryTool,
            # Cron jobs (scheduled by chatbot)
            ScheduleJobTool,
        ]
        
        for tool_class in default_tools:
            self.register(tool_class)
        
        # Exchange (EWS) tools - only when exchangelib is available
        try:
            from .implementations.exchange_tools import (
                EWS_AVAILABLE,
                ExchangeListEmailsTool,
                ExchangeGetEmailTool,
                ExchangeSendEmailTool,
                ExchangeListCalendarTool,
                ExchangeCreateEventTool,
                ExchangeListTasksTool,
                ExchangeCreateTaskTool,
            )
            if EWS_AVAILABLE:
                exchange_tools = [
                    ExchangeListEmailsTool,
                    ExchangeGetEmailTool,
                    ExchangeSendEmailTool,
                    ExchangeListCalendarTool,
                    ExchangeCreateEventTool,
                    ExchangeListTasksTool,
                    ExchangeCreateTaskTool,
                ]
                for tool_class in exchange_tools:
                    self.register(tool_class)
        except ImportError:
            pass
    
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

    def list_builtin_tools(self) -> List[str]:
        """List only built-in (non-custom) tool names."""
        return [name for name in self.tools.keys() if name not in self._custom_versions]

    def is_custom_tool(self, name: str) -> bool:
        """Return True if the given tool name corresponds to a custom tool."""
        return name in self._custom_versions
    
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

    # -------------------- Custom tools runtime --------------------
    def _permission_from_string(self, level: str) -> ToolPermission:
        mapping = {
            "safe": ToolPermission.SAFE,
            "read_files": ToolPermission.READ_FILES,
            "write_files": ToolPermission.WRITE_FILES,
            "network": ToolPermission.NETWORK,
            "web_access": ToolPermission.WEB_ACCESS,
            "database_read": ToolPermission.DATABASE_READ,
            "database_write": ToolPermission.DATABASE_WRITE,
            "system": ToolPermission.SYSTEM,
            "system_read": ToolPermission.SYSTEM_READ,
        }
        return mapping.get((level or "").lower(), ToolPermission.SAFE)

    def register_custom_tool_config(self, cfg: Any) -> bool:
        """Register or refresh a custom tool from a DB config object.

        Expected fields on cfg: name, description, permission_level, parameters_schema, code, updated_at (optional)
        """
        try:
            tool_name = cfg.name
            version_key = str(getattr(cfg, "updated_at", ""))
            # Skip if same version already registered
            if tool_name in self.tools and self._custom_versions.get(tool_name) == version_key:
                return True

            permission = self._permission_from_string(cfg.permission_level)
            parameters_schema = cfg.parameters_schema or {"type": "object", "properties": {}, "required": []}
            user_code = cfg.code or ""

            # Prepare execution function from user code
            # Build a safe import mechanism with a conservative allowlist
            import builtins as _py_builtins  # local import
            _original_import = _py_builtins.__import__

            allowed_modules = {
                # Always-allowed standard libs (non-IO, non-system)
                "math", "random", "re", "json", "time", "datetime", "uuid", "base64", "hashlib", "typing", "asyncio",
            }
            # Allow-list specific internal module prefixes (narrow, not whole package)
            allowed_prefixes = {"backend.tools.base"}
            # Expand allowlist based on permission
            if permission in {ToolPermission.NETWORK, ToolPermission.WEB_ACCESS}:
                allowed_modules.update({"urllib", "urllib.parse", "httpx", "requests", "wikipedia"})
            if permission in {ToolPermission.DATABASE_READ, ToolPermission.DATABASE_WRITE}:
                allowed_modules.update({"sqlite3"})

            def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[override]
                top_level = name.split(".")[0]
                # Allow exact module names
                if top_level in allowed_modules:
                    return _original_import(name, globals, locals, fromlist, level)
                # Allow specific safe prefixes (e.g., 'backend.tools.base') only
                for prefix in allowed_prefixes:
                    if name == prefix or name.startswith(prefix + "."):
                        return _original_import(name, globals, locals, fromlist, level)
                raise ImportError(f"Module '{name}' is not allowed in custom tool")

            safe_globals = {
                "__builtins__": {
                    "len": len,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "range": range,
                    "enumerate": enumerate,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "sorted": sorted,
                    "print": print,
                    "__import__": _safe_import,
                },
                "ToolResult": ToolResult,
                "asyncio": asyncio,
            }
            local_ns: Dict[str, Any] = {}
            compiled = compile(user_code, f"<custom_tool_{tool_name}>", "exec")
            exec(compiled, safe_globals, local_ns)

            user_exec: Optional[Callable] = local_ns.get("execute")
            if not callable(user_exec):
                logger.error(f"Custom tool '{tool_name}' code must define an execute(**parameters) function")
                return False

            # Build dynamic BaseTool subclass that calls user code
            permission_value = permission
            description_value = cfg.description
            params_value = parameters_schema

            class _UserCustomTool(BaseTool):
                @property
                def name(self) -> str:
                    return tool_name

                @property
                def description(self) -> str:
                    return description_value

                @property
                def parameters(self) -> Dict[str, Any]:
                    return params_value

                @property
                def permission(self) -> ToolPermission:
                    return permission_value

                async def execute(self, **kwargs) -> ToolResult:
                    try:
                        if asyncio.iscoroutinefunction(user_exec):
                            return await user_exec(self, **kwargs)  # type: ignore[arg-type]
                        else:
                            # Run sync in thread to avoid blocking event loop
                            loop = asyncio.get_event_loop()
                            return await loop.run_in_executor(None, lambda: user_exec(self, **kwargs))  # type: ignore[misc]
                    except Exception as e:
                        return ToolResult(success=False, output=None, error=str(e))

            # Register/replace
            self.tools[tool_name] = Tool(_UserCustomTool)
            self._custom_versions[tool_name] = version_key
            logger.info(f"Registered custom tool: {tool_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register custom tool '{getattr(cfg, 'name', '?')}': {e}")
            return False

    def register_custom_tools_for_user(self, db: Any, user_id: int) -> int:
        """Load active custom tools for the user from DB and register them. Returns count."""
        try:
            from backend.models import CustomTool  # Local import to avoid cycles
            tools = db.query(CustomTool).filter(
                CustomTool.created_by == user_id,
                CustomTool.is_active == True
            ).all()
            count = 0
            for cfg in tools:
                if self.register_custom_tool_config(cfg):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error registering custom tools for user {user_id}: {e}")
            return 0


# Global registry instance
tool_registry = ToolRegistry()
