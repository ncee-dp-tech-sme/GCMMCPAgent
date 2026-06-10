"""Orchestrate adapter for GCM Agent.

This module provides the abstraction layer between WatsonX Orchestrate
and the GCM Agent, following the portability design principles.

Made with Bob
2026-06-10 02:47 UTC - Initial implementation of orchestrate adapter
2026-06-10 03:01 UTC - Added create_graph function for WatsonX Orchestrate entrypoint
"""

from typing import Dict, Any, Optional, AsyncGenerator
import time
import uuid
from datetime import datetime

from gcm_agent.agent import create_gcm_agent, GCMAgent, AgentExecutionError
from gcm_agent.config.config_manager import AgentSetupConfig
from gcm_agent.config import get_config_manager
from gcm_agent.config.config_manager import LLMProviderConfig
from gcm_agent.utils.logger import get_agent_logger

from watsonxorch.models import AgentRequest, AgentResponse


async def create_graph():
    """
    Create and return the LangGraph graph for WatsonX Orchestrate.
    
    This function is the entrypoint specified in agent.yaml.
    It initializes the GCM Agent and returns the underlying LangGraph graph.
    
    Returns:
        LangGraph graph instance
        
    Example:
        >>> graph = await create_graph()
        >>> # WatsonX Orchestrate will use this graph for agent execution
    """
    logger = get_agent_logger()
    logger.info("Creating LangGraph graph for WatsonX Orchestrate")
    
    try:
        # Load configuration
        config_mgr = get_config_manager()
        
        # Determine LLM provider
        llm_provider = config_mgr.get_llm_provider()
        
        if llm_provider == "watsonx":
            llm_config = LLMProviderConfig(
                provider="watsonx",
                watsonx_config=config_mgr.get_watsonx_config(),
                watsonx_api_key=config_mgr.get_watsonx_api_key()
            )
        elif llm_provider == "openai":
            llm_config = LLMProviderConfig(
                provider="openai",
                openai_config=config_mgr.get_openai_config(),
                openai_api_key=config_mgr.get_openai_api_key()
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        # Create agent setup config
        setup_config = AgentSetupConfig(
            keycloak_config=config_mgr.get_keycloak_config(),
            gcm_config=config_mgr.get_gcm_config(),
            auth_config=config_mgr.get_auth_config(),
            llm_config=llm_config,
            agent_config=config_mgr.get_agent_config(),
            password=config_mgr.get_password(),
            client_secret=config_mgr.get_client_secret()
        )
        
        # Create GCM agent
        agent = await create_gcm_agent(setup_config)
        
        logger.info("LangGraph graph created successfully")
        
        # Return the underlying LangGraph graph
        return agent.graph
        
    except Exception as e:
        logger.error(f"Failed to create LangGraph graph: {e}")
        raise


class OrchestrateAdapter:
    """
    Adapter layer between WatsonX Orchestrate and GCM Agent.
    
    This class provides a stateless interface for executing agent requests,
    making it compatible with WatsonX Orchestrate's skill execution model.
    """
    
    def __init__(self, agent: GCMAgent):
        """
        Initialize orchestrate adapter.
        
        Args:
            agent: Initialized GCM Agent instance
        """
        self.agent = agent
        self.logger = get_agent_logger()
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    async def create(cls, config: AgentSetupConfig) -> "OrchestrateAdapter":
        """
        Create orchestrate adapter with initialized agent.
        
        Args:
            config: Agent setup configuration
            
        Returns:
            Initialized orchestrate adapter
            
        Example:
            >>> from gcm_agent.config import get_config_manager
            >>> from gcm_agent.config.config_manager import AgentSetupConfig, LLMProviderConfig
            >>> from watsonxorch.adapter import OrchestrateAdapter
            >>>
            >>> config_mgr = get_config_manager()
            >>> llm_config = LLMProviderConfig(
            ...     provider="watsonx",
            ...     watsonx_config=config_mgr.get_watsonx_config(),
            ...     watsonx_api_key=config_mgr.get_watsonx_api_key()
            ... )
            >>> setup_config = AgentSetupConfig(
            ...     keycloak_config=config_mgr.get_keycloak_config(),
            ...     gcm_config=config_mgr.get_gcm_config(),
            ...     auth_config=config_mgr.get_auth_config(),
            ...     llm_config=llm_config,
            ...     agent_config=config_mgr.get_agent_config(),
            ...     password=config_mgr.get_password(),
            ...     client_secret=config_mgr.get_client_secret()
            ... )
            >>> adapter = await OrchestrateAdapter.create(setup_config)
        """
        agent = await create_gcm_agent(config)
        return cls(agent)
    
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Execute agent request and return structured response.
        
        Args:
            request: Agent request with query and context
            
        Returns:
            Structured agent response
            
        Raises:
            AgentExecutionError: If agent execution fails
        """
        start_time = time.time()
        session_id = request.session_id or self._generate_session_id()
        
        self.logger.info(
            f"Executing agent request",
            extra={
                "session_id": session_id,
                "query": request.query[:100],  # Truncate for logging
                "has_context": bool(request.context),
            }
        )
        
        try:
            # Execute agent query
            result = await self.agent.chat(request.query)
            
            # Extract tools used from agent history
            tools_used = self._extract_tools_used()
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Build response
            response = AgentResponse(
                result=result,
                tools_used=tools_used,
                execution_time=execution_time,
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat(),
                metadata={
                    "query_length": len(request.query),
                    "context_keys": list(request.context.keys()) if request.context else [],
                    "agent_config": {
                        "discovery_mode": self.agent.agent_config.discovery_mode,
                        "max_iterations": self.agent.agent_config.max_iterations,
                    }
                }
            )
            
            self.logger.info(
                f"Agent request completed successfully",
                extra={
                    "session_id": session_id,
                    "execution_time": execution_time,
                    "tools_used_count": len(tools_used),
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                f"Agent execution failed: {e}",
                extra={
                    "session_id": session_id,
                    "query": request.query[:100],
                    "error_type": type(e).__name__,
                }
            )
            raise AgentExecutionError(f"Failed to execute agent request: {e}") from e
    
    async def stream_execute(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        """
        Execute agent request with streaming response.
        
        Args:
            request: Agent request with query and context
            
        Yields:
            Response chunks as they are generated
            
        Raises:
            AgentExecutionError: If agent execution fails
        """
        session_id = request.session_id or self._generate_session_id()
        
        self.logger.info(
            f"Starting streaming agent request",
            extra={
                "session_id": session_id,
                "query": request.query[:100],
            }
        )
        
        try:
            async for chunk in self.agent.stream_chat(request.query):
                yield chunk
                
        except Exception as e:
            self.logger.error(
                f"Streaming execution failed: {e}",
                extra={
                    "session_id": session_id,
                    "error_type": type(e).__name__,
                }
            )
            raise AgentExecutionError(f"Failed to stream agent response: {e}") from e
    
    def _extract_tools_used(self) -> list:
        """Extract list of tools used from agent history."""
        tools_used = []
        
        if hasattr(self.agent, 'history') and self.agent.history:
            for message in self.agent.history:
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if hasattr(tool_call, 'name'):
                            tools_used.append(tool_call.name)
        
        return tools_used
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"sess_{uuid.uuid4().hex[:12]}"
    
    async def close(self):
        """Close adapter and cleanup resources."""
        self.logger.info("Closing orchestrate adapter")
        if self.agent:
            await self.agent.close()

# Made with Bob
