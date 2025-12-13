"""Custom tools API endpoints."""

import logging
import json
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.models import get_db, User, CustomTool
from backend.tools import tool_registry
from backend.tools import tool_registry
from backend.auth import get_current_user
from backend.agent.langchain_model import OllamaChatModel
from backend.agent.model_factory import create_model
from langchain_core.messages import HumanMessage, SystemMessage

router = APIRouter()
logger = logging.getLogger(__name__)


def _fix_common_syntax_issues(code: str) -> str:
    """Fix common syntax issues in generated code."""
    if not code:
        return code
    
    # Fix common typos and syntax errors
    # 1. Fix Tool,Result -> ToolResult (common typo)
    code = re.sub(r'\bTool\s*,\s*Result\b', 'ToolResult', code)
    
    # 2. Fix Tool Result -> ToolResult (spaces)
    code = re.sub(r'\bTool\s+Result\b', 'ToolResult', code)
    
    # 3. Fix common import issues
    code = re.sub(r'from\s+backend\.tools\.base\s+import\s+Tool\s*,\s*Result', 
                  'from backend.tools.base import ToolResult', code)
    
    # Count brackets/parentheses for basic validation
    open_parens = code.count('(')
    close_parens = code.count(')')
    open_brackets = code.count('[')
    close_brackets = code.count(']')
    open_braces = code.count('{')
    close_braces = code.count('}')
    
    # Log warnings for significant imbalances
    if abs(open_parens - close_parens) > 2:
        logger.warning(f"Potential parenthesis mismatch: {open_parens} open, {close_parens} close")
    if abs(open_brackets - close_brackets) > 2:
        logger.warning(f"Potential bracket mismatch: {open_brackets} open, {close_brackets} close")
    if abs(open_braces - close_braces) > 2:
        logger.warning(f"Potential brace mismatch: {open_braces} open, {close_braces} close")
    
    return code


class CustomToolCreate(BaseModel):
    """Custom tool creation request."""
    name: str = Field(..., min_length=1, max_length=100, pattern="^[a-zA-Z0-9_]+$")
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    permission_level: str = Field(default="safe")
    code: str = Field(..., min_length=1)
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)


class CustomToolUpdate(BaseModel):
    """Custom tool update request."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    permission_level: Optional[str] = None
    code: Optional[str] = Field(None, min_length=1)
    parameters_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class CustomToolResponse(BaseModel):
    """Custom tool response."""
    id: int
    name: str
    display_name: str
    description: str
    permission_level: str
    is_active: bool
    code: str
    parameters_schema: Dict[str, Any]
    created_by: int
    created_at: str
    updated_at: Optional[str]
    usage_count: int


class AIToolGenerationRequest(BaseModel):
    """AI-assisted tool generation request."""
    description: str = Field(..., min_length=1, max_length=2000, description="Natural language description of what the tool should do")
    name: Optional[str] = Field(None, description="Optional tool name (will be generated if not provided)")
    permission_level: str = Field(default="safe", description="Permission level for the tool")


@router.get("/", response_model=List[CustomToolResponse])
async def list_custom_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """List all custom tools created by the current user."""
    
    query = db.query(CustomTool).filter(CustomTool.created_by == current_user.id)
    
    if active_only:
        query = query.filter(CustomTool.is_active == True)
    
    tools = query.order_by(CustomTool.created_at.desc()).all()
    
    return [CustomToolResponse(**tool.to_dict()) for tool in tools]


@router.post("/", response_model=CustomToolResponse)
async def create_custom_tool(
    tool_data: CustomToolCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new custom tool."""
    
    # Check if tool name already exists
    existing_tool = db.query(CustomTool).filter(CustomTool.name == tool_data.name).first()
    if existing_tool:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool with name '{tool_data.name}' already exists"
        )
    
    # Validate permission level
    valid_permissions = ["safe", "read_files", "write_files", "network", "database_read", "database_write", "system"]
    if tool_data.permission_level not in valid_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level. Must be one of: {valid_permissions}"
        )
    
    # Validate code (basic syntax check)
    try:
        compile(tool_data.code, f"<custom_tool_{tool_data.name}>", "exec")
    except SyntaxError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Python code: {str(e)}"
        )
    
    # Create the custom tool
    custom_tool = CustomTool(
        name=tool_data.name,
        display_name=tool_data.display_name,
        description=tool_data.description,
        permission_level=tool_data.permission_level,
        code=tool_data.code,
        parameters_schema=tool_data.parameters_schema,
        created_by=current_user.id
    )
    
    db.add(custom_tool)
    db.commit()
    db.refresh(custom_tool)
    
    logger.info(f"User {current_user.username} created custom tool: {custom_tool.name}")
    # Immediately (re)register tool so it's available without restart
    try:
        tool_registry.register_custom_tool_config(custom_tool)
    except Exception as reg_err:
        logger.warning(f"Failed to register custom tool after create: {reg_err}")
    
    return CustomToolResponse(**custom_tool.to_dict())


@router.get("/{tool_id}", response_model=CustomToolResponse)
async def get_custom_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific custom tool."""
    
    tool = db.query(CustomTool).filter(
        CustomTool.id == tool_id,
        CustomTool.created_by == current_user.id
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom tool not found"
        )
    
    return CustomToolResponse(**tool.to_dict())


@router.put("/{tool_id}", response_model=CustomToolResponse)
async def update_custom_tool(
    tool_id: int,
    tool_data: CustomToolUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a custom tool."""
    
    tool = db.query(CustomTool).filter(
        CustomTool.id == tool_id,
        CustomTool.created_by == current_user.id
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom tool not found"
        )
    
    # Update fields
    update_data = tool_data.model_dump(exclude_unset=True)
    
    if "permission_level" in update_data:
        valid_permissions = ["safe", "read_files", "write_files", "network", "database_read", "database_write", "system"]
        if update_data["permission_level"] not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level. Must be one of: {valid_permissions}"
            )
    
    if "code" in update_data:
        try:
            compile(update_data["code"], f"<custom_tool_{tool.name}>", "exec")
        except SyntaxError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Python code: {str(e)}"
            )
    
    for field, value in update_data.items():
        setattr(tool, field, value)
    
    db.commit()
    db.refresh(tool)
    
    logger.info(f"User {current_user.username} updated custom tool: {tool.name}")
    # Immediately (re)register updated tool so changes take effect
    try:
        tool_registry.register_custom_tool_config(tool)
    except Exception as reg_err:
        logger.warning(f"Failed to register custom tool after update: {reg_err}")
    
    return CustomToolResponse(**tool.to_dict())


@router.delete("/{tool_id}")
async def delete_custom_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a custom tool."""
    
    tool = db.query(CustomTool).filter(
        CustomTool.id == tool_id,
        CustomTool.created_by == current_user.id
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom tool not found"
        )
    
    tool_name = tool.name

    # Unregister from in-memory registry so it no longer appears in available tools
    try:
        tool_registry.unregister(tool_name)
    except Exception:
        pass

    # Remove from current user's allowed_tools list if present
    try:
        allowed = current_user.allowed_tools or []
        if tool_name in allowed:
            allowed = [t for t in allowed if t != tool_name]
            current_user.allowed_tools = allowed
            flag_modified(current_user, "allowed_tools")
            db.commit()
            db.refresh(current_user)
    except Exception:
        pass

    # Delete from DB
    db.delete(tool)
    db.commit()

    logger.info(f"User {current_user.username} deleted custom tool: {tool_name}")

    return {"message": f"Custom tool '{tool_name}' deleted successfully", "success": True}


@router.post("/{tool_id}/toggle")
async def toggle_custom_tool(
    tool_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle a custom tool's active status."""
    
    tool = db.query(CustomTool).filter(
        CustomTool.id == tool_id,
        CustomTool.created_by == current_user.id
    ).first()
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom tool not found"
        )
    
    tool.is_active = not tool.is_active
    db.commit()
    db.refresh(tool)
    
    status_text = "activated" if tool.is_active else "deactivated"
    logger.info(f"User {current_user.username} {status_text} custom tool: {tool.name}")
    
    return {
        "message": f"Custom tool '{tool.name}' {status_text} successfully",
        "success": True,
        "is_active": tool.is_active
    }


@router.post("/generate", response_model=Dict[str, Any])
async def generate_tool_with_ai(
    request: AIToolGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a custom tool using AI based on natural language description."""
    
    try:
        # Refresh user object to ensure we have latest preferences from database
        db.refresh(current_user)
        
        # Get user's API configuration
        preferences = current_user.preferences or {}
        api_config = preferences.get("api_config", {})
        llm_provider = api_config.get("llm_provider", "ollama")
        
        # Get API keys from environment if not in user config
        from backend.config import settings as app_settings
        if not api_config.get("openai_api_key") and app_settings.OPENAI_API_KEY:
            api_config["openai_api_key"] = app_settings.OPENAI_API_KEY
        if not api_config.get("deepseek_api_key") and app_settings.DEEPSEEK_API_KEY:
            api_config["deepseek_api_key"] = app_settings.DEEPSEEK_API_KEY
        if not api_config.get("mistral_api_key") and app_settings.MISTRAL_API_KEY:
            api_config["mistral_api_key"] = app_settings.MISTRAL_API_KEY
        if not api_config.get("gemini_api_key") and app_settings.GEMINI_API_KEY:
            api_config["gemini_api_key"] = app_settings.GEMINI_API_KEY
        
        # For Ollama, use the model name from preferences
        # For other providers, use the model from api_config
        if llm_provider == "ollama":
            user_model = preferences.get("model", "qwen3:latest")
        else:
            # Use provider-specific model from api_config
            provider_model_key = f"{llm_provider}_model"
            user_model = api_config.get(provider_model_key) or preferences.get("model", "qwen3:latest")
        
        logger.info(f"Using {llm_provider} provider with model '{user_model}' for user {current_user.username} (preferences: {preferences})")
        
        # Create LLM instance using model factory (respects user's API configuration)
        try:
            llm = create_model(
                provider=llm_provider,
                model_name=user_model,
                temperature=0.3,  # Lower temperature for more deterministic code generation
                max_tokens=4000,  # Code generation may need more tokens
                api_config=api_config
            )
        except Exception as model_error:
            logger.warning(f"Failed to create {llm_provider} model: {model_error}. Falling back to Ollama.")
            # Fallback to Ollama if provider setup fails
            user_model = preferences.get("model", "qwen3:latest")
            llm = OllamaChatModel(model_name=user_model, temperature=0.3)
        
        # Create system prompt for tool generation
        system_prompt = """You are an expert Python developer specializing in creating custom AI tools following LangChain best practices.
Your task is to generate Python code for a tool based on a natural language description.

CRITICAL: You MUST respond with ONLY a valid JSON object. No explanations, no markdown, no code blocks, no reasoning tags, no additional text. Just the raw JSON.

CRITICAL JSON ESCAPING RULES:
- The "code" field contains Python code as a JSON string
- ALL quotes inside the code string MUST be escaped: use \" for double quotes, \' for single quotes
- ALL backslashes MUST be escaped: use \\ for a single backslash
- Newlines in strings MUST be escaped: use \\n (not actual newlines)
- Parentheses, brackets, and braces in string literals must be properly balanced
- Test your JSON before returning it - invalid JSON will cause errors

TOOL CREATION BEST PRACTICES (based on LangChain documentation):
1. The code MUST define an async function named `execute` that takes `**parameters` as arguments
2. The function MUST return a `ToolResult` object with the following structure:
   - success: bool
   - output: Any (the result data)
   - error: Optional[str] (error message if any)
   - metadata: Optional[Dict] (additional metadata)
3. Import ToolResult from: `from backend.tools.base import ToolResult`
4. Handle errors gracefully with try-except blocks
5. The code should be production-ready and well-commented

PARAMETER SCHEMA REQUIREMENTS (LangChain pattern):
- The parameters_schema MUST be a valid JSON Schema object
- Each parameter should have: type, description, and optionally default
- Use clear, descriptive parameter names
- Provide detailed descriptions for each parameter to help the LLM understand when and how to use them
- Required parameters should be listed in the "required" array
- Use appropriate types: "string", "integer", "number", "boolean", "array", "object"
- For enums, use "enum" in the schema with an array of allowed values

TOOL DESCRIPTION BEST PRACTICES:
- The suggested_description should be clear, concise, and informative
- It should explain what the tool does and when to use it
- Include examples of use cases if helpful
- Make it easy for the LLM to understand when this tool is appropriate

CODE QUALITY:
- Use proper type hints in comments/docstrings (even though execute uses **kwargs)
- Write clear, self-documenting code
- Include error handling for all external operations
- Use async/await properly for I/O operations
- Add helpful comments explaining complex logic

ALLOWED MODULES (CRITICAL - ONLY USE THESE):
- Standard library: math, random, re, json, time, datetime, uuid, base64, hashlib, typing, asyncio
- For network/API access (if permission_level is "network" or "web_access"): httpx, requests, urllib, urllib.parse, wikipedia
- For database access (if permission_level is "database_read" or "database_write"): sqlite3
- Internal: backend.tools.base

IMPORTANT: Only use modules from the allowed list. The 'wikipedia' library is allowed when permission_level is "network" or "web_access".

OUTPUT FORMAT - RETURN ONLY THIS JSON STRUCTURE (NO OTHER TEXT):
{
    "code": "the complete Python code as a string (escape newlines and quotes properly)",
    "parameters_schema": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string|number|boolean|array|object",
                "description": "Clear, detailed description that helps the LLM understand when and how to use this parameter. Include examples if helpful."
            }
        },
        "required": ["param_name1", "param_name2"]
    },
    "suggested_name": "suggested_tool_name (snake_case, descriptive)",
    "suggested_display_name": "Suggested Display Name (human-readable)",
    "suggested_description": "Clear, informative description following LangChain best practices. Should explain: what the tool does, when to use it, what it returns, and any important context. This description is critical for the LLM to understand when to select this tool."
}

REMEMBER: Return ONLY the JSON object. Start with { and end with }. No markdown, no code blocks, no explanations."""

        # Determine allowed modules based on permission level
        allowed_modules_note = "Allowed modules: math, random, re, json, time, datetime, uuid, base64, hashlib, typing, asyncio"
        if request.permission_level in ["network", "web_access"]:
            allowed_modules_note += ", httpx, requests, urllib, urllib.parse, wikipedia"
        if request.permission_level in ["database_read", "database_write"]:
            allowed_modules_note += ", sqlite3"
        
        user_prompt = f"""Generate a custom AI tool based on this description:

{request.description}

Permission level: {request.permission_level}
{allowed_modules_note}

FOLLOW LANGCHAIN TOOL PATTERNS:
1. Create an async execute function with clear parameter handling
2. Define a comprehensive parameters_schema with:
   - Clear type definitions for each parameter
   - Detailed descriptions for each parameter (this helps the LLM understand when to use the tool)
   - Proper required/optional field specification
   - Default values where appropriate
3. Write a clear, informative tool description that explains:
   - What the tool does
   - When to use it
   - What it returns
4. Use proper error handling and return ToolResult with success/error information
5. Make the code production-ready with good comments

EXAMPLE STRUCTURE:
```python
async def execute(self, query: str, max_results: int = 10, **parameters):
    \"\"\"
    Execute the tool with proper error handling.
    
    Args:
        query: Clear description of what this parameter does
        max_results: Clear description with default value
    \"\"\"
    from backend.tools.base import ToolResult
    
    try:
        # Implementation here
        result = perform_operation(query, max_results)
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
```

Return only the JSON object with code, parameters_schema, suggested_name, suggested_display_name, and suggested_description."""

        # Generate code using LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Use ainvoke (standard LangChain method)
        try:
            response = await llm.ainvoke(messages)
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                # Try to get content from message object
                response_text = str(response)
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate code with AI: {str(e)}"
            )
        
        # Strip reasoning tags if present
        def strip_reasoning_tags(content: str) -> str:
            """Remove reasoning tags from content."""
            if not content:
                return content
            # Remove <think>...</think> tags
            content = re.sub(r'<(?:think|redacted_reasoning)>.*?</(?:think|redacted_reasoning)>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Handle unclosed tags
            content = re.sub(r'<(?:think|redacted_reasoning)>.*?$', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'^.*?</(?:think|redacted_reasoning)>', '', content, flags=re.DOTALL | re.IGNORECASE)
            # Clean up extra whitespace
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            return content.strip()
        
        response_text = strip_reasoning_tags(response_text)
        
        # Extract JSON from response (handle various formats)
        result = None
        
        # Strategy 1: Try to find JSON in markdown code blocks first
        json_code_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text, re.IGNORECASE | re.DOTALL)
        if json_code_block:
            try:
                result = json.loads(json_code_block.group(1))
            except json.JSONDecodeError:
                pass
        
        # Strategy 2: If not found, try to find JSON object directly with balanced braces
        if result is None:
            start_idx = response_text.find('{')
            if start_idx != -1:
                # Find matching closing brace
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                
                if brace_count == 0:
                    json_candidate = response_text[start_idx:end_idx + 1]
                    try:
                        result = json.loads(json_candidate)
                    except json.JSONDecodeError:
                        # Try cleaning up common issues
                        # Remove trailing commas before closing braces/brackets
                        json_candidate = re.sub(r',\s*([}\]])', r'\1', json_candidate)
                        try:
                            result = json.loads(json_candidate)
                        except json.JSONDecodeError:
                            pass
        
        # Strategy 3: Try to find any JSON-like structure (more lenient)
        if result is None:
            # Look for patterns like {"code": "...", ...}
            json_pattern = re.search(r'\{[^{}]*"code"[^{}]*\{[^{}]*\}[^{}]*\}', response_text, re.DOTALL)
            if json_pattern:
                try:
                    # Try to extract a larger JSON structure around this pattern
                    start = max(0, json_pattern.start() - 100)
                    end = min(len(response_text), json_pattern.end() + 100)
                    candidate = response_text[start:end]
                    # Find the first { and try to match braces
                    start_idx = candidate.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        end_idx = start_idx
                        for i in range(start_idx, len(candidate)):
                            if candidate[i] == '{':
                                brace_count += 1
                            elif candidate[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i
                                    break
                        if brace_count == 0:
                            try:
                                result = json.loads(candidate[start_idx:end_idx + 1])
                            except json.JSONDecodeError:
                                pass
                except Exception:
                    pass
        
        # Strategy 4: Try to extract incomplete JSON and fix it
        if result is None:
            # Look for {"code": pattern and try to extract even if incomplete
            code_match = re.search(r'"code"\s*:\s*"((?:[^"\\]|\\.|\\n)*)"', response_text, re.DOTALL)
            if code_match:
                try:
                    # Extract and unescape the code string
                    code_value = code_match.group(1)
                    # Unescape common escape sequences
                    code_value = code_value.replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
                    
                    # Try to find parameters_schema
                    params_match = re.search(r'"parameters_schema"\s*:\s*(\{[^}]*\})', response_text, re.DOTALL)
                    params_schema = {"type": "object", "properties": {}, "required": []}
                    if params_match:
                        try:
                            params_schema = json.loads(params_match.group(1))
                        except:
                            pass
                    
                    # Try to find suggested names
                    name_match = re.search(r'"suggested_name"\s*:\s*"([^"]*)"', response_text)
                    suggested_name = name_match.group(1) if name_match else "generated_tool"
                    
                    display_name_match = re.search(r'"suggested_display_name"\s*:\s*"([^"]*)"', response_text)
                    suggested_display_name = display_name_match.group(1) if display_name_match else "Generated Tool"
                    
                    desc_match = re.search(r'"suggested_description"\s*:\s*"([^"]*)"', response_text)
                    suggested_description = desc_match.group(1) if desc_match else ""
                    
                    # Build result object
                    result = {
                        "code": code_value,
                        "parameters_schema": params_schema,
                        "suggested_name": suggested_name,
                        "suggested_display_name": suggested_display_name,
                        "suggested_description": suggested_description
                    }
                    logger.info("Extracted incomplete JSON using pattern matching")
                except Exception as e:
                    logger.warning(f"Failed to extract from incomplete JSON: {e}")
                    pass
        
        if result is None:
            logger.error(f"Failed to parse LLM response as JSON")
            logger.error(f"Response was: {response_text[:2000]}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI generated invalid response format. Please try again or use manual mode."
            )
        
        # Validate and extract fields
        code = result.get("code", "")
        if not code:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI did not generate code. Please try again or use manual mode."
            )
        
        # Validate and fix code syntax
        code = _fix_common_syntax_issues(code)
        
        try:
            compile(code, "<generated_tool>", "exec")
        except SyntaxError as e:
            logger.error(f"Generated code has syntax errors: {e}")
            # Log more context about the error
            error_line = getattr(e, 'lineno', None)
            error_text = getattr(e, 'text', None)
            if error_line:
                logger.error(f"Error at line {error_line}: {error_text}")
            logger.error(f"Problematic code (first 1000 chars):\n{code[:1000]}")
            
            # Try to provide more helpful error message
            error_msg = str(e)
            if "unmatched" in error_msg.lower():
                error_msg += " This is often caused by unescaped quotes or parentheses in string literals. The AI may need to regenerate the code with proper escaping."
            elif "unexpected" in error_msg.lower():
                error_msg += " This might be due to invalid syntax or unescaped characters in the generated code."
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generated code has syntax errors: {error_msg}. Please try again or use manual mode."
            )
        
        # Extract parameters schema
        parameters_schema = result.get("parameters_schema", {
            "type": "object",
            "properties": {},
            "required": []
        })
        
        # Extract suggested names
        suggested_name = result.get("suggested_name", request.name or "generated_tool")
        suggested_display_name = result.get("suggested_display_name", "Generated Tool")
        suggested_description = result.get("suggested_description", request.description)
        
        # Clean up suggested name (only alphanumeric and underscores)
        suggested_name = re.sub(r'[^a-zA-Z0-9_]', '_', suggested_name)
        if not suggested_name or suggested_name[0].isdigit():
            suggested_name = "generated_tool"
        
        return {
            "code": code,
            "parameters_schema": parameters_schema,
            "suggested_name": suggested_name,
            "suggested_display_name": suggested_display_name,
            "suggested_description": suggested_description,
            "permission_level": request.permission_level
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tool with AI: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tool: {str(e)}. Please try again or use manual mode."
        )
