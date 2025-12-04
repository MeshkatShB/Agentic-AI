"""Custom tools API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.models import get_db, User, CustomTool
from backend.tools import tool_registry
from backend.tools import tool_registry
from backend.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


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
    parameters_schema: Dict[str, Any]
    created_by: int
    created_at: str
    updated_at: Optional[str]
    usage_count: int


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
