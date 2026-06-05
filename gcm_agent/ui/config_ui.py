"""Gradio-based configuration UI module for collecting and validating GCM agent settings."""

# Made with Bob
# 2026-06-05 22:14 UTC - Initial implementation of configuration UI with secure credential handling

from typing import Tuple, Optional
import gradio as gr

from gcm_agent.config.config_manager import (
    get_config_manager,
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


def load_configuration() -> Tuple[str, str, int, str, bool, str, str, str, str, str, str, bool, int, int, str]:
    """
    Load existing configuration from secure storage.
    
    Returns:
        Tuple of all configuration values for UI fields
    """
    try:
        config_manager = get_config_manager()
        
        # Try to load configuration
        if not config_manager.load_config():
            logger.info("No existing configuration found")
            return ("", "", 443, "master", True, "", "", "", "", "", "ibm/granite-13b-chat-v2", True, 10, 300, "No configuration found. Please enter your settings.")
        
        # Load each section
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
            gcm_config.url,
            gcm_config.hostname,
            gcm_config.keycloak_port,
            gcm_config.realm,
            gcm_config.verify_ssl,
            auth_config.username,
            password,
            auth_config.client_id,
            client_secret,
            watsonx_config.project_id,
            api_key,
            watsonx_config.model,
            agent_config.discovery_mode,
            agent_config.max_iterations,
            agent_config.timeout,
            "✅ Configuration loaded successfully"
        )
        
    except (MissingConfigError, InvalidConfigError) as e:
        logger.warning(f"Configuration incomplete or invalid: {e}")
        return ("", "", 443, "master", True, "", "", "", "", "", "", "ibm/granite-13b-chat-v2", True, 10, 300, f"⚠️ Configuration incomplete: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return ("", "", 443, "master", True, "", "", "", "", "", "", "ibm/granite-13b-chat-v2", True, 10, 300, f"❌ Error loading configuration: {str(e)}")


def save_configuration(
    gcm_url: str,
    gcm_hostname: str,
    keycloak_port: int,
    realm: str,
    verify_ssl: bool,
    username: str,
    password: str,
    client_id: str,
    client_secret: str,
    project_id: str,
    api_key: str,
    model: str,
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
        if not all([gcm_url, gcm_hostname, username, password, client_id, client_secret, project_id, api_key]):
            return "❌ Error: All fields are required"
        
        # Create configuration objects (will validate)
        gcm_config = GCMServerConfig(
            url=gcm_url,
            hostname=gcm_hostname,
            keycloak_port=keycloak_port,
            realm=realm,
            verify_ssl=verify_ssl,
        )
        
        auth_config = AuthConfig(
            username=username,
            client_id=client_id,
        )
        
        watsonx_config = WatsonXConfig(
            project_id=project_id,
            model=model,
        )
        
        agent_config = AgentConfig(
            discovery_mode=discovery_mode,
            max_iterations=max_iterations,
            timeout=timeout,
        )
        
        # Save configurations
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
    gcm_url: str,
    gcm_hostname: str,
    keycloak_port: int,
    realm: str,
    verify_ssl: bool,
    username: str,
    password: str,
    client_id: str,
    client_secret: str,
) -> str:
    """
    Test connection to GCM server with provided credentials.
    
    Args:
        GCM server and authentication parameters
        
    Returns:
        Status message
    """
    try:
        # Validate required fields
        if not all([gcm_url, gcm_hostname, username, password, client_id, client_secret]):
            return "❌ Error: All connection fields are required"
        
        logger.info("Testing connection to GCM server")
        
        # Create auth instance and test connection
        # Build Keycloak URL from GCM URL and port
        keycloak_url = f"{gcm_url.rstrip('/')}:{keycloak_port}"
        
        auth = KeycloakAuthenticator(
            keycloak_url=keycloak_url,
            realm=realm,
            client_id=client_id,
            username=username,
            password=password,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        
        # Attempt to get token
        token = await auth.get_token()
        
        if token:
            logger.info("Connection test successful")
            return "✅ Connection successful! Credentials are valid."
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
    
    with gr.Blocks(title="GCM Agent Configuration", theme=gr.themes.Soft()) as config_ui:
        gr.Markdown("# 🔧 GCM Agent Configuration")
        gr.Markdown("Configure your GCM Agent connection, authentication, and settings.")
        
        with gr.Tab("🖥️ GCM Server"):
            gr.Markdown("### Server Connection Settings")
            gcm_url = gr.Textbox(
                label="GCM URL",
                placeholder="https://gcm.example.com",
                info="Full URL to your GCM server"
            )
            gcm_hostname = gr.Textbox(
                label="Hostname",
                placeholder="gcm-server",
                info="GCM server hostname"
            )
            keycloak_port = gr.Number(
                label="Keycloak Port",
                value=443,
                precision=0,
                info="Port for Keycloak authentication (default: 443)"
            )
            realm = gr.Textbox(
                label="Realm",
                value="master",
                info="Keycloak realm (default: master)"
            )
            verify_ssl = gr.Checkbox(
                label="Verify SSL Certificates",
                value=True,
                info="Enable SSL certificate verification (recommended)"
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
            model = gr.Dropdown(
                label="Model",
                choices=[
                    "ibm/granite-13b-chat-v2",
                    "ibm/granite-20b-multilingual",
                    "meta-llama/llama-3-70b-instruct",
                    "meta-llama/llama-3-1-70b-instruct",
                ],
                value="ibm/granite-13b-chat-v2",
                info="Select the LLM model to use"
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
                gcm_url, gcm_hostname, keycloak_port, realm, verify_ssl,
                username, password, client_id, client_secret,
                project_id, api_key, model,
                discovery_mode, max_iterations, timeout
            ],
            outputs=status
        )
        
        test_btn.click(
            fn=test_connection,
            inputs=[
                gcm_url, gcm_hostname, keycloak_port, realm, verify_ssl,
                username, password, client_id, client_secret
            ],
            outputs=status
        )
        
        load_btn.click(
            fn=load_configuration,
            outputs=[
                gcm_url, gcm_hostname, keycloak_port, realm, verify_ssl,
                username, password, client_id, client_secret,
                project_id, api_key, model,
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
