"""Tools API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from backend.models import get_db, User
from backend.auth import get_current_user
from backend.tools import tool_registry, ToolPermission

router = APIRouter()


class ToolInfo(BaseModel):
    """Tool information."""
    name: str
    description: str
    permission: str
    parameters: dict


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    tool_name: str
    parameters: dict
    require_approval: bool = True


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: dict = {}


@router.get("/", response_model=List[ToolInfo])
async def list_tools(
    current_user: User = Depends(get_current_user)
):
    """List all available tools for the user."""
    
    # Get user's allowed tools
    allowed_tools = current_user.allowed_tools or []
    
    # Get tool schemas
    tools = []
    for tool_name in allowed_tools:
        tool = tool_registry.get_tool(tool_name)
        if tool:
            tools.append(ToolInfo(
                name=tool.name,
                description=tool.description,
                permission=tool.permission.value,
                parameters=tool.parameters
            ))
    
    return tools


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool(
    tool_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific tool."""
    
    # Check if user has access
    if tool_name not in (current_user.allowed_tools or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this tool is not allowed"
        )
    
    tool = tool_registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    return ToolInfo(
        name=tool.name,
        description=tool.description,
        permission=tool.permission.value,
        parameters=tool.parameters
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute a tool directly (for testing/debugging)."""
    
    # Check if user has access
    if request.tool_name not in (current_user.allowed_tools or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this tool is not allowed"
        )
    
    # Get tool
    tool = tool_registry.get_tool(request.tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found"
        )
    
    # Check if tool needs approval
    if request.require_approval and tool.permission != ToolPermission.SAFE:
        # In a real app, this would trigger an approval flow
        # For now, we'll just note it in the response
        return ToolExecuteResponse(
            success=False,
            output=None,
            error="Tool requires approval",
            metadata={"permission_required": tool.permission.value}
        )
    
    # Execute tool
    result = await tool_registry.execute_tool(
        tool_name=request.tool_name,
        parameters=request.parameters,
        check_permission=False  # Already checked above
    )
    
    return ToolExecuteResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        metadata=result.metadata
    )


@router.get("/permissions/list")
async def list_permissions():
    """List all available permission levels."""
    
    return [
        {
            "name": perm.value,
            "description": get_permission_description(perm)
        }
        for perm in ToolPermission
    ]


def get_permission_description(permission: ToolPermission) -> str:
    """Get description for a permission level."""
    
    descriptions = {
        ToolPermission.SAFE: "No special permissions required",
        ToolPermission.READ_FILES: "Can read local files",
        ToolPermission.WRITE_FILES: "Can write local files",
        ToolPermission.NETWORK: "Can access the network",
        ToolPermission.DATABASE_READ: "Can read from databases",
        ToolPermission.DATABASE_WRITE: "Can write to databases",
        ToolPermission.SYSTEM: "Can execute system commands"
    }
    
    return descriptions.get(permission, "Unknown permission")


@router.post("/grant-permission")
async def grant_permission(
    tool_name: str,
    grant: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Grant or revoke permission for a tool."""
    
    # Get current allowed tools
    allowed_tools = current_user.allowed_tools or []
    
    if grant and tool_name not in allowed_tools:
        # Add tool
        allowed_tools.append(tool_name)
        current_user.allowed_tools = allowed_tools
        db.commit()
        
        return {"message": f"Granted access to {tool_name}"}
    
    elif not grant and tool_name in allowed_tools:
        # Remove tool
        allowed_tools.remove(tool_name)
        current_user.allowed_tools = allowed_tools
        db.commit()
        
        return {"message": f"Revoked access to {tool_name}"}
    
    return {"message": "No change needed"}
