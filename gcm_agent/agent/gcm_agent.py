"""Main LangGraph agent module for coordinating prompts, tools, and GCM-specific workflows."""

# Made with Bob
# 2026-06-05 22:13 UTC - Added tool limiting to respect WatsonX 128 tool limit
# 2026-06-05 22:11 UTC - Initial implementation of LangGraph agent following AGENTS.md patterns
# 2026-06-05 21:51 UTC - Added WatsonX URL parameter to LLM initialization
# 2026-06-05 22:05 UTC - Fixed to use ChatWatsonx instead of WatsonxLLM for tool binding support

from typing import List, Optional, AsyncGenerator
from datetime import datetime

from langchain_ibm import ChatWatsonx
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import Tool

from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader
from gcm_agent.config.config_manager import WatsonXConfig, AgentConfig
from gcm_agent.agent.prompts import get_system_prompt
from gcm_agent.utils.logger import get_agent_logger


# Custom exceptions for agent operations
class AgentError(Exception):
    """Base exception for agent operations."""
    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""
    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    pass


class ToolExecutionError(AgentError):
    """Raised when tool execution fails."""
    pass


class GCMAgent:
    """
    LangGraph-based agent for GCM operations.
    
    This agent orchestrates tool execution using LangGraph, following the patterns
    defined in AGENTS.md. It uses WatsonX LLM and GCM MCP tools to provide
    intelligent assistance for cryptography management tasks.
    """

    def __init__(
        self,
        mcp_client: GCMMCPClient,
        tool_loader: GCMToolLoader,
        watsonx_config: WatsonXConfig,
        api_key: str,
        agent_config: AgentConfig,
    ):
        """
        Initialize GCM Agent with LangGraph.
        
        Args:
            mcp_client: Connected MCP client
            tool_loader: Tool loader instance
            watsonx_config: WatsonX configuration
            api_key: WatsonX API key
            agent_config: Agent configuration
        """
        self.mcp_client = mcp_client
        self.tool_loader = tool_loader
        self.watsonx_config = watsonx_config
        self.api_key = api_key
        self.agent_config = agent_config
        self.logger = get_agent_logger()
        
        # Initialize components
        self.llm: Optional[ChatWatsonx] = None
        self.tools: List[Tool] = []
        self.graph: Optional[StateGraph] = None
        self.history: List[BaseMessage] = []
        
        self.logger.info("GCM Agent instance created")

    def _initialize_llm(self) -> ChatWatsonx:
        """
        Initialize WatsonX Chat LLM with configuration.
        
        Returns:
            Configured ChatWatsonx instance (supports tool calling)
        """
        self.logger.debug(f"Initializing ChatWatsonx with model: {self.watsonx_config.model} at {self.watsonx_config.url}")
        
        return ChatWatsonx(
            model_id=self.watsonx_config.model,
            url=self.watsonx_config.url,
            project_id=self.watsonx_config.project_id,
            apikey=self.api_key,
            params={
                "max_tokens": 2048,  # Use max_tokens instead of max_new_tokens to avoid warning
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
            },
        )

    async def _load_tools(self) -> List[Tool]:
        """
        Load tools from MCP server via tool loader.
        
        WatsonX has a hard limit of 128 tools. If more tools are loaded,
        we limit to the first 128 tools and log a warning.
        
        Returns:
            List of available tools (max 128 for WatsonX compatibility)
            
        Raises:
            AgentInitializationError: If tool loading fails
        """
        try:
            self.logger.debug("Loading tools from MCP server")
            tools = await self.tool_loader.load_tools()
            self.logger.info(f"Loaded {len(tools)} tools from MCP server")
            
            # WatsonX has a hard limit of 128 tools
            MAX_TOOLS = 128
            if len(tools) > MAX_TOOLS:
                self.logger.warning(
                    f"Loaded {len(tools)} tools, but WatsonX supports max {MAX_TOOLS}. "
                    f"Limiting to first {MAX_TOOLS} tools. "
                    f"Consider enabling discovery_mode=true for dynamic tool loading."
                )
                tools = tools[:MAX_TOOLS]
                self.logger.info(f"Using {len(tools)} tools after limiting")
            
            return tools
        except Exception as e:
            self.logger.error(f"Failed to load tools: {e}")
            raise AgentInitializationError(f"Failed to load tools: {e}") from e

    def _create_agent_graph(self) -> StateGraph:
        """
        Create LangGraph agent following AGENTS.md pattern.
        
        CRITICAL: Must use create_agent() wrapper, not raw LLM.
        Graph structure: START → agent → END (no tool node needed)
        
        Returns:
            Compiled StateGraph
        """
        self.logger.debug("Creating LangGraph agent")
        
        # Get system prompt based on discovery mode
        system_prompt = get_system_prompt(self.agent_config.discovery_mode)
        
        # Create agent using create_react_agent() wrapper (CRITICAL per AGENTS.md)
        # System prompt will be injected via messages in the agent node
        agent = create_react_agent(
            self.llm,
            self.tools,
        )
        
        # Define async agent node with system prompt injection
        async def agent_node(state: MessagesState) -> MessagesState:
            """Agent node that processes messages with system prompt."""
            # Inject system prompt as first message if not present
            messages = state["messages"]
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=system_prompt)] + messages
            
            result = await agent.ainvoke({"messages": messages})
            return {"messages": result["messages"]}
        
        # Build graph: START → agent → END
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_edge(START, "agent")
        graph.add_edge("agent", END)
        
        self.logger.debug("LangGraph agent created successfully")
        return graph.compile()

    async def initialize(self) -> None:
        """
        Initialize agent components (LLM, tools, graph).
        
        Must be called before using the agent.
        
        Raises:
            AgentInitializationError: If initialization fails
        """
        try:
            self.logger.info("Initializing GCM Agent")
            
            # Step 1: Initialize LLM
            self.llm = self._initialize_llm()
            
            # Step 2: Load tools
            self.tools = await self._load_tools()
            
            # Step 3: Create agent graph
            self.graph = self._create_agent_graph()
            
            self.logger.info("GCM Agent initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Agent initialization failed: {e}")
            raise AgentInitializationError(f"Agent initialization failed: {e}") from e

    async def chat(self, message: str) -> str:
        """
        Process a user message and return response.
        
        Args:
            message: User's message
            
        Returns:
            Agent's response
            
        Raises:
            AgentExecutionError: If execution fails
        """
        if self.graph is None:
            raise AgentExecutionError("Agent not initialized. Call initialize() first.")
        
        try:
            self.logger.debug(f"Processing message: {message[:100]}...")
            
            # Add user message to history
            self.history.append(HumanMessage(content=message))
            
            # Invoke agent
            result = await self.graph.ainvoke(
                {"messages": self.history},
                config={"recursion_limit": self.agent_config.max_iterations},
            )
            
            # Extract AI messages without tool_calls (per AGENTS.md)
            ai_messages = [
                msg
                for msg in result["messages"]
                if isinstance(msg, AIMessage) and not msg.tool_calls
            ]
            
            # Update history with complete result
            self.history = result["messages"]
            
            # Return last AI message
            if ai_messages:
                response = ai_messages[-1].content
                self.logger.debug(f"Generated response: {response[:100]}...")
                return response
            else:
                self.logger.warning("No response generated")
                return "No response generated"
                
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            raise AgentExecutionError(f"Agent execution failed: {e}") from e

    async def stream_chat(self, message: str) -> AsyncGenerator[str, None]:
        """
        Stream agent responses for real-time feedback.
        
        Args:
            message: User's message
            
        Yields:
            Response chunks
            
        Raises:
            AgentExecutionError: If execution fails
        """
        if self.graph is None:
            raise AgentExecutionError("Agent not initialized. Call initialize() first.")
        
        try:
            self.logger.debug(f"Streaming response for message: {message[:100]}...")
            
            # Add user message to history
            self.history.append(HumanMessage(content=message))
            
            # Stream agent responses
            async for chunk in self.graph.astream(
                {"messages": self.history},
                config={"recursion_limit": self.agent_config.max_iterations},
            ):
                if "agent" in chunk:
                    messages = chunk["agent"]["messages"]
                    for msg in messages:
                        if isinstance(msg, AIMessage) and not msg.tool_calls:
                            yield msg.content
            
            # Update history after streaming
            result = await self.graph.ainvoke({"messages": self.history})
            self.history = result["messages"]
            
        except Exception as e:
            self.logger.error(f"Agent streaming failed: {e}")
            raise AgentExecutionError(f"Agent streaming failed: {e}") from e

    def get_history(self) -> List[dict]:
        """
        Get conversation history in serializable format.
        
        Returns:
            List of message dictionaries with role, content, and timestamp
        """
        return [
            {
                "role": "human" if isinstance(msg, HumanMessage) else "ai",
                "content": msg.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for msg in self.history
        ]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []
        self.logger.info("Conversation history cleared")

    async def close(self) -> None:
        """Close agent and cleanup resources."""
        try:
            self.logger.info("Closing GCM Agent")
            await self.mcp_client.disconnect()
            self.history = []
            self.logger.info("GCM Agent closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing agent: {e}")
            raise AgentError(f"Error closing agent: {e}") from e


__all__ = [
    "GCMAgent",
    "AgentError",
    "AgentInitializationError",
    "AgentExecutionError",
    "ToolExecutionError",
]
