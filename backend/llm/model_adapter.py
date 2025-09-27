"""Model adapters for different LLM formats."""

import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import re


class ModelAdapter(ABC):
    """Base adapter for different model formats."""
    
    @abstractmethod
    def format_tools(self, tools: List[Dict]) -> str:
        """Format tools for the model's expected format."""
        pass
    
    @abstractmethod
    def parse_tool_calls(self, response: str) -> List[Dict]:
        """Parse tool calls from model response."""
        pass
    
    @abstractmethod
    def format_system_prompt(self, base_prompt: str, tools: Optional[List[Dict]] = None) -> str:
        """Format the system prompt with tool information."""
        pass


class QwenAdapter(ModelAdapter):
    """Adapter for Qwen models with tool calling support."""
    
    def format_tools(self, tools: List[Dict]) -> str:
        """Format tools for Qwen's expected format."""
        
        tool_descriptions = []
        for tool in tools:
            params = tool.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])
            
            # Build parameter descriptions
            param_desc = []
            for name, spec in properties.items():
                param_type = spec.get("type", "string")
                description = spec.get("description", "")
                is_required = name in required
                param_desc.append(
                    f"  - {name}: {param_type} {'(required)' if is_required else '(optional)'} - {description}"
                )
            
            tool_str = f"""Tool: {tool['name']}
Description: {tool.get('description', '')}
Parameters:
{chr(10).join(param_desc)}"""
            
            tool_descriptions.append(tool_str)
        
        return "\n\n".join(tool_descriptions)
    
    def parse_tool_calls(self, response: str) -> List[Dict]:
        """Parse tool calls from Qwen model response."""
        
        tool_calls = []
        
        # Format 1: Simple format - TOOL_CALL: tool_name followed by JSON on same or next line
        pattern1 = r'TOOL_CALL:\s*(\w+)\s*\n?\s*(\{[^{}]*\}|\{[\s\S]*?\})'
        matches = re.findall(pattern1, response, re.DOTALL)
        for tool_name, args_str in matches:
            try:
                args = json.loads(args_str.strip()) if args_str.strip() else {}
                tool_calls.append({
                    "name": tool_name,
                    "arguments": args
                })
            except Exception as e:
                # More flexible parsing - try to extract any JSON-like structure
                args = {}
                # Remove extra whitespace and newlines
                clean_args = args_str.strip().replace('\n', ' ')
                # Try to find key-value pairs in various formats
                if clean_args:
                    try:
                        # Try again with cleaned string
                        args = json.loads(clean_args)
                    except:
                        # Manual parsing as fallback
                        for match in re.findall(r'"([^"]+)":\s*"([^"]+)"', clean_args):
                            key, value = match
                            args[key] = value
                        # Also try without quotes
                        for match in re.findall(r'(\w+):\s*"([^"]+)"', clean_args):
                            key, value = match
                            args[key] = value
                
                tool_calls.append({
                    "name": tool_name,
                    "arguments": args
                })
        
        # Format 1b: Even simpler - TOOL_CALL: tool_name on one line, JSON on next line
        pattern1b = r'TOOL_CALL:\s*(\w+)\s*\n\s*(\{[^}]*\})'
        matches = re.findall(pattern1b, response, re.MULTILINE)
        for tool_name, args_str in matches:
            try:
                args = json.loads(args_str.strip()) if args_str.strip() else {}
                tool_calls.append({
                    "name": tool_name,
                    "arguments": args
                })
            except Exception as e:
                tool_calls.append({
                    "name": tool_name,
                    "arguments": {"query": args_str.strip()}
                })
        
        # Format 2: Legacy format - TOOL_CALL: tool_name(args)
        pattern2 = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.findall(pattern2, response, re.DOTALL)
        for tool_name, args_str in matches:
            try:
                # Try to parse as JSON
                args = json.loads(args_str) if args_str else {}
            except:
                # Fallback to simple key=value parsing
                args = {}
                for match in re.findall(r'(\w+)=([^,]+)', args_str):
                    key, value = match
                    # Clean up quotes
                    value = value.strip().strip('"\'')
                    args[key] = value
            
            tool_calls.append({
                "name": tool_name,
                "arguments": args
            })
        
        # Format 3: JSON format
        json_pattern = r'\{[^{}]*"tool"[^{}]*\}'
        json_matches = re.findall(json_pattern, response)
        for match in json_matches:
            try:
                tool_data = json.loads(match)
                if "tool" in tool_data:
                    tool_calls.append({
                        "name": tool_data["tool"],
                        "arguments": tool_data.get("arguments", {})
                    })
            except:
                pass
        
        # Format 4: Function call format
        func_pattern = r'<function>(\w+)</function>\s*<arguments>(.*?)</arguments>'
        func_matches = re.findall(func_pattern, response, re.DOTALL)
        for tool_name, args_str in func_matches:
            try:
                args = json.loads(args_str)
            except:
                args = {"query": args_str.strip()}
            
            tool_calls.append({
                "name": tool_name,
                "arguments": args
            })
        
        return tool_calls
    
    def format_system_prompt(self, base_prompt: str, tools: Optional[List[Dict]] = None) -> str:
        """Format the system prompt with tool information for Qwen."""
        
        prompt = base_prompt
        
        if tools:
            tool_desc = self.format_tools(tools)
            prompt = f"""{base_prompt}

AVAILABLE TOOLS:
{tool_desc}

Remember: Use the exact format shown in the instructions above!"""
        
        return prompt


class Llama3Adapter(ModelAdapter):
    """Adapter for Llama 3 models."""
    
    def format_tools(self, tools: List[Dict]) -> str:
        """Format tools for Llama 3."""
        # Similar to Qwen but might need adjustments based on Llama 3 specifics
        return QwenAdapter().format_tools(tools)
    
    def parse_tool_calls(self, response: str) -> List[Dict]:
        """Parse tool calls from Llama 3 response."""
        # Similar parsing logic, might need model-specific adjustments
        return QwenAdapter().parse_tool_calls(response)
    
    def format_system_prompt(self, base_prompt: str, tools: Optional[List[Dict]] = None) -> str:
        """Format system prompt for Llama 3."""
        # Adjust prompt format for Llama 3 if needed
        return QwenAdapter().format_system_prompt(base_prompt, tools)


class ModelAdapterFactory:
    """Factory for creating model adapters."""
    
    _adapters = {
        "qwen": QwenAdapter,
        "qwen2": QwenAdapter,
        "qwen3:latest": QwenAdapter,
        "llama3": Llama3Adapter,
        "llama": Llama3Adapter
    }
    
    @classmethod
    def get_adapter(cls, model_name: str) -> ModelAdapter:
        """Get the appropriate adapter for a model."""
        
        # Extract base model name
        base_name = model_name.lower().split(":")[0].split("-")[0]
        
        # Find matching adapter
        for key, adapter_class in cls._adapters.items():
            if base_name.startswith(key):
                return adapter_class()
        
        # Default to Qwen adapter
        return QwenAdapter()
