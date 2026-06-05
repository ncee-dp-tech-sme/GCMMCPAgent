#!/usr/bin/env python3
"""Test script to verify logging configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded .env from {env_path}")
else:
    print(f"✗ No .env file found at {env_path}")

# Print logging configuration
print("\n=== Logging Configuration ===")
print(f"LOG_LEVEL: {os.getenv('LOG_LEVEL', 'NOT SET')}")
print(f"LOG_TO_FILE: {os.getenv('LOG_TO_FILE', 'NOT SET')}")
print(f"LOG_DIR: {os.getenv('LOG_DIR', 'NOT SET')}")

# Test logger
print("\n=== Testing Logger ===")
from gcm_agent.utils.logger import get_auth_logger, get_mcp_logger

auth_logger = get_auth_logger()
mcp_logger = get_mcp_logger()

print(f"Auth logger level: {auth_logger.level} (10=DEBUG, 20=INFO)")
print(f"Auth logger handlers: {len(auth_logger.handlers)}")
for i, handler in enumerate(auth_logger.handlers):
    print(f"  Handler {i}: {type(handler).__name__}")

print(f"\nMCP logger level: {mcp_logger.level}")
print(f"MCP logger handlers: {len(mcp_logger.handlers)}")

# Test logging
print("\n=== Test Log Messages ===")
auth_logger.debug("This is a DEBUG message")
auth_logger.info("This is an INFO message")
auth_logger.warning("This is a WARNING message")
auth_logger.error("This is an ERROR message")

# Check if logs directory was created
logs_dir = Path(os.getenv('LOG_DIR', 'logs'))
if logs_dir.exists():
    print(f"\n✓ Logs directory exists: {logs_dir.absolute()}")
    log_files = list(logs_dir.glob("*.log"))
    if log_files:
        print(f"✓ Found {len(log_files)} log file(s):")
        for log_file in log_files:
            size = log_file.stat().st_size
            print(f"  - {log_file.name} ({size} bytes)")
    else:
        print("✗ No log files found in logs directory")
else:
    print(f"\n✗ Logs directory does not exist: {logs_dir.absolute()}")

print("\n=== Test Complete ===")

# Made with Bob
