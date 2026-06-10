#!/usr/bin/env python3
"""Convenience script to run the WatsonX Orchestrate API server.

Made with Bob
2026-06-10 02:48 UTC - Initial implementation of server run script
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from watsonxorch.api import run_server
from watsonxorch.config import OrchestrateConfig


def main():
    """Run the WatsonX Orchestrate API server."""
    parser = argparse.ArgumentParser(
        description="Run WatsonX Orchestrate API server for GCM Agent"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Server host address (default: from env or 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: from env or 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    args = parser.parse_args()
    
    # Load config from environment
    config = OrchestrateConfig.from_env()
    
    # Override with command-line arguments
    host = args.host or config.host
    port = args.port or config.port
    
    print(f"Starting WatsonX Orchestrate API server on {host}:{port}")
    print(f"Auto-reload: {'enabled' if args.reload else 'disabled'}")
    print(f"Log level: {config.log_level}")
    print(f"CORS: {'enabled' if config.cors_enabled else 'disabled'}")
    print("\nAPI Documentation:")
    print(f"  - Swagger UI: http://{host}:{port}/docs")
    print(f"  - ReDoc: http://{host}:{port}/redoc")
    print(f"  - Health Check: http://{host}:{port}/health")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        run_server(host=host, port=port, reload=args.reload)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
