"""LangChain tool adapter for converting BaseTool to LangChain tools."""

from typing import Any, Dict, Optional, Annotated
from langchain_core.tools import BaseTool as LangChainBaseTool, StructuredTool
from pydantic import BaseModel, Field, ConfigDict
import asyncio
import logging

from backend.tools.base import BaseTool, ToolResult
from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class LangChainToolAdapter:
    """Adapter to convert BaseTool instances to LangChain tools."""
    
    @staticmethod
    def convert_tool(base_tool_instance: BaseTool) -> LangChainBaseTool:
        """Convert a BaseTool instance to a LangChain tool."""
        
        tool_name = base_tool_instance.name
        tool_description = base_tool_instance.description
        tool_params = base_tool_instance.parameters
        
        # Extract parameter schema for LangChain
        properties = tool_params.get("properties", {})
        required = tool_params.get("required", [])
        
        # Create Pydantic model for tool arguments
        annotations = {}
        field_defaults = {}
        
        for param_name, param_spec in properties.items():
            param_type = param_spec.get("type", "string")
            param_desc = param_spec.get("description", "")
            param_default = param_spec.get("default")
            is_required = param_name in required
            
            # Map JSON schema types to Python types
            python_type = str
            if param_type == "integer":
                python_type = int
            elif param_type == "number":
                python_type = float
            elif param_type == "boolean":
                python_type = bool
            elif param_type == "array":
                python_type = list
            elif param_type == "object":
                python_type = dict
            
            # Create annotation and field
            if is_required:
                annotations[param_name] = Annotated[python_type, Field(description=param_desc)]
            else:
                # For optional fields, use Optional with default
                default_value = param_default if param_default is not None else None
                annotations[param_name] = Annotated[
                    Optional[python_type], 
                    Field(default=default_value, description=param_desc)
                ]
                field_defaults[param_name] = default_value
        
        # Create dynamic Pydantic model for arguments
        model_config = ConfigDict(arbitrary_types_allowed=True)
        
        # Handle "json" field name conflict (shadows BaseModel.json)
        if "json" in annotations:
            # Rename to json_data to avoid shadowing
            if "json" in field_defaults:
                field_defaults["json_data"] = field_defaults.pop("json")
            annotations["json_data"] = annotations.pop("json")
        
        # Build the class dictionary
        class_dict = {
            "__annotations__": annotations,
            "model_config": model_config,
            **field_defaults
        }
        
        ToolArgs = type(
            f"{tool_name}Args",
            (BaseModel,),
            class_dict
        )
        
        # Create async tool function
        async def tool_func(**kwargs) -> str:
            """Execute the tool and return result as string."""
            try:
                # Handle renamed json field
                if "json_data" in kwargs and "json" not in kwargs:
                    kwargs["json"] = kwargs.pop("json_data")
                
                # Get the tool instance from registry
                tool_wrapper = tool_registry.get_tool(tool_name)
                if not tool_wrapper:
                    return f"Error: Tool '{tool_name}' not found"
                
                # Execute the tool (it's already async)
                result: ToolResult = await tool_wrapper.execute(**kwargs)
                
                # Format the result
                if result.success:
                    if isinstance(result.output, (dict, list)):
                        import json
                        return json.dumps(result.output, indent=2, ensure_ascii=False)
                    return str(result.output)
                else:
                    return f"Error: {result.error}"
                    
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                return f"Error: {str(e)}"
        
        # Create LangChain tool using StructuredTool.from_function
        # For async tools, LangChain automatically detects coroutine functions
        langchain_tool = StructuredTool.from_function(
            coroutine=tool_func,  # Use coroutine for async functions
            name=tool_name,
            description=tool_description,
            args_schema=ToolArgs
        )
        
        return langchain_tool
    
    @staticmethod
    def convert_tools_for_user(allowed_tool_names: list, user_id: int = None) -> list[LangChainBaseTool]:
        """Convert multiple tools for a user to LangChain tools."""
        langchain_tools = []
        
        for tool_name in allowed_tool_names:
            tool_wrapper = tool_registry.get_tool(tool_name)
            if tool_wrapper:
                try:
                    # For search_local_files, inject user_id
                    if tool_name == "search_local_files" and user_id is not None:
                        langchain_tool = LangChainToolAdapter.convert_tool_with_user(
                            tool_wrapper.instance, user_id
                        )
                    else:
                        langchain_tool = LangChainToolAdapter.convert_tool(tool_wrapper.instance)
                    langchain_tools.append(langchain_tool)
                except Exception as e:
                    logger.error(f"Failed to convert tool {tool_name} to LangChain: {e}", exc_info=True)
        
        return langchain_tools
    
    @staticmethod
    def convert_tool_with_user(base_tool_instance: BaseTool, user_id: int) -> LangChainBaseTool:
        """Convert a BaseTool instance to a LangChain tool with user context."""
        tool_name = base_tool_instance.name
        tool_description = base_tool_instance.description
        tool_params = base_tool_instance.parameters
        
        # Extract parameter schema for LangChain
        properties = tool_params.get("properties", {})
        required = tool_params.get("required", [])
        
        # Create Pydantic model for tool arguments
        annotations = {}
        field_defaults = {}
        
        for param_name, param_spec in properties.items():
            param_type = param_spec.get("type", "string")
            param_desc = param_spec.get("description", "")
            param_default = param_spec.get("default")
            is_required = param_name in required
            
            # Map JSON schema types to Python types
            python_type = str
            if param_type == "integer":
                python_type = int
            elif param_type == "number":
                python_type = float
            elif param_type == "boolean":
                python_type = bool
            elif param_type == "array":
                python_type = list
            elif param_type == "object":
                python_type = dict
            
            # Create annotation and field
            if is_required:
                annotations[param_name] = Annotated[python_type, Field(description=param_desc)]
            else:
                default_value = param_default if param_default is not None else None
                annotations[param_name] = Annotated[
                    Optional[python_type], 
                    Field(default=default_value, description=param_desc)
                ]
                field_defaults[param_name] = default_value
        
        # Create dynamic Pydantic model for arguments
        model_config = ConfigDict(arbitrary_types_allowed=True)
        
        # Handle "json" field name conflict
        if "json" in annotations:
            if "json" in field_defaults:
                field_defaults["json_data"] = field_defaults.pop("json")
            annotations["json_data"] = annotations.pop("json")
        
        class_dict = {
            "__annotations__": annotations,
            "model_config": model_config,
            **field_defaults
        }
        
        ToolArgs = type(
            f"{tool_name}Args",
            (BaseModel,),
            class_dict
        )
        
        # Create async tool function with user_id injected
        async def tool_func(**kwargs) -> str:
            """Execute the tool with user context and return result as string."""
            try:
                # Inject user_id for search_local_files
                if tool_name == "search_local_files":
                    kwargs["user_id"] = user_id
                
                # Handle renamed json field
                if "json_data" in kwargs and "json" not in kwargs:
                    kwargs["json"] = kwargs.pop("json_data")
                
                # Get the tool instance from registry
                tool_wrapper = tool_registry.get_tool(tool_name)
                if not tool_wrapper:
                    return f"Error: Tool '{tool_name}' not found"
                
                # Execute the tool (it's already async)
                result: ToolResult = await tool_wrapper.execute(**kwargs)
                
                # Format the result
                if result.success:
                    if isinstance(result.output, (dict, list)):
                        import json
                        return json.dumps(result.output, indent=2, ensure_ascii=False)
                    return str(result.output)
                else:
                    return f"Error: {result.error}"
                    
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                return f"Error: {str(e)}"
        
        # Create LangChain tool
        langchain_tool = StructuredTool.from_function(
            coroutine=tool_func,
            name=tool_name,
            description=tool_description,
            args_schema=ToolArgs
        )
        
        return langchain_tool
