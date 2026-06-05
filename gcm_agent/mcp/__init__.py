"""MCP client and tool loader for GCM Agent."""

# Made with Bob
# 2026-06-05 22:00 UTC - Initial implementation of MCP exceptions and helper functions

from typing import Tuple

from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader


# Custom exceptions for MCP operations
class MCPError(Exception):
    """Base exception for MCP operations."""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""
    pass


class MCPToolError(MCPError):
    """Raised when tool execution fails."""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operation times out."""
    pass


class ToolNotFoundError(MCPError):
    """Raised when requested tool is not found."""
    pass


async def create_gcm_mcp_client(
    gcm_config,
    auth_config,
    agent_config,
    password: str,
    client_secret: str,
) -> Tuple[GCMMCPClient, GCMToolLoader]:
    """
    Create and connect GCM MCP client with tool loader.
    
    This is the main entry point for creating an authenticated MCP client
    that can interact with the GCM MCP server. It handles the complete
    authentication flow and returns a ready-to-use client and tool loader.
    
    Args:
        gcm_config: GCM server configuration (GCMServerConfig)
        auth_config: Authentication configuration (AuthConfig)
        agent_config: Agent configuration (AgentConfig)
        password: GCM user password
        client_secret: OAuth2 client secret
    
    Returns:
        Tuple of (mcp_client, tool_loader)
    
    Raises:
        MCPConnectionError: If connection to MCP server fails
        KeycloakAuthError: If Keycloak authentication fails
        GCMAuthError: If GCM authorization fails
    
    Example:
        >>> from gcm_agent.config import get_config_manager
        >>> config_mgr = get_config_manager()
        >>> gcm_config = config_mgr.get_gcm_config()
        >>> auth_config = config_mgr.get_auth_config()
        >>> agent_config = config_mgr.get_agent_config()
        >>> password = config_mgr.get_password()
        >>> client_secret = config_mgr.get_client_secret()
        >>>
        >>> mcp_client, tool_loader = await create_gcm_mcp_client(
        ...     gcm_config, auth_config, agent_config, password, client_secret
        ... )
        >>> tools = await tool_loader.load_tools()
    """
    from gcm_agent.auth import get_client_factory
    from gcm_agent.utils.logger import get_mcp_logger
    
    logger = get_mcp_logger()
    logger.info("Creating GCM MCP client")
    
    try:
        # Step 1 & 2: Authenticate and get client factory
        # get_client_factory handles the complete two-step auth flow internally
        logger.debug("Step 1-2: Authenticating and creating client factory")
        client_factory = await get_client_factory(
            gcm_config, auth_config, password, client_secret, timeout=agent_config.timeout
        )
        
        # Step 3: Create MCP client
        logger.debug("Step 3: Creating MCP client")
        mcp_client = GCMMCPClient(
            gcm_url=gcm_config.url,
            client_factory=client_factory,
            discovery_mode=agent_config.discovery_mode,
            timeout=agent_config.timeout,
        )
        
        # Step 4: Connect to MCP server
        logger.debug("Step 4: Connecting to MCP server")
        await mcp_client.connect()
        
        # Step 5: Create tool loader
        logger.debug("Step 5: Creating tool loader")
        tool_loader = GCMToolLoader(mcp_client)
        
        logger.info("Successfully created GCM MCP client and tool loader")
        return mcp_client, tool_loader
        
    except Exception as e:
        logger.error(f"Failed to create GCM MCP client: {e}")
        raise MCPConnectionError(f"Failed to create GCM MCP client: {e}") from e


__all__ = [
    "GCMMCPClient",
    "GCMToolLoader",
    "MCPError",
    "MCPConnectionError",
    "MCPToolError",
    "MCPTimeoutError",
    "ToolNotFoundError",
    "create_gcm_mcp_client",
]
