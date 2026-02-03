"""MCP service for managing MCP clients and tools."""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("langchain-mcp-adapters not installed. MCP features will be disabled.")

from backend.models import MCPServer

logger = logging.getLogger(__name__)


class MCPService:
    """Service for managing MCP clients and loading tools."""
    
    def __init__(self):
        """Initialize MCP service."""
        if not MCP_AVAILABLE:
            logger.warning("MCP adapters not available. Install langchain-mcp-adapters to enable MCP features.")
        self._clients: Dict[int, MultiServerMCPClient] = {}  # user_id -> client
    
    def get_mcp_config_for_user(self, db: Session, user_id: int) -> Dict[str, Dict]:
        """Get MCP server configurations for a user."""
        servers = db.query(MCPServer).filter(
            MCPServer.created_by == user_id,
            MCPServer.is_active == True,
            MCPServer.is_enabled == True
        ).all()
        
        config = {}
        for server in servers:
            config[server.name] = server.to_mcp_config()
        
        return config
    
    async def get_client_for_user(self, db: Session, user_id: int) -> Optional[MultiServerMCPClient]:
        """Get or create MCP client for a user."""
        if not MCP_AVAILABLE:
            return None
        
        # Return cached client if available
        if user_id in self._clients:
            return self._clients[user_id]
        
        # Get server configurations
        config = self.get_mcp_config_for_user(db, user_id)
        
        if not config:
            logger.info(f"No MCP servers configured for user {user_id}")
            return None
        
        try:
            # Create client
            client = MultiServerMCPClient(config)
            self._clients[user_id] = client
            logger.info(f"Created MCP client for user {user_id} with {len(config)} servers")
            return client
        except Exception as e:
            logger.error(f"Failed to create MCP client for user {user_id}: {e}", exc_info=True)
            return None
    
    async def get_tools_for_user(self, db: Session, user_id: int) -> List[Any]:
        """Get MCP tools for a user."""
        if not MCP_AVAILABLE:
            return []
        
        client = await self.get_client_for_user(db, user_id)
        if not client:
            return []
        
        try:
            tools = await client.get_tools()
            logger.info(f"Loaded {len(tools)} MCP tools for user {user_id}")
            return tools
        except Exception as e:
            logger.error(f"Failed to load MCP tools for user {user_id}: {e}", exc_info=True)
            return []
    
    async def test_server_connection(self, server: MCPServer) -> tuple[bool, Optional[str], Optional[List[dict]], Optional[int]]:
        """Test connection to an MCP server.
        
        Returns:
            Tuple of (success, message, tools_list, tool_count)
        """
        if not MCP_AVAILABLE:
            return False, "MCP adapters not installed", None, None
        
        try:
            config = {server.name: server.to_mcp_config()}
            client = MultiServerMCPClient(config)
            
            # Try to get tools as a connection test
            tools = await client.get_tools()
            
            # Extract tool information
            tools_info = []
            for tool in tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description or "",
                }
                # Try to get args schema if available
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    try:
                        tool_info["parameters"] = tool.args_schema.model_json_schema() if hasattr(tool.args_schema, 'model_json_schema') else {}
                    except:
                        tool_info["parameters"] = {}
                else:
                    tool_info["parameters"] = {}
                
                tools_info.append(tool_info)
            
            message = f"Connected successfully. Found {len(tools)} tool(s)."
            return True, message, tools_info, len(tools)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to MCP server {server.name}: {e}", exc_info=True)
            return False, error_msg, None, None
    
    def clear_user_client(self, user_id: int):
        """Clear cached client for a user (e.g., when servers are updated)."""
        if user_id in self._clients:
            del self._clients[user_id]
            logger.info(f"Cleared MCP client cache for user {user_id}")
    
    def clear_all_clients(self):
        """Clear all cached clients."""
        self._clients.clear()
        logger.info("Cleared all MCP client caches")


# Global service instance
mcp_service = MCPService()

