"""Gradio-based configuration UI module for collecting and validating GCM agent settings."""

# Made with Bob
# 2026-06-08 20:48 UTC - Phase 2: Added configurable LLM parameters (temperature, max_tokens, top_p, top_k, decoding_method) to UI
# 2026-06-05 22:14 UTC - Initial implementation of configuration UI with secure credential handling
# 2026-06-05 21:03 UTC - Split Keycloak and GCM server configuration into separate tabs
# 2026-06-05 21:50 UTC - Added WatsonX URL field and made model field editable
# 2026-06-06 02:43 UTC - Added WatsonX SSL verification configuration to the UI

from typing import Tuple, Optional
import gradio as gr

from gcm_agent.config.config_manager import (
    get_config_manager,
    KeycloakConfig,
    GCMServerConfig,
    AuthConfig,
    WatsonXConfig,
    AgentConfig,
    ConfigurationError,
    InvalidConfigError,
    MissingConfigError,
)
from gcm_agent.config.storage import StorageError
from gcm_agent.auth.keycloak_auth import KeycloakAuthenticator
from gcm_agent.utils.logger import get_ui_logger


logger = get_ui_logger()


def load_configuration() -> Tuple[str, int, str, bool, str, str, bool, str, str, str, str, str, str, str, str, bool, float, int, float, int, str, bool, int, int, str]:
    """
    Load existing configuration from secure storage.
    
    Returns:
        Tuple of all configuration values for UI fields (including new LLM parameters)
    """
    try:
        config_manager = get_config_manager()
        
        # Try to load configuration
        if not config_manager.load_config():
            logger.info("No existing configuration found")
            return ("", 443, "master", True, "", "", True, "", "", "", "", "https://us-south.ml.cloud.ibm.com", "", "", "ibm/granite-13b-chat-v2", True, 0.1, 4096, 0.95, 40, "greedy", False, 30, 300, "No configuration found. Please enter your settings.")
        
        # Load each section
        keycloak_config = config_manager.get_keycloak_config()
        gcm_config = config_manager.get_gcm_config()
        auth_config = config_manager.get_auth_config()
        watsonx_config = config_manager.get_watsonx_config()
        agent_config = config_manager.get_agent_config()
        
        # Get sensitive credentials (will be empty strings if not found)
        password = config_manager.get_password() or ""
        client_secret = config_manager.get_client_secret() or ""
        api_key = config_manager.get_watsonx_api_key() or ""
        
        logger.info("Configuration loaded successfully")
        
        return (
            keycloak_config.url,
            keycloak_config.port,
            keycloak_config.realm,
            keycloak_config.verify_ssl,
            gcm_config.url,
            gcm_config.hostname,
            gcm_config.verify_ssl,
            auth_config.username,
            password,
            auth_config.client_id,
            client_secret,
            watsonx_config.url,
            watsonx_config.project_id,
            api_key,
            watsonx_config.model,
            watsonx_config.verify_ssl,
            watsonx_config.temperature,
            watsonx_config.max_tokens,
            watsonx_config.top_p,
            watsonx_config.top_k,
            watsonx_config.decoding_method,
            agent_config.discovery_mode,
            agent_config.max_iterations,
            agent_config.timeout,
            "✅ Configuration loaded successfully"
        )
        
    except (MissingConfigError, InvalidConfigError) as e:
        logger.warning(f"Configuration incomplete or invalid: {e}")
        return ("", 443, "master", True, "", "", True, "", "", "", "", "https://us-south.ml.cloud.ibm.com", "", "", "ibm/granite-13b-chat-v2", True, 0.1, 4096, 0.95, 40, "greedy", False, 30, 300, f"⚠️ Configuration incomplete: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return ("", 443, "master", True, "", "", True, "", "", "", "", "https://us-south.ml.cloud.ibm.com", "", "", "ibm/granite-13b-chat-v2", True, 0.1, 4096, 0.95, 40, "greedy", False, 30, 300, f"❌ Error loading configuration: {str(e)}")


def save_configuration(
    keycloak_url: str,
    keycloak_port: int,
    keycloak_realm: str,
    keycloak_verify_ssl: bool,
    gcm_url: str,
    gcm_hostname: str,
    gcm_verify_ssl: bool,
    username: str,
    password: str,
    client_id: str,
    client_secret: str,
    watsonx_url: str,
    project_id: str,
    api_key: str,
    model: str,
    watsonx_verify_ssl: bool,
    temperature: float,
    max_tokens: int,
    top_p: float,
    top_k: int,
    decoding_method: str,
    discovery_mode: bool,
    max_iterations: int,
    timeout: int,
) -> str:
    """
    Save configuration to secure storage.
    
    Args:
        All configuration parameters from UI fields
        
    Returns:
        Status message
    """
    try:
        config_manager = get_config_manager()
        
        # Validate required fields
        if not all([keycloak_url, gcm_url, gcm_hostname, username, password, client_id, client_secret, watsonx_url, project_id, api_key, model]):
            return "❌ Error: All fields are required"
        
        # Create configuration objects (will validate)
        keycloak_config = KeycloakConfig(
            url=keycloak_url,
            port=keycloak_port,
            realm=keycloak_realm,
            verify_ssl=keycloak_verify_ssl,
        )
        
        gcm_config = GCMServerConfig(
            url=gcm_url,
            hostname=gcm_hostname,
            verify_ssl=gcm_verify_ssl,
        )
        
        auth_config = AuthConfig(
            username=username,
            client_id=client_id,
        )
        
        watsonx_config = WatsonXConfig(
            url=watsonx_url,
            project_id=project_id,
            model=model,
            verify_ssl=watsonx_verify_ssl,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            decoding_method=decoding_method,
        )
        
        agent_config = AgentConfig(
            discovery_mode=discovery_mode,
            max_iterations=max_iterations,
            timeout=timeout,
        )
        
        # Save configurations
        config_manager.update_keycloak_config(keycloak_config)
        config_manager.update_gcm_config(gcm_config)
        config_manager.update_auth_config(auth_config, password, client_secret)
        config_manager.update_watsonx_config(watsonx_config, api_key)
        config_manager.update_agent_config(agent_config)
        
        logger.info("Configuration saved successfully")
        return "✅ Configuration saved successfully"
        
    except InvalidConfigError as e:
        logger.error(f"Invalid configuration: {e}")
        return f"❌ Invalid configuration: {str(e)}"
    except StorageError as e:
        logger.error(f"Storage error: {e}")
        return f"❌ Storage error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error saving configuration: {e}")
        return f"❌ Error: {str(e)}"


async def test_connection(
    keycloak_url: str,
    keycloak_port: int,
    keycloak_realm: str,
    keycloak_verify_ssl: bool,
    username: str,
    password: str,
    client_id: str,
    client_secret: str,
) -> str:
    """
    Test connection to Keycloak server with provided credentials.
    
    Args:
        Keycloak server and authentication parameters
        
    Returns:
        Status message
    """
    try:
        # Validate required fields
        if not all([keycloak_url, username, password, client_id, client_secret]):
            return "❌ Error: All connection fields are required"
        
        logger.info("Testing connection to Keycloak server")
        
        # Create auth instance and test connection
        auth = KeycloakAuthenticator(
            keycloak_url=keycloak_url,
            realm=keycloak_realm,
            client_id=client_id,
            username=username,
            password=password,
            client_secret=client_secret,
            verify_ssl=keycloak_verify_ssl,
        )
        
        # Attempt to get token
        token = await auth.get_token()
        
        if token:
            logger.info("Connection test successful")
            return "✅ Connection successful! Keycloak credentials are valid."
        else:
            logger.warning("Connection test failed: No token received")
            return "❌ Connection failed: Unable to obtain authentication token"
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return f"❌ Connection failed: {str(e)}"


def clear_configuration() -> str:
    """
    Clear all configuration from secure storage.
    
    Returns:
        Status message
    """
    try:
        config_manager = get_config_manager()
        config_manager.reset_config()
        logger.info("Configuration cleared successfully")
        return "✅ Configuration cleared successfully"
    except StorageError as e:
        logger.error(f"Failed to clear configuration: {e}")
        return f"❌ Error clearing configuration: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error clearing configuration: {e}")
        return f"❌ Error: {str(e)}"


def create_config_ui() -> gr.Blocks:
    """
    Create configuration UI with Gradio.
    
    Returns:
        Gradio Blocks interface
    """
    logger.info("Creating configuration UI")
    
    with gr.Blocks(title="GCM Agent Configuration") as config_ui:
        gr.Markdown("# 🔧 GCM Agent Configuration")
        gr.Markdown("Configure your GCM Agent connection, authentication, and settings.")
        
        with gr.Tab("🔑 Keycloak Server"):
            gr.Markdown("### Keycloak Authentication Server")
            keycloak_url = gr.Textbox(
                label="Keycloak URL",
                placeholder="https://keycloak.example.com",
                info="Keycloak authentication server URL"
            )
            keycloak_port = gr.Number(
                label="Keycloak Port",
                value=443,
                precision=0,
                info="Keycloak server port (default: 443)"
            )
            keycloak_realm = gr.Textbox(
                label="Realm",
                value="master",
                info="Keycloak realm name (default: master)"
            )
            keycloak_verify_ssl = gr.Checkbox(
                label="Verify SSL",
                value=False,
                info="Verify SSL certificates for Keycloak (disabled by default for self-signed certs)"
            )
        
        with gr.Tab("🖥️ GCM Server"):
            gr.Markdown("### GCM MCP Server Connection")
            gcm_url = gr.Textbox(
                label="GCM URL",
                placeholder="https://gcm.example.com",
                info="GCM MCP server URL (used for both MCP and authorization)"
            )
            gcm_hostname = gr.Textbox(
                label="Hostname",
                placeholder="gcm-server",
                info="GCM server hostname"
            )
            gcm_verify_ssl = gr.Checkbox(
                label="Verify SSL",
                value=False,
                info="Verify SSL certificates for GCM (disabled by default for self-signed certs)"
            )
        
        with gr.Tab("🔐 Authentication"):
            gr.Markdown("### GCM Authentication Credentials")
            username = gr.Textbox(
                label="Username",
                placeholder="admin",
                info="GCM username"
            )
            password = gr.Textbox(
                label="Password",
                type="password",
                placeholder="••••••••",
                info="GCM user password (stored securely)"
            )
            client_id = gr.Textbox(
                label="Client ID",
                placeholder="gcm-client",
                info="OAuth2 client ID"
            )
            client_secret = gr.Textbox(
                label="Client Secret",
                type="password",
                placeholder="••••••••",
                info="OAuth2 client secret (stored securely)"
            )
        
        with gr.Tab("🤖 WatsonX"):
            gr.Markdown("### WatsonX LLM Configuration")
            watsonx_url = gr.Textbox(
                label="WatsonX URL",
                value="https://us-south.ml.cloud.ibm.com",
                placeholder="https://us-south.ml.cloud.ibm.com",
                info="WatsonX API endpoint URL"
            )
            project_id = gr.Textbox(
                label="Project ID",
                placeholder="12345678-1234-1234-1234-123456789abc",
                info="WatsonX project ID"
            )
            api_key = gr.Textbox(
                label="API Key",
                type="password",
                placeholder="••••••••",
                info="WatsonX API key (stored securely)"
            )
            model = gr.Textbox(
                label="Model",
                value="ibm/granite-13b-chat-v2",
                placeholder="ibm/granite-13b-chat-v2",
                info="WatsonX model identifier (editable - enter any valid model ID)"
            )
            watsonx_verify_ssl = gr.Checkbox(
                label="Verify SSL",
                value=True,
                info="Verify SSL certificates for WatsonX (recommended)"
            )
            gr.Markdown("**Common models:** `ibm/granite-13b-chat-v2`, `ibm/granite-20b-multilingual`, `meta-llama/llama-3-70b-instruct`, `ibm/granite-3-8b-instruct`")
            
            gr.Markdown("### LLM Generation Parameters")
            gr.Markdown("*Advanced settings for controlling LLM behavior. Defaults are optimized for tool selection accuracy.*")
            
            temperature = gr.Slider(
                label="Temperature",
                minimum=0.0,
                maximum=2.0,
                value=0.1,
                step=0.1,
                info="Sampling temperature (0.0=deterministic, 2.0=creative). Lower values improve tool selection accuracy."
            )
            max_tokens = gr.Slider(
                label="Max Tokens",
                minimum=256,
                maximum=8192,
                value=4096,
                step=256,
                info="Maximum tokens in response. Higher values allow complete reasoning."
            )
            top_p = gr.Slider(
                label="Top P",
                minimum=0.0,
                maximum=1.0,
                value=0.95,
                step=0.05,
                info="Nucleus sampling threshold. Controls diversity of token selection."
            )
            top_k = gr.Slider(
                label="Top K",
                minimum=1,
                maximum=100,
                value=40,
                step=1,
                info="Top-k sampling. Limits token selection to top k candidates."
            )
            decoding_method = gr.Radio(
                label="Decoding Method",
                choices=["greedy", "sample"],
                value="greedy",
                info="Decoding method: 'greedy' (deterministic) or 'sample' (stochastic)"
            )
        
        with gr.Tab("⚙️ Agent Settings"):
            gr.Markdown("### Agent Behavior Configuration")
            discovery_mode = gr.Checkbox(
                label="Discovery Mode",
                value=True,
                info="Enable dynamic tool discovery (recommended)"
            )
            max_iterations = gr.Slider(
                label="Max Iterations",
                minimum=1,
                maximum=50,
                value=10,
                step=1,
                info="Maximum number of agent reasoning steps"
            )
            timeout = gr.Slider(
                label="Timeout (seconds)",
                minimum=60,
                maximum=600,
                value=300,
                step=30,
                info="Maximum time for agent operations"
            )
        
        gr.Markdown("---")
        
        with gr.Row():
            save_btn = gr.Button("💾 Save Configuration", variant="primary", scale=2)
            test_btn = gr.Button("🔌 Test Connection", variant="secondary", scale=2)
            load_btn = gr.Button("📥 Load Configuration", variant="secondary", scale=1)
            clear_btn = gr.Button("🗑️ Clear All", variant="stop", scale=1)
        
        status = gr.Textbox(
            label="Status",
            interactive=False,
            placeholder="Ready to configure...",
            lines=2
        )
        
        # Event handlers
        save_btn.click(
            fn=save_configuration,
            inputs=[
                keycloak_url, keycloak_port, keycloak_realm, keycloak_verify_ssl,
                gcm_url, gcm_hostname, gcm_verify_ssl,
                username, password, client_id, client_secret,
                watsonx_url, project_id, api_key, model, watsonx_verify_ssl,
                temperature, max_tokens, top_p, top_k, decoding_method,
                discovery_mode, max_iterations, timeout
            ],
            outputs=status
        )
        
        test_btn.click(
            fn=test_connection,
            inputs=[
                keycloak_url, keycloak_port, keycloak_realm, keycloak_verify_ssl,
                username, password, client_id, client_secret
            ],
            outputs=status
        )
        
        load_btn.click(
            fn=load_configuration,
            outputs=[
                keycloak_url, keycloak_port, keycloak_realm, keycloak_verify_ssl,
                gcm_url, gcm_hostname, gcm_verify_ssl,
                username, password, client_id, client_secret,
                watsonx_url, project_id, api_key, model, watsonx_verify_ssl,
                temperature, max_tokens, top_p, top_k, decoding_method,
                discovery_mode, max_iterations, timeout,
                status
            ]
        )
        
        clear_btn.click(
            fn=clear_configuration,
            outputs=status
        )
    
    logger.info("Configuration UI created successfully")
    return config_ui


__all__ = ["create_config_ui"]
