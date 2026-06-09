#!/usr/bin/env python3
"""Test script to reproduce JSON parsing error in execute tool.

This script tests the failing queries:
1. "get all certificates"
2. "Fetch the policy violations dashboard"

The goal is to capture detailed logs showing where malformed JSON originates.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gcm_agent.config.config_manager import ConfigManager
from gcm_agent.auth import get_client_factory
from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader
from gcm_agent.agent.gcm_agent import GCMAgent
from gcm_agent.utils.logger import get_agent_logger

logger = get_agent_logger()


async def test_json_parsing_error():
    """Test JSON parsing error with failing queries."""
    
    logger.info("=" * 80)
    logger.info("JSON PARSING ERROR TEST")
    logger.info("=" * 80)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        if not config:
            logger.error("No configuration found. Please run the UI to configure the agent.")
            return
        
        # Get client factory with authentication
        logger.info("Setting up authentication...")
        client_factory = await get_client_factory(
            gcm_config=config.gcm,
            keycloak_config=config.keycloak
        )
        
        # Create MCP client
        logger.info("Creating MCP client...")
        mcp_client = GCMMCPClient(
            gcm_url=config.gcm.url,
            gcm_hostname=config.gcm.hostname,
            client_factory=client_factory,
            discovery_mode=config.agent.discovery_mode,
            timeout=config.agent.timeout,
            verify_ssl=config.gcm.verify_ssl,
        )
        
        # Connect to MCP server
        logger.info("Connecting to MCP server...")
        await mcp_client.connect()
        
        # Create tool loader
        logger.info("Creating tool loader...")
        tool_loader = GCMToolLoader(mcp_client)
        
        # Create agent
        logger.info("Creating agent...")
        from gcm_agent.config.config_manager import LLMProviderConfig
        
        if config.llm.provider == "watsonx":
            llm_config = LLMProviderConfig(
                provider="watsonx",
                watsonx_config=config.llm.watsonx,
                watsonx_api_key=os.getenv("LLM_WATSONX_API_KEY"),
            )
        else:
            llm_config = LLMProviderConfig(
                provider="openai",
                openai_config=config.llm.openai,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
            )
        
        agent = GCMAgent(
            mcp_client=mcp_client,
            tool_loader=tool_loader,
            agent_config=config.agent,
            llm_config=llm_config,
        )
        
        # Initialize agent
        logger.info("Initializing agent...")
        await agent.initialize()
        
        # Test queries that cause JSON parsing errors
        test_queries = [
            "get all certificates",
            "Fetch the policy violations dashboard",
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info("=" * 80)
            logger.info(f"TEST {i}/{len(test_queries)}: {query}")
            logger.info("=" * 80)
            
            try:
                response = await agent.chat(query)
                logger.info(f"Response: {response}")
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
            
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("TEST COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    asyncio.run(test_json_parsing_error())

# Made with Bob
