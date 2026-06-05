"""
GCM Agent Application

Main entry point for the GCM Agent with configuration and chat interfaces.
"""

# Made with Bob
# 2026-06-05 22:16 UTC - Initial implementation of main application entry point

import gradio as gr

from gcm_agent.ui import create_config_ui, create_chat_ui
from gcm_agent.utils.logger import get_ui_logger


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
            theme=gr.themes.Soft(),
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
            server_name="0.0.0.0",  # Listen on all interfaces
            server_port=7860,        # Default Gradio port
            share=False,             # Don't create public link
            show_error=True,         # Show detailed errors in UI
            favicon_path=None,       # Use default favicon
            show_api=False,          # Don't show API docs
        )
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        raise


if __name__ == "__main__":
    main()