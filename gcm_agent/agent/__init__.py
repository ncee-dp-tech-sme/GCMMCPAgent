"""Agent package for LangGraph-based orchestration of GCM MCP tools and LLM interactions."""

# Made with Bob
# 2026-07-17 00:36 UTC - Pass gcm_api_key from AgentSetupConfig to create_gcm_mcp_client()
# 2026-06-09 19:50 UTC - Major refactoring: consolidated parameters into AgentSetupConfig, inlined context manager, enhanced logging, fixed exception handling
# 2026-06-09 19:42 UTC - Refactored create_gcm_agent: extracted cleanup, consolidated exceptions, improved logging, added context manager
# 2026-06-09 19:35 UTC - Comprehensive refactoring: added type hints, validation, better error handling, cleanup on failure
# 2026-06-09 19:23 UTC - Updated create_gcm_agent to use LLMProviderConfig
# 2026-06-05 22:12 UTC - Initial implementation of agent package with helper function

from typing import Optional

from gcm_agent.agent.gcm_agent import (
    GCMAgent,
    AgentError,
    AgentInitializationError,
    AgentExecutionError,
    ToolExecutionError,
)
from gcm_agent.agent.prompts import (
    GCM_SYSTEM_PROMPT,
    DISCOVERY_MODE_PROMPT,
    STANDARD_MODE_PROMPT,
    get_system_prompt,
)
from gcm_agent.config.config_manager import (
    KeycloakConfig,
    GCMServerConfig,
    AuthConfig,
    LLMProviderConfig,
    AgentConfig,
    AgentSetupConfig,
)
from gcm_agent.mcp import create_gcm_mcp_client, MCPConnectionError
from gcm_agent.utils.logger import get_agent_logger


async def _cleanup_mcp_client(mcp_client: Optional['GCMMCPClient'], logger) -> None:
    """
    Cleanup MCP client resources.
    
    Args:
        mcp_client: MCP client to cleanup (may be None)
        logger: Logger instance for warning messages
    """
    if mcp_client:
        try:
            await mcp_client.close()
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup MCP client: {cleanup_error}")


async def create_gcm_agent(config: AgentSetupConfig, debug_ui: Optional['DebugUI'] = None) -> GCMAgent:
    """
    Create and initialize GCM Agent with all dependencies.
    
    This is the main entry point for creating a fully initialized GCM Agent.
    It handles all setup steps including MCP client connection, tool loading,
    and agent initialization with automatic resource cleanup on failure.
    
    Args:
        config: Consolidated agent setup configuration (AgentSetupConfig)
        debug_ui: Optional debug UI instance for real-time observability logs
    
    Returns:
        Initialized GCM Agent ready for use
        
    Raises:
        MCPConnectionError: If MCP connection fails
        AgentInitializationError: If agent initialization fails
    
    Example:
        >>> from gcm_agent.config import get_config_manager
        >>> from gcm_agent.config.config_manager import AgentSetupConfig, LLMProviderConfig
        >>> from gcm_agent.agent import create_gcm_agent
        >>>
        >>> config_mgr = get_config_manager()
        >>>
        >>> # Create LLM config for WatsonX
        >>> llm_config = LLMProviderConfig(
        ...     provider="watsonx",
        ...     watsonx_config=config_mgr.get_watsonx_config(),
        ...     watsonx_api_key=config_mgr.get_watsonx_api_key()
        ... )
        >>>
        >>> # Create consolidated setup config
        >>> setup_config = AgentSetupConfig(
        ...     keycloak_config=config_mgr.get_keycloak_config(),
        ...     gcm_config=config_mgr.get_gcm_config(),
        ...     auth_config=config_mgr.get_auth_config(),
        ...     llm_config=llm_config,
        ...     agent_config=config_mgr.get_agent_config(),
        ...     password=config_mgr.get_password(),
        ...     client_secret=config_mgr.get_client_secret()
        ... )
        >>>
        >>> agent = await create_gcm_agent(setup_config)
        >>>
        >>> # Use the agent
        >>> response = await agent.chat("List all cryptographic keys")
        >>> print(response)
        >>>
        >>> # Clean up
        >>> await agent.close()
    """
    logger = get_agent_logger()
    
    # Log comprehensive diagnostic information
    logger.info(
        "Creating GCM Agent",
        extra={
            "gcm_url": config.gcm_config.url,
            "gcm_hostname": config.gcm_config.hostname,
            "keycloak_url": config.keycloak_config.url,
            "keycloak_realm": config.keycloak_config.realm,
            "discovery_mode": config.agent_config.discovery_mode,
            "llm_provider": config.llm_config.provider,
            "max_iterations": config.agent_config.max_iterations,
            "username": config.auth_config.username,
        }
    )
    
    mcp_client = None
    try:
        # Create MCP client and tool loader
        logger.debug("Creating MCP client and tool loader")
        mcp_client, tool_loader = await create_gcm_mcp_client(
            config.keycloak_config,
            config.gcm_config,
            config.auth_config,
            config.agent_config,
            config.password,
            config.client_secret,
            gcm_api_key=config.gcm_api_key,
        )
        
        # Create agent instance with unified LLM config
        logger.debug("Instantiating GCM agent")
        agent = GCMAgent(
            mcp_client=mcp_client,
            tool_loader=tool_loader,
            agent_config=config.agent_config,
            llm_config=config.llm_config,
            debug_ui=debug_ui,
        )
        
        # Initialize agent (load tools, create graph)
        logger.debug("Initializing agent (loading tools, building graph)")
        await agent.initialize()
        
        logger.info("GCM Agent created and initialized successfully")
        return agent
        
    except (MCPConnectionError, AgentInitializationError) as e:
        # Cleanup and re-raise known exceptions
        await _cleanup_mcp_client(mcp_client, logger)
        logger.error(f"Failed to create GCM Agent: {e}")
        raise
    except Exception as e:
        # Cleanup and convert unexpected exceptions
        await _cleanup_mcp_client(mcp_client, logger)
        logger.error(f"Unexpected error creating GCM Agent: {e}")
        raise AgentInitializationError(f"Unexpected error: {e}") from e


__all__ = [
    # Main agent class
    "GCMAgent",
    # Helper function
    "create_gcm_agent",
    # Exceptions
    "AgentError",
    "AgentInitializationError",
    "AgentExecutionError",
    "ToolExecutionError",
    # Prompts
    "GCM_SYSTEM_PROMPT",
    "DISCOVERY_MODE_PROMPT",
    "STANDARD_MODE_PROMPT",
    "get_system_prompt",
]
