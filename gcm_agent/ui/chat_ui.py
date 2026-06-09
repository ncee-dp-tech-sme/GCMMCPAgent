"""Chat interface module for interacting with the GCM LangChain agent through a local UI."""

# Made with Bob
# 2026-06-05 22:08 UTC - Fixed Gradio message format to use dict format with 'role' and 'content' keys (Gradio 6.0+)
# 2026-06-05 22:15 UTC - Initial implementation of chat UI with streaming support
# 2026-06-05 21:05 UTC - Updated to use separate KeycloakConfig and GCMServerConfig
# 2026-06-08 22:09 UTC - Integrated debug UI for real-time observability logs

from typing import List, Tuple, Optional, AsyncGenerator, Dict
import json
from datetime import datetime, timezone
import gradio as gr

from gcm_agent.agent.gcm_agent import GCMAgent, AgentInitializationError, AgentExecutionError
from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader
from gcm_agent.config.config_manager import get_config_manager, MissingConfigError
from gcm_agent.utils.logger import get_ui_logger
from gcm_agent.ui.debug_ui import get_debug_ui_instance


logger = get_ui_logger()


class AgentState:
    """Manages agent instance state for the UI."""
    
    def __init__(self):
        """Initialize agent state."""
        self.agent: Optional[GCMAgent] = None
        self.mcp_client: Optional[GCMMCPClient] = None
        self.tool_loader: Optional[GCMToolLoader] = None
        self.initialized: bool = False
        self.error_message: Optional[str] = None
    
    def is_ready(self) -> bool:
        """Check if agent is ready for chat."""
        return self.initialized and self.agent is not None
    
    def get_status(self) -> str:
        """Get current agent status."""
        if self.error_message:
            return f"❌ Error: {self.error_message}"
        elif self.initialized:
            return "✅ Agent Ready"
        else:
            return "⚠️ Not Initialized"
    
    async def cleanup(self):
        """Cleanup agent resources."""
        if self.agent:
            try:
                await self.agent.close()
            except Exception as e:
                logger.error(f"Error closing agent: {e}")
        
        self.agent = None
        self.mcp_client = None
        self.tool_loader = None
        self.initialized = False
        self.error_message = None


# Global agent state
_agent_state = AgentState()


async def initialize_agent() -> str:
    """
    Initialize agent from configuration.
    
    Returns:
        Status message
    """
    global _agent_state
    
    try:
        logger.info("Initializing GCM Agent from configuration")
        
        # Cleanup existing agent if any
        await _agent_state.cleanup()
        
        # Get configuration
        config_manager = get_config_manager()
        
        if not config_manager.is_configured():
            error_msg = "Configuration incomplete. Please configure the agent first."
            logger.warning(error_msg)
            _agent_state.error_message = error_msg
            return f"❌ {error_msg}"
        
        # Get all configuration
        keycloak_config = config_manager.get_keycloak_config()
        gcm_config = config_manager.get_gcm_config()
        auth_config = config_manager.get_auth_config()
        agent_config = config_manager.get_agent_config()
        llm_config = config_manager.get_llm_config()
        
        # Get sensitive credentials
        password = config_manager.get_password()
        client_secret = config_manager.get_client_secret()
        
        if not all([password, client_secret]):
            error_msg = "Missing GCM credentials. Please reconfigure the agent."
            logger.error(error_msg)
            _agent_state.error_message = error_msg
            return f"❌ {error_msg}"
        
        # Get LLM-specific configuration based on provider
        watsonx_config = None
        watsonx_api_key = None
        openai_config = None
        openai_api_key = None
        
        if llm_config.provider == "watsonx":
            watsonx_config = config_manager.get_watsonx_config()
            watsonx_api_key = config_manager.get_watsonx_api_key()
            if not watsonx_api_key:
                error_msg = "Missing WatsonX API key. Please reconfigure the agent."
                logger.error(error_msg)
                _agent_state.error_message = error_msg
                return f"❌ {error_msg}"
        elif llm_config.provider == "openai":
            openai_config = config_manager.get_openai_config()
            openai_api_key = config_manager.get_openai_api_key()
            if not openai_api_key:
                error_msg = "Missing OpenAI API key. Please reconfigure the agent."
                logger.error(error_msg)
                _agent_state.error_message = error_msg
                return f"❌ {error_msg}"
        
        # Create MCP client and tool loader using the helper function
        logger.debug("Creating MCP client and tool loader")
        from gcm_agent.mcp import create_gcm_mcp_client
        
        _agent_state.mcp_client, _agent_state.tool_loader = await create_gcm_mcp_client(
            keycloak_config=keycloak_config,
            gcm_config=gcm_config,
            auth_config=auth_config,
            agent_config=agent_config,
            password=password,
            client_secret=client_secret,
        )
        
        # Create unified LLM provider config
        from gcm_agent.config.config_manager import LLMProviderConfig
        
        llm_provider_config = LLMProviderConfig(
            provider=llm_config.provider,
            watsonx_config=watsonx_config,
            watsonx_api_key=watsonx_api_key,
            openai_config=openai_config,
            openai_api_key=openai_api_key,
        )
        
        # Create agent with debug UI integration
        logger.debug(f"Creating GCM Agent with {llm_config.provider} LLM")
        debug_ui = get_debug_ui_instance()
        _agent_state.agent = GCMAgent(
            mcp_client=_agent_state.mcp_client,
            tool_loader=_agent_state.tool_loader,
            agent_config=agent_config,
            llm_config=llm_provider_config,
            debug_ui=debug_ui,
        )
        
        # Initialize agent
        logger.debug("Initializing agent components")
        await _agent_state.agent.initialize()
        
        _agent_state.initialized = True
        _agent_state.error_message = None
        
        logger.info("GCM Agent initialized successfully")
        return "✅ Agent initialized successfully! You can now start chatting."
        
    except MissingConfigError as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        _agent_state.error_message = error_msg
        await _agent_state.cleanup()
        return f"❌ {error_msg}"
    except AgentInitializationError as e:
        error_msg = f"Agent initialization failed: {str(e)}"
        logger.error(error_msg)
        _agent_state.error_message = error_msg
        await _agent_state.cleanup()
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        _agent_state.error_message = error_msg
        await _agent_state.cleanup()
        return f"❌ {error_msg}"


async def chat_response(message: str, history: List[dict]) -> AsyncGenerator[Tuple[List[dict], str], None]:
    """
    Process chat message and stream response.
    
    Args:
        message: User's message
        history: Chat history as list of message dictionaries with 'role' and 'content' keys
        
    Yields:
        Updated history and empty message box
    """
    global _agent_state
    
    if not message or not message.strip():
        yield history, ""
        return
    
    if not _agent_state.is_ready():
        error_response = "⚠️ Agent not initialized. Please initialize the agent first."
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_response})
        yield history, ""
        return
    
    try:
        logger.debug(f"Processing message: {message[:100]}...")
        
        # Add user message to history immediately
        history.append({"role": "user", "content": message})
        # Add placeholder for assistant response
        history.append({"role": "assistant", "content": ""})
        
        # Stream response
        response = ""
        async for chunk in _agent_state.agent.stream_chat(message):
            response = chunk
            # Update the last message in history with accumulated response
            history[-1] = {"role": "assistant", "content": response}
            yield history, ""
        
        logger.debug(f"Response complete: {len(response)} characters")
        
    except AgentExecutionError as e:
        error_msg = f"❌ Agent error: {str(e)}"
        logger.error(error_msg)
        history[-1] = {"role": "assistant", "content": error_msg}
        yield history, ""
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        logger.error(error_msg)
        history[-1] = {"role": "assistant", "content": error_msg}
        yield history, ""


def clear_history() -> Tuple[List[dict], str]:
    """
    Clear conversation history.
    
    Returns:
        Empty history (list of message dicts) and status message
    """
    global _agent_state
    
    if _agent_state.agent:
        _agent_state.agent.clear_history()
        logger.info("Conversation history cleared")
        return [], "✅ History cleared"
    else:
        return [], "⚠️ No active agent"


def export_conversation() -> Tuple[str, str]:
    """
    Export conversation history to JSON.
    
    Returns:
        JSON string and status message
    """
    global _agent_state
    
    if not _agent_state.agent:
        return "", "⚠️ No active agent to export"
    
    try:
        history = _agent_state.agent.get_history()
        
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(history),
            "messages": history,
        }
        
        json_str = json.dumps(export_data, indent=2)
        logger.info(f"Exported {len(history)} messages")
        
        return json_str, f"✅ Exported {len(history)} messages"
        
    except Exception as e:
        error_msg = f"Export failed: {str(e)}"
        logger.error(error_msg)
        return "", f"❌ {error_msg}"


def get_agent_status() -> str:
    """
    Get current agent status.
    
    Returns:
        Status string
    """
    global _agent_state
    return _agent_state.get_status()


def create_chat_ui() -> gr.Blocks:
    """
    Create chat UI with Gradio.
    
    Returns:
        Gradio Blocks interface
    """
    logger.info("Creating chat UI")
    
    with gr.Blocks(title="GCM Agent Chat") as chat_ui:
        gr.Markdown("# 💬 GCM Agent Chat Interface")
        gr.Markdown("Interact with IBM Guardium Cryptography Manager using natural language.")
        
        with gr.Row():
            status_indicator = gr.Textbox(
                label="Agent Status",
                value="⚠️ Not Initialized",
                interactive=False,
                scale=3
            )
            init_btn = gr.Button("🚀 Initialize Agent", variant="primary", scale=1)
        
        gr.Markdown("---")
        
        chatbot = gr.Chatbot(
            label="Conversation",
            height=500,
            show_label=True,
            avatar_images=(None, "🤖"),
        )
        
        with gr.Row():
            msg = gr.Textbox(
                label="Message",
                placeholder="Ask me about GCM operations... (e.g., 'List all keys', 'Show key groups', 'Get key details')",
                scale=5,
                lines=2
            )
        
        with gr.Row():
            submit_btn = gr.Button("📤 Send", variant="primary", scale=2)
            clear_btn = gr.Button("🗑️ Clear History", variant="secondary", scale=1)
            export_btn = gr.Button("💾 Export", variant="secondary", scale=1)
        
        export_output = gr.Textbox(
            label="Exported Conversation (JSON)",
            visible=False,
            lines=10,
            max_lines=20
        )
        
        export_status = gr.Textbox(
            label="Export Status",
            visible=False,
            interactive=False
        )
        
        # Event handlers
        init_btn.click(
            fn=initialize_agent,
            outputs=status_indicator
        )
        
        # Submit message on button click or Enter key
        msg.submit(
            fn=chat_response,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        submit_btn.click(
            fn=chat_response,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        clear_btn.click(
            fn=clear_history,
            outputs=[chatbot, status_indicator]
        )
        
        def show_export(json_str: str, status: str) -> Tuple[dict, dict, str]:
            """Show export output and status."""
            return (
                gr.update(visible=True, value=json_str),
                gr.update(visible=True, value=status),
                status
            )
        
        export_btn.click(
            fn=export_conversation,
            outputs=[export_output, export_status]
        ).then(
            fn=show_export,
            inputs=[export_output, export_status],
            outputs=[export_output, export_status, status_indicator]
        )
        
        # Update status on load
        chat_ui.load(
            fn=get_agent_status,
            outputs=status_indicator
        )
    
    logger.info("Chat UI created successfully")
    return chat_ui


__all__ = ["create_chat_ui"]
