"""MCP server API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

from backend.models import get_db, User, MCPServer
from backend.auth import get_current_user
from backend.services.mcp_service import mcp_service

router = APIRouter()
logger = logging.getLogger(__name__)


class MCPServerCreate(BaseModel):
    """Request model for creating an MCP server."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    transport: str = Field(..., pattern="^(http|stdio)$")
    
    # HTTP transport fields
    url: Optional[str] = None
    
    # stdio transport fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    
    # Optional fields
    headers: Optional[dict] = None
    auth_config: Optional[dict] = None
    
    @model_validator(mode='after')
    def validate_transport_fields(self):
        """Validate transport-specific fields."""
        if self.transport == "http" and not self.url:
            raise ValueError("URL is required for HTTP transport")
        if self.transport == "stdio" and not self.command:
            raise ValueError("Command is required for stdio transport")
        return self


class MCPServerUpdate(BaseModel):
    """Request model for updating an MCP server."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    transport: Optional[str] = Field(None, pattern="^(http|stdio)$")
    
    # HTTP transport fields
    url: Optional[str] = None
    
    # stdio transport fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    
    # Optional fields
    headers: Optional[dict] = None
    auth_config: Optional[dict] = None
    is_enabled: Optional[bool] = None


class MCPServerResponse(BaseModel):
    """Response model for MCP server."""
    id: int
    name: str
    description: Optional[str]
    transport: str
    url: Optional[str]
    command: Optional[str]
    args: Optional[List[str]]
    headers: Optional[dict]
    auth_config: Optional[dict]
    is_active: bool
    is_enabled: bool
    created_by: int
    created_at: Optional[str]
    updated_at: Optional[str]
    last_connected_at: Optional[str]
    last_error: Optional[str]
    last_tool_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class MCPServerTestResponse(BaseModel):
    """Response model for MCP server connection test."""
    success: bool
    message: str
    tool_count: Optional[int] = None
    tools: Optional[List[dict]] = None  # List of available tools with their details


@router.get("/", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all MCP servers for the current user."""
    servers = db.query(MCPServer).filter(
        MCPServer.created_by == current_user.id
    ).all()
    
    return [MCPServerResponse(**server.to_dict()) for server in servers]


@router.post("/", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_data: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new MCP server configuration."""
    
    # Check if name already exists for this user
    existing = db.query(MCPServer).filter(
        MCPServer.name == server_data.name,
        MCPServer.created_by == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MCP server with name '{server_data.name}' already exists"
        )
    
    # Create server
    server = MCPServer(
        name=server_data.name,
        description=server_data.description,
        transport=server_data.transport,
        url=server_data.url,
        command=server_data.command,
        args=server_data.args or [],
        headers=server_data.headers or {},
        auth_config=server_data.auth_config or {},
        created_by=current_user.id
    )
    
    db.add(server)
    db.commit()
    db.refresh(server)
    
    # Clear cached client for this user
    mcp_service.clear_user_client(current_user.id)
    
    logger.info(f"Created MCP server '{server.name}' for user {current_user.id}")
    
    return MCPServerResponse(**server.to_dict())


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific MCP server."""
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.created_by == current_user.id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found"
        )
    
    return MCPServerResponse(**server.to_dict())


@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: int,
    server_data: MCPServerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an MCP server configuration."""
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.created_by == current_user.id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found"
        )
    
    # Update fields
    update_data = server_data.dict(exclude_unset=True)
    
    # Check name uniqueness if changing name
    if "name" in update_data and update_data["name"] != server.name:
        existing = db.query(MCPServer).filter(
            MCPServer.name == update_data["name"],
            MCPServer.created_by == current_user.id,
            MCPServer.id != server_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MCP server with name '{update_data['name']}' already exists"
            )
    
    for key, value in update_data.items():
        setattr(server, key, value)
    
    db.commit()
    db.refresh(server)
    
    # Clear cached client for this user
    mcp_service.clear_user_client(current_user.id)
    
    logger.info(f"Updated MCP server '{server.name}' for user {current_user.id}")
    
    return MCPServerResponse(**server.to_dict())


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an MCP server."""
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.created_by == current_user.id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found"
        )
    
    db.delete(server)
    db.commit()
    
    # Clear cached client for this user
    mcp_service.clear_user_client(current_user.id)
    
    logger.info(f"Deleted MCP server '{server.name}' for user {current_user.id}")


@router.post("/{server_id}/test", response_model=MCPServerTestResponse)
async def test_mcp_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test connection to an MCP server."""
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.created_by == current_user.id
    ).first()
    
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found"
        )
    
    # Test connection
    success, message, tools_list, tool_count = await mcp_service.test_server_connection(server)
    
    # Update server status
    if success:
        from datetime import datetime
        server.last_connected_at = datetime.utcnow()
        server.last_error = None
        server.last_tool_count = tool_count  # Store tool count
    else:
        server.last_error = message
        server.last_tool_count = None  # Clear tool count on error
    
    db.commit()
    
    return MCPServerTestResponse(
        success=success,
        message=message,
        tool_count=tool_count,
        tools=tools_list
    )


@router.get("/tools/list")
async def list_mcp_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available tools from MCP servers."""
    tools = await mcp_service.get_tools_for_user(db, current_user.id)
    
    # Convert tools to serializable format
    tool_list = []
    for tool in tools:
        tool_list.append({
            "name": tool.name,
            "description": tool.description or "",
            "args_schema": tool.args_schema.model_json_schema() if hasattr(tool, "args_schema") else {}
        })
    
    return {
        "tools": tool_list,
        "count": len(tool_list)
    }

