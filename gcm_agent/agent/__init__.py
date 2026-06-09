"""Agent package for LangGraph-based orchestration of GCM MCP tools and LLM interactions."""

# Made with Bob
# 2026-06-09 19:23 UTC - Updated create_gcm_agent to use LLMProviderConfig
# 2026-06-05 22:12 UTC - Initial implementation of agent package with helper function

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


async def create_gcm_agent(
    gcm_config,
    auth_config,
    llm_config,
    agent_config,
    password: str,
    client_secret: str,
):
    """
    Create and initialize GCM Agent with all dependencies.
    
    This is the main entry point for creating a fully initialized GCM Agent.
    It handles all the setup steps including MCP client connection, tool loading,
    and agent initialization.
    
    Args:
        gcm_config: GCM server configuration (GCMServerConfig)
        auth_config: Authentication configuration (AuthConfig)
        llm_config: Unified LLM provider configuration (LLMProviderConfig)
        agent_config: Agent configuration (AgentConfig)
        password: GCM user password
        client_secret: OAuth2 client secret
    
    Returns:
        Initialized GCM Agent ready for use
        
    Raises:
        MCPConnectionError: If MCP connection fails
        AgentInitializationError: If agent initialization fails
    
    Example:
        >>> from gcm_agent.config import get_config_manager
        >>> from gcm_agent.config.config_manager import LLMProviderConfig
        >>> from gcm_agent.agent import create_gcm_agent
        >>>
        >>> config_mgr = get_config_manager()
        >>> gcm_config = config_mgr.get_gcm_config()
        >>> auth_config = config_mgr.get_auth_config()
        >>> agent_config = config_mgr.get_agent_config()
        >>> password = config_mgr.get_password()
        >>> client_secret = config_mgr.get_client_secret()
        >>>
        >>> # Create LLM config for WatsonX
        >>> llm_config = LLMProviderConfig(
        ...     provider="watsonx",
        ...     watsonx_config=config_mgr.get_watsonx_config(),
        ...     watsonx_api_key=config_mgr.get_watsonx_api_key()
        ... )
        >>>
        >>> agent = await create_gcm_agent(
        ...     gcm_config, auth_config, llm_config, agent_config,
        ...     password, client_secret
        ... )
        >>>
        >>> # Use the agent
        >>> response = await agent.chat("List all cryptographic keys")
        >>> print(response)
        >>>
        >>> # Clean up
        >>> await agent.close()
    """
    from gcm_agent.mcp import create_gcm_mcp_client
    from gcm_agent.utils.logger import get_agent_logger
    
    logger = get_agent_logger()
    logger.info("Creating GCM Agent")
    
    try:
        # Step 1: Create MCP client and tool loader
        logger.debug("Step 1: Creating MCP client and tool loader")
        mcp_client, tool_loader = await create_gcm_mcp_client(
            gcm_config, auth_config, agent_config, password, client_secret
        )
        
        # Step 2: Create agent instance with unified LLM config
        logger.debug("Step 2: Creating agent instance")
        agent = GCMAgent(
            mcp_client=mcp_client,
            tool_loader=tool_loader,
            agent_config=agent_config,
            llm_config=llm_config,
        )
        
        # Step 3: Initialize agent (load tools, create graph)
        logger.debug("Step 3: Initializing agent")
        await agent.initialize()
        
        logger.info("GCM Agent created and initialized successfully")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create GCM Agent: {e}")
        raise


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
