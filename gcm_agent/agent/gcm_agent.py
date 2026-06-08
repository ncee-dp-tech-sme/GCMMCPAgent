"""Main LangGraph agent module for coordinating prompts, tools, and GCM-specific workflows."""

# Made with Bob
# 2026-06-06 03:10 UTC - Added OpenAI LLM support as alternative to WatsonX
# 2026-06-06 01:30 UTC - Added error handling in stream_chat to prevent TaskGroup exceptions
# 2026-06-05 22:13 UTC - Added tool limiting to respect WatsonX 128 tool limit
# 2026-06-05 22:11 UTC - Initial implementation of LangGraph agent following AGENTS.md patterns
# 2026-06-05 21:51 UTC - Added WatsonX URL parameter to LLM initialization
# 2026-06-05 22:05 UTC - Fixed to use ChatWatsonx instead of WatsonxLLM for tool binding support
# 2026-06-06 02:43 UTC - Added WatsonX SSL verification configuration to LLM initialization

from typing import List, Optional, AsyncGenerator, Union
from datetime import datetime

from langchain_ibm import ChatWatsonx
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import Tool
from langchain_core.language_models.chat_models import BaseChatModel

from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader
from gcm_agent.config.config_manager import WatsonXConfig, OpenAIConfig, AgentConfig
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
        agent_config: AgentConfig,
        llm_provider: str = "watsonx",
        watsonx_config: Optional[WatsonXConfig] = None,
        watsonx_api_key: Optional[str] = None,
        openai_config: Optional[OpenAIConfig] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize GCM Agent with LangGraph.
        
        Args:
            mcp_client: Connected MCP client
            tool_loader: Tool loader instance
            agent_config: Agent configuration
            llm_provider: LLM provider ("watsonx" or "openai")
            watsonx_config: WatsonX configuration (required if llm_provider="watsonx")
            watsonx_api_key: WatsonX API key (required if llm_provider="watsonx")
            openai_config: OpenAI configuration (required if llm_provider="openai")
            openai_api_key: OpenAI API key (required if llm_provider="openai")
        """
        self.mcp_client = mcp_client
        self.tool_loader = tool_loader
        self.agent_config = agent_config
        self.llm_provider = llm_provider.lower()
        self.logger = get_agent_logger()
        
        # Store LLM-specific configs
        self.watsonx_config = watsonx_config
        self.watsonx_api_key = watsonx_api_key
        self.openai_config = openai_config
        self.openai_api_key = openai_api_key
        
        # Validate configuration based on provider
        if self.llm_provider == "watsonx":
            if not watsonx_config or not watsonx_api_key:
                raise AgentInitializationError("WatsonX config and API key required for watsonx provider")
        elif self.llm_provider == "openai":
            if not openai_config or not openai_api_key:
                raise AgentInitializationError("OpenAI config and API key required for openai provider")
        else:
            raise AgentInitializationError(f"Unsupported LLM provider: {llm_provider}")
        
        # Initialize components
        self.llm: Optional[BaseChatModel] = None
        self.tools: List[Tool] = []
        self.graph: Optional[StateGraph] = None
        self.history: List[BaseMessage] = []
        
        self.logger.info(f"GCM Agent instance created (LLM provider: {self.llm_provider})")

    def _initialize_llm(self) -> BaseChatModel:
        """
        Initialize LLM based on configured provider.
        
        Returns:
            Configured LLM instance (ChatWatsonx or ChatOpenAI)
        """
        if self.llm_provider == "watsonx":
            self.logger.debug(
                f"Initializing ChatWatsonx with model: {self.watsonx_config.model} "
                f"at {self.watsonx_config.url} (verify_ssl={self.watsonx_config.verify_ssl}), "
                f"temperature={self.watsonx_config.temperature}, max_tokens={self.watsonx_config.max_tokens}"
            )
            
            return ChatWatsonx(
                model_id=self.watsonx_config.model,
                url=self.watsonx_config.url,
                project_id=self.watsonx_config.project_id,
                apikey=self.watsonx_api_key,
                verify=self.watsonx_config.verify_ssl,
                params={
                    "max_tokens": self.watsonx_config.max_tokens,
                    "temperature": self.watsonx_config.temperature,
                    "top_p": self.watsonx_config.top_p,
                    "top_k": self.watsonx_config.top_k,
                    "decoding_method": self.watsonx_config.decoding_method,
                },
            )
        
        elif self.llm_provider == "openai":
            self.logger.debug(
                f"Initializing ChatOpenAI with model: {self.openai_config.model}"
            )
            
            return ChatOpenAI(
                model=self.openai_config.model,
                api_key=self.openai_api_key,
                temperature=self.openai_config.temperature,
                max_tokens=self.openai_config.max_tokens,
            )
        
        else:
            raise AgentInitializationError(f"Unsupported LLM provider: {self.llm_provider}")

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
        self.logger.debug(
            f"Creating LangGraph agent with max_iterations={self.agent_config.max_iterations}"
        )
        
        # Get system prompt based on discovery mode
        system_prompt = get_system_prompt(self.agent_config.discovery_mode)
        
        # Create agent using create_react_agent() wrapper (CRITICAL per AGENTS.md)
        # Phase 2: Pass max_iterations from config to properly limit recursion
        agent = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=system_prompt,
        )
        
        # Store system prompt for injection at conversation start
        self._system_prompt = system_prompt
        self._system_prompt_injected = False
        
        # Build graph: START → agent → END
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent)
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
            
            # Inject system prompt once at start of conversation
            if not self._system_prompt_injected and len(self.history) == 0:
                self.history.append(SystemMessage(content=self._system_prompt))
                self._system_prompt_injected = True
                self.logger.debug("System prompt injected at conversation start")
            
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
            
            # Update history with sliding window to prevent unbounded growth
            # Filter out tool call messages and limit to last 20 messages (10 exchanges)
            MAX_HISTORY_MESSAGES = 20
            filtered_messages = [
                msg for msg in result["messages"]
                if not (isinstance(msg, AIMessage) and msg.tool_calls)
            ]
            self.history = filtered_messages[-MAX_HISTORY_MESSAGES:]
            self.logger.debug(f"History size: {len(self.history)} messages (max: {MAX_HISTORY_MESSAGES})")
            
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
            
            # Inject system prompt once at start of conversation
            if not self._system_prompt_injected and len(self.history) == 0:
                self.history.append(SystemMessage(content=self._system_prompt))
                self._system_prompt_injected = True
                self.logger.debug("System prompt injected at conversation start")
            
            # Add user message to history
            self.history.append(HumanMessage(content=message))
            
            # Track if we successfully streamed any content
            streamed_content = False
            last_messages = None
            
            # Stream agent responses
            async for chunk in self.graph.astream(
                {"messages": self.history},
                config={"recursion_limit": self.agent_config.max_iterations},
            ):
                if "agent" in chunk:
                    messages = chunk["agent"]["messages"]
                    last_messages = messages  # Keep track of last messages
                    for msg in messages:
                        if isinstance(msg, AIMessage) and not msg.tool_calls:
                            yield msg.content
                            streamed_content = True
            
            # Update history after streaming with sliding window
            # Use last_messages from streaming if available to avoid re-invoking
            if last_messages is not None:
                # Reconstruct history from streamed messages
                # Remove the user message we added and replace with complete result
                full_history = self.history[:-1] + last_messages
                
                # Apply sliding window and filter tool calls
                MAX_HISTORY_MESSAGES = 20
                filtered_messages = [
                    msg for msg in full_history
                    if not (isinstance(msg, AIMessage) and msg.tool_calls)
                ]
                self.history = filtered_messages[-MAX_HISTORY_MESSAGES:]
                self.logger.debug(f"Updated history from streamed messages (size: {len(self.history)})")
            else:
                # Fallback: try to invoke to get final state, but catch errors
                try:
                    result = await self.graph.ainvoke({"messages": self.history})
                    
                    # Apply sliding window and filter tool calls
                    MAX_HISTORY_MESSAGES = 20
                    filtered_messages = [
                        msg for msg in result["messages"]
                        if not (isinstance(msg, AIMessage) and msg.tool_calls)
                    ]
                    self.history = filtered_messages[-MAX_HISTORY_MESSAGES:]
                    self.logger.debug(f"Updated history from final invocation (size: {len(self.history)})")
                except Exception as invoke_error:
                    # If final invocation fails but we streamed content, log warning but don't fail
                    if streamed_content:
                        self.logger.warning(f"Final invocation failed but streaming succeeded: {invoke_error}")
                    else:
                        # If we didn't stream anything, this is a real error
                        raise
            
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
        """Clear conversation history and reset system prompt flag."""
        self.history = []
        self._system_prompt_injected = False
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
