"""
GCM Agent Application

Main entry point for the GCM Agent with configuration and chat interfaces.
"""

# Made with Bob
# 2026-06-06 01:08 UTC - Moved SSL bypass to application startup BEFORE any imports to fix SSL verification errors
# 2026-06-05 22:16 UTC - Initial implementation of main application entry point
# 2026-06-05 22:48 UTC - Removed show_api parameter (not supported in Gradio 6.0), changed server to listen on 127.0.0.1 for security
# 2026-06-05 21:38 UTC - Added dotenv loading for environment variables including logging configuration

# ============================================================================
# SSL BYPASS - MUST BE APPLIED AT STARTUP BEFORE ANY OTHER IMPORTS
# ============================================================================
# This section patches httpx.AsyncClient at the very start of the application
# to ensure ALL httpx clients (including those created by MCP library) have
# SSL verification disabled for self-signed certificates.
# This MUST be done before importing any gcm_agent modules or MCP libraries.
# ============================================================================

import httpx
import ssl

# Store original httpx.AsyncClient.__init__ before any modifications
_original_httpx_init = httpx.AsyncClient.__init__


def _global_ssl_bypass_init(self, *args, **kwargs):
    """
    Global SSL bypass for self-signed certificates.
    
    Patches httpx.AsyncClient.__init__ to disable SSL verification by default.
    If verify is not explicitly set to True, it will be set to False.
    """
    # If verify not explicitly set to True, disable it
    if 'verify' not in kwargs:
        kwargs['verify'] = False
    elif kwargs.get('verify') is None:
        kwargs['verify'] = False
    
    return _original_httpx_init(self, *args, **kwargs)


# Apply patch GLOBALLY before any other imports
httpx.AsyncClient.__init__ = _global_ssl_bypass_init

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# NOW import everything else - MCP and httpx clients will use our patched version
import os
from pathlib import Path
from dotenv import load_dotenv
import gradio as gr

from gcm_agent.ui import create_config_ui, create_chat_ui
from gcm_agent.utils.logger import get_ui_logger

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    print(f"No .env file found at {env_path}, using system environment variables")


logger = get_ui_logger()


def create_app() -> gr.TabbedInterface:
    """
    Create the main GCM Agent application.
    
    Combines configuration and chat interfaces into a tabbed layout.
    
    Returns:
        Gradio TabbedInterface with configuration and chat tabs
    """
    logger.info("Creating GCM Agent application")
    
    try:
        # Create individual UIs
        config_ui = create_config_ui()
        chat_ui = create_chat_ui()
        
        # Combine into tabbed interface
        app = gr.TabbedInterface(
            [config_ui, chat_ui],
            ["⚙️ Configuration", "💬 Chat"],
            title="GCM Agent - IBM Guardium Cryptography Manager Assistant",
        )
        
        logger.info("GCM Agent application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create application: {e}")
        raise


def main():
    """
    Main entry point for the application.
    
    Launches the Gradio interface on the specified host and port.
    """
    logger.info("Starting GCM Agent application")
    
    try:
        app = create_app()
        
        # Launch the application
        app.launch(
            server_name="127.0.0.1",  # Listen on localhost only (security best practice)
            server_port=7860,         # Default Gradio port
            share=False,              # Don't create public link
            show_error=True,          # Show detailed errors in UI
            favicon_path=None,        # Use default favicon
            theme=gr.themes.Soft(),   # Apply theme at launch
        )
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        raise


if __name__ == "__main__":
    main()