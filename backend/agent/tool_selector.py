"""Intelligent tool selection using LLM."""

from typing import List, Dict, Optional, Tuple
from backend.tools import tool_registry
from backend.llm import OllamaClient
from backend.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class ToolSelector:
    """Intelligently selects the most appropriate tool using LLM reasoning."""
    
    def __init__(self):
        """Initialize the tool selector."""
        self.llm_client = OllamaClient()
    
    async def plan_tools(self, query: str, available_tools: List[str]) -> List[Tuple[str, Dict]]:
        """
        Produce an ordered multi-step tool plan.

        Returns a list of (tool_name, suggested_args). Empty list if no plan.
        """
        logger.info(f"ToolSelector.plan_tools called with tools: {available_tools}")
        if not available_tools:
            return []

        # Gather tool descriptions
        tool_descriptions = []
        for tool_name in available_tools:
            tool = tool_registry.get_tool(tool_name)
            if tool:
                tool_descriptions.append({
                    "name": tool_name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                })

        # Simple deterministic fallbacks
        ql = (query or "").lower()
        # If searching then reading files makes sense
        if ("search" in ql or "find" in ql or "جستجو" in ql) and "search_local_files" in available_tools:
            plan: List[Tuple[str, Dict]] = [("search_local_files", {"query": query.strip(), "top_k": 5})]
            # If read_file is also available and user mentions a specific filename, add it second
            if "read_file" in available_tools and (".txt" in ql or ".md" in ql or ".py" in ql):
                plan.append(("read_file", {"path": query.strip()}))
            return plan

        # LLM-based planner
        tools_info_lines = []
        for t in tool_descriptions:
            tools_info_lines.append(f"- {t['name']}: {t['description']}")
        tools_info = "\n".join(tools_info_lines)

        plan_prompt = f"""You are a tool planner. Given a user query and available tools, plan a short sequence
of up to 3 steps to solve the task. Use tools only from the list. Prefer minimal steps.

User Query: "{query}"

Available Tools:\n{tools_info}

Return ONLY JSON with this exact shape:
{{
  "steps": [
    {{ "tool": "tool_name", "parameters": {{ ... }} }},
    ...
  ]
}}

For search tasks, ensure parameters include a non-empty "query" string.
"""

        try:
            response_text = ""
            async for chunk in self.llm_client.chat(
                model=settings.DEFAULT_MODEL,
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.1,
                max_tokens=600,
                stream=True,
            ):
                if "message" in chunk:
                    response_text += chunk["message"].get("content", "")

            # Extract JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start < 0 or json_end <= json_start:
                return []
            import json as _json
            data = _json.loads(response_text[json_start:json_end])
            steps = data.get("steps", []) or []

            plan: List[Tuple[str, Dict]] = []
            for item in steps:
                name = item.get("tool")
                params = item.get("parameters", {})
                if name in available_tools:
                    # Validate/clean via existing helper
                    plan.append((name, self._validate_parameters(name, params)))
            return plan
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return []

    async def analyze_query(self, query: str, available_tools: List[str]) -> Optional[Tuple[str, Dict]]:
        """
        Analyze user query and intelligently select the most appropriate tool using LLM.
        
        Args:
            query: User's query
            available_tools: List of available tool names for the user
            
        Returns:
            Tuple of (tool_name, suggested_args) or None if no tool matches
        """
        logger.info(f"ToolSelector.analyze_query called with available_tools: {available_tools}")
        
        if not available_tools:
            logger.debug("No available tools provided")
            return None
        
        # Get tool descriptions for available tools
        tool_descriptions = []
        for tool_name in available_tools:
            tool = tool_registry.get_tool(tool_name)
            if tool:
                tool_descriptions.append({
                    "name": tool_name,
                    "description": tool.description,
                    "parameters": tool.parameters
                })
        
        if not tool_descriptions:
            logger.debug("No valid tools found in registry")
            return None
        
        # Simple rule-based fallback when LLM is not available
        query_lower = query.lower()
        
        # Handle scraping requests
        if any(word in query_lower for word in ['scrape', 'اسکرپ', 'extract', 'get content from']):
            if 'scrape_webpage' in available_tools:
                # Extract URL from query
                import re
                # Look for URLs or domain names in the query
                url_patterns = [
                    r'https?://[^\s]+',  # Full URLs
                    r'www\.[^\s]+',      # www.domain.com
                    r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'  # domain.com or domain.com/path
                ]
                
                extracted_url = None
                for pattern in url_patterns:
                    matches = re.findall(pattern, query)
                    if matches:
                        extracted_url = matches[0]
                        break
                
                if extracted_url:
                    logger.info(f"Rule-based selection: scrape_webpage with url '{extracted_url}'")
                    return 'scrape_webpage', {'url': extracted_url}
        
        # Handle search requests
        if any(word in query_lower for word in ['فایل', 'file', 'جستجو', 'search', 'پیدا', 'find', 'باگ', 'bug']):
            if 'search_local_files' in available_tools:
                # Extract search terms from Persian query
                search_terms = query.strip()
                # Remove common Persian question words
                search_terms = search_terms.replace('در فایلها راجع به', '').replace('چی گفته شده؟', '').replace('؟', '').strip()
                
                logger.info(f"Rule-based selection: search_local_files with query '{search_terms}'")
                return 'search_local_files', {'query': search_terms, 'top_k': 5}
        
        # Create a prompt for the LLM to select the best tool
        tools_info = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in tool_descriptions
        ])
        
        selection_prompt = f"""You are a tool selection assistant. Given a user query and available tools, select the most appropriate tool and suggest parameters.

User Query: "{query}"

Available Tools:
{tools_info}

Your task:
1. Analyze the user's intent
2. Select the most appropriate tool from the list above
3. Suggest appropriate parameters for that tool

IMPORTANT: 
- For search tools, extract the actual search terms from the user query
- If the user asks to search for something, use the search terms as the "query" parameter
- For scraping tools, extract the URL/domain from the user query
- For Persian queries, extract the Persian search terms
- Don't leave required parameters empty - extract meaningful values

Examples:
- User: "search for bug reports" → query: "bug reports"
- User: "find documents about performance" → query: "performance"
- User: "go scrape digikala.com" → url: "digikala.com"
- User: "scrape https://example.com" → url: "https://example.com"
- User: "extract content from google.com" → url: "google.com"
- User: "دستور العمل کنترل عملکرد سرور" → query: "دستور العمل کنترل عملکرد سرور"

Respond with ONLY a JSON object in this exact format:
{{
    "selected_tool": "tool_name",
    "reasoning": "brief explanation of why this tool was selected",
    "suggested_parameters": {{
        "query": "extracted_search_terms",
        "url": "extracted_url",
        "other_parameter": "value"
    }}
}}

If no tool is appropriate, respond with:
{{
    "selected_tool": null,
    "reasoning": "explanation of why no tool is suitable"
}}"""

        try:
            # Get LLM response
            response_text = ""
            async for chunk in self.llm_client.chat(
                model=settings.DEFAULT_MODEL,
                messages=[{"role": "user", "content": selection_prompt}],
                temperature=0.1,  # Low temperature for consistent selection
                max_tokens=500,
                stream=True
            ):
                if "message" in chunk:
                    response_text += chunk["message"].get("content", "")
            
            # Parse the JSON response
            try:
                # Extract JSON from response (in case there's extra text)
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                    
                    selected_tool = result.get("selected_tool")
                    reasoning = result.get("reasoning", "")
                    suggested_params = result.get("suggested_parameters", {})
                    
                    if selected_tool and selected_tool in available_tools:
                        logger.info(f"LLM selected tool '{selected_tool}' for query: {query}")
                        logger.debug(f"Reasoning: {reasoning}")
                        logger.debug(f"Suggested parameters: {suggested_params}")
                        
                        # Validate and clean parameters based on tool schema
                        cleaned_params = self._validate_parameters(selected_tool, suggested_params)
                        
                        logger.info(f"ToolSelector selected tool: {selected_tool} with params: {cleaned_params}")
                        return selected_tool, cleaned_params
                    else:
                        logger.debug(f"LLM did not select a valid tool. Response: {result}")
                        return None
                        
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"LLM response: {response_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error during tool selection: {e}")
            return None
    
    def _validate_parameters(self, tool_name: str, suggested_params: Dict) -> Dict:
        """Validate and clean suggested parameters based on tool schema."""
        tool = tool_registry.get_tool(tool_name)
        if not tool:
            return suggested_params
        
        # Get the tool's parameter schema
        schema = tool.parameters
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        cleaned_params = {}
        
        # Validate each suggested parameter
        for param_name, param_value in suggested_params.items():
            if param_name in properties:
                param_spec = properties[param_name]
                param_type = param_spec.get("type", "string")
                
                # Type conversion and validation
                try:
                    if param_type == "integer":
                        cleaned_params[param_name] = int(param_value)
                    elif param_type == "number":
                        cleaned_params[param_name] = float(param_value)
                    elif param_type == "boolean":
                        if isinstance(param_value, str):
                            cleaned_params[param_name] = param_value.lower() in ["true", "yes", "1"]
                        else:
                            cleaned_params[param_name] = bool(param_value)
                    elif param_type == "array":
                        if isinstance(param_value, str):
                            # Try to parse as JSON array or split by comma
                            try:
                                cleaned_params[param_name] = json.loads(param_value)
                            except:
                                cleaned_params[param_name] = [item.strip() for item in param_value.split(",")]
                        else:
                            cleaned_params[param_name] = param_value
                    else:  # string or other types
                        cleaned_params[param_name] = str(param_value)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert parameter {param_name} to {param_type}: {e}")
                    # Keep original value if conversion fails
                    cleaned_params[param_name] = param_value
        
        # Add default values for required parameters that are missing
        for required_param in required:
            if required_param not in cleaned_params:
                param_spec = properties.get(required_param, {})
                default_value = param_spec.get("default")
                if default_value is not None:
                    cleaned_params[required_param] = default_value
                else:
                    # For critical parameters like 'query', don't set empty defaults
                    # Let the tool handle the validation and provide meaningful error messages
                    if required_param == "query":
                        logger.warning(f"Required parameter 'query' is missing for tool '{tool_name}'")
                        # Don't set a default - let the tool handle the validation
                        continue
                    
                    # Set reasonable defaults based on type for non-critical parameters
                    param_type = param_spec.get("type", "string")
                    if param_type == "integer":
                        cleaned_params[required_param] = 0
                    elif param_type == "boolean":
                        cleaned_params[required_param] = False
                    elif param_type == "array":
                        cleaned_params[required_param] = []
                    else:
                        cleaned_params[required_param] = ""
        
        return cleaned_params
