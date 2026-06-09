"""Chat interface module for interacting with the GCM LangChain agent through a local UI."""

# Made with Bob
# 2026-06-05 22:08 UTC - Fixed Gradio message format to use dict format with 'role' and 'content' keys (Gradio 6.0+)
# 2026-06-05 22:15 UTC - Initial implementation of chat UI with streaming support
# 2026-06-05 21:05 UTC - Updated to use separate KeycloakConfig and GCMServerConfig
# 2026-06-08 22:09 UTC - Integrated debug UI for real-time observability logs
# 2026-06-09 20:45 UTC - Refactored for better maintainability: extracted helpers, consolidated error handling, fixed streaming accumulation

from typing import List, Tuple, Optional, AsyncGenerator, Dict, Callable, Any
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


# Configuration validation helpers
def _validate_base_config(config_manager) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate base configuration and retrieve configs.
    
    Returns:
        Tuple of (error_message, config_dict) where error_message is None on success
    """
    if not config_manager.is_configured():
        return "Configuration incomplete. Please configure the agent first.", None
    
    try:
        configs = {
            'keycloak': config_manager.get_keycloak_config(),
            'gcm': config_manager.get_gcm_config(),
            'auth': config_manager.get_auth_config(),
            'agent': config_manager.get_agent_config(),
            'llm': config_manager.get_llm_config(),
            'password': config_manager.get_password(),
            'client_secret': config_manager.get_client_secret(),
        }
        
        if not all([configs['password'], configs['client_secret']]):
            return "Missing GCM credentials. Please reconfigure the agent.", None
        
        return None, configs
    except Exception as e:
        return f"Configuration retrieval failed: {str(e)}", None


def _get_watsonx_config(config_manager) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Get WatsonX configuration and API key."""
    watsonx_config = config_manager.get_watsonx_config()
    watsonx_api_key = config_manager.get_watsonx_api_key()
    
    if not watsonx_api_key:
        return "Missing WatsonX API key. Please reconfigure the agent.", None
    
    return None, {'config': watsonx_config, 'api_key': watsonx_api_key}


def _get_openai_config(config_manager) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Get OpenAI configuration and API key."""
    openai_config = config_manager.get_openai_config()
    openai_api_key = config_manager.get_openai_api_key()
    
    if not openai_api_key:
        return "Missing OpenAI API key. Please reconfigure the agent.", None
    
    return None, {'config': openai_config, 'api_key': openai_api_key}


# Provider configuration mapping
_PROVIDER_CONFIG_HANDLERS: Dict[str, Callable] = {
    'watsonx': _get_watsonx_config,
    'openai': _get_openai_config,
}


def _get_llm_provider_config(config_manager, provider: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Get LLM provider-specific configuration.
    
    Returns:
        Tuple of (error_message, provider_config) where error_message is None on success
    """
    handler = _PROVIDER_CONFIG_HANDLERS.get(provider)
    if not handler:
        return f"Unknown LLM provider: {provider}", None
    
    return handler(config_manager)


async def _handle_initialization_error(error_msg: str, agent_state: AgentState) -> str:
    """
    Centralized error handling for initialization failures.
    
    Args:
        error_msg: Error message to log and display
        agent_state: Agent state to update
        
    Returns:
        Formatted error message for UI
    """
    logger.error(error_msg)
    agent_state.error_message = error_msg
    await agent_state.cleanup()
    return f"❌ {error_msg}"


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
        
        # Get and validate base configuration
        config_manager = get_config_manager()
        error_msg, configs = _validate_base_config(config_manager)
        if error_msg:
            return await _handle_initialization_error(error_msg, _agent_state)
        
        # Get LLM provider-specific configuration
        llm_config = configs['llm']
        error_msg, provider_data = _get_llm_provider_config(config_manager, llm_config.provider)
        if error_msg:
            return await _handle_initialization_error(error_msg, _agent_state)
        
        # Create unified LLM provider config
        from gcm_agent.config.config_manager import LLMProviderConfig, AgentSetupConfig
        from gcm_agent.agent import create_gcm_agent
        
        llm_provider_config = LLMProviderConfig(
            provider=llm_config.provider,
            watsonx_config=provider_data.get('config') if llm_config.provider == 'watsonx' else None,
            watsonx_api_key=provider_data.get('api_key') if llm_config.provider == 'watsonx' else None,
            openai_config=provider_data.get('config') if llm_config.provider == 'openai' else None,
            openai_api_key=provider_data.get('api_key') if llm_config.provider == 'openai' else None,
        )
        
        # Create consolidated setup config
        setup_config = AgentSetupConfig(
            keycloak_config=configs['keycloak'],
            gcm_config=configs['gcm'],
            auth_config=configs['auth'],
            llm_config=llm_provider_config,
            agent_config=configs['agent'],
            password=configs['password'],
            client_secret=configs['client_secret'],
        )
        
        # Create and initialize agent using refactored function
        logger.debug(f"Creating GCM Agent with {llm_config.provider} LLM")
        _agent_state.agent = await create_gcm_agent(setup_config)
        
        # Store MCP client and tool loader references for cleanup
        _agent_state.mcp_client = _agent_state.agent.mcp_client
        _agent_state.tool_loader = _agent_state.agent.tool_loader
        
        # Integrate debug UI
        debug_ui = get_debug_ui_instance()
        _agent_state.agent.debug_ui = debug_ui
        
        _agent_state.initialized = True
        _agent_state.error_message = None
        
        logger.info("GCM Agent initialized successfully")
        return "✅ Agent initialized successfully! You can now start chatting."
        
    except (MissingConfigError, AgentInitializationError) as e:
        error_msg = f"{'Configuration' if isinstance(e, MissingConfigError) else 'Agent initialization'} error: {str(e)}"
        return await _handle_initialization_error(error_msg, _agent_state)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return await _handle_initialization_error(error_msg, _agent_state)


async def chat_response(message: str, history: List[dict], agent_state: Optional[AgentState] = None) -> AsyncGenerator[Tuple[List[dict], str], None]:
    """
    Process chat message and stream response.
    
    Args:
        message: User's message
        history: Chat history as list of message dictionaries with 'role' and 'content' keys
        agent_state: Optional agent state (defaults to global state for backward compatibility)
        
    Yields:
        Updated history and empty message box
    """
    # Use provided agent_state or fall back to global state
    state = agent_state or _agent_state
    
    if not message or not message.strip():
        yield history, ""
        return
    
    if not state.is_ready():
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
        
        # Stream response - accumulate chunks properly
        response = ""
        async for chunk in state.agent.stream_chat(message):
            response += chunk  # Accumulate chunks instead of overwriting
            # Update the last message in history with accumulated response
            history[-1] = {"role": "assistant", "content": response}
            yield history, ""
        
        logger.debug(f"Response complete: {len(response)} characters")
        
    except (AgentExecutionError, Exception) as e:
        # Consolidated error handling
        error_prefix = "Agent error" if isinstance(e, AgentExecutionError) else "Unexpected error"
        error_msg = f"❌ {error_prefix}: {str(e)}"
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


def _show_export(json_str: str, status: str) -> Tuple[dict, dict, str]:
    """
    Show export output and status (extracted from create_chat_ui for better organization).
    
    Args:
        json_str: Exported JSON string
        status: Export status message
        
    Returns:
        Tuple of Gradio update dicts and status
    """
    return (
        gr.update(visible=True, value=json_str),
        gr.update(visible=True, value=status),
        status
    )


def _build_status_row() -> Tuple[gr.Textbox, gr.Button]:
    """Build status indicator and initialization button row."""
    with gr.Row():
        status_indicator = gr.Textbox(
            label="Agent Status",
            value="⚠️ Not Initialized",
            interactive=False,
            scale=3
        )
        init_btn = gr.Button("🚀 Initialize Agent", variant="primary", scale=1)
    return status_indicator, init_btn


def _build_chatbot_section() -> Tuple[gr.Chatbot, gr.Textbox]:
    """Build chatbot display and message input section."""
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
    
    return chatbot, msg


def _build_action_buttons() -> Tuple[gr.Button, gr.Button, gr.Button]:
    """Build action buttons row (send, clear, export)."""
    with gr.Row():
        submit_btn = gr.Button("📤 Send", variant="primary", scale=2)
        clear_btn = gr.Button("🗑️ Clear History", variant="secondary", scale=1)
        export_btn = gr.Button("💾 Export", variant="secondary", scale=1)
    return submit_btn, clear_btn, export_btn


def _build_export_section() -> Tuple[gr.Textbox, gr.Textbox]:
    """Build export output section."""
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
    
    return export_output, export_status


def _setup_submit_handler(component: gr.components.Component, msg: gr.Textbox, chatbot: gr.Chatbot):
    """
    Setup unified submit handler for both message textbox and submit button.
    
    Args:
        component: Gradio component to attach handler to (textbox or button)
        msg: Message input textbox
        chatbot: Chatbot display component
    """
    component.click(
        fn=chat_response,
        inputs=[msg, chatbot],
        outputs=[chatbot, msg]
    ) if isinstance(component, gr.Button) else component.submit(
        fn=chat_response,
        inputs=[msg, chatbot],
        outputs=[chatbot, msg]
    )


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
        
        # Build UI sections using helper functions
        status_indicator, init_btn = _build_status_row()
        
        gr.Markdown("---")
        
        chatbot, msg = _build_chatbot_section()
        submit_btn, clear_btn, export_btn = _build_action_buttons()
        export_output, export_status = _build_export_section()
        
        # Event handlers
        init_btn.click(
            fn=initialize_agent,
            outputs=status_indicator
        )
        
        # Unified submit handlers using helper
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
        
        export_btn.click(
            fn=export_conversation,
            outputs=[export_output, export_status]
        ).then(
            fn=_show_export,
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
