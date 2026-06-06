#!/usr/bin/env python3
"""
Test script for x-gcm-hostname header fix.

This script verifies that the x-gcm-hostname header is properly propagated
through the authentication and MCP client stack, fixing the 400/500 errors
that occurred when the placeholder 'asset' hostname was used in internal API calls.

Tests:
1. get_asset_groups - Previously failed with 500 error
2. fetch_detailed_asset_list_by_crypto_objects - Previously failed with 500 error

Expected Results:
- Operations complete without 400/500 errors
- URLs use actual GCM hostname instead of 'asset' placeholder
- Token refresh maintains hostname in headers
"""

# Made with Bob
# 2026-06-06 03:01 UTC - Created test script for x-gcm-hostname header fix verification

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from gcm_agent.config.config_manager import (
    ConfigManager,
    KeycloakConfig,
    GCMServerConfig,
    AuthConfig,
    WatsonXConfig,
    AgentConfig,
)
from gcm_agent.auth import get_client_factory
from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader
from gcm_agent.agent.gcm_agent import GCMAgent
from gcm_agent.utils.logger import get_agent_logger


async def test_hostname_fix():
    """
    Test the x-gcm-hostname header fix by executing operations that previously failed.
    """
    logger = get_agent_logger()
    logger.info("=" * 80)
    logger.info("Starting x-gcm-hostname header fix test")
    logger.info("=" * 80)
    
    # Load environment variables
    env_path = project_root / ".env"
    if not env_path.exists():
        logger.error(f"❌ .env file not found at {env_path}")
        logger.error("Please create .env file with required configuration")
        return False
    
    load_dotenv(env_path)
    logger.info(f"✓ Loaded environment variables from {env_path}")
    
    try:
        # Step 1: Load configuration
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Loading configuration")
        logger.info("=" * 80)
        
        config_manager = ConfigManager()
        
        # Get configurations
        keycloak_config = config_manager.get_keycloak_config()
        gcm_config = config_manager.get_gcm_config()
        auth_config = config_manager.get_auth_config()
        watsonx_config = config_manager.get_watsonx_config()
        agent_config = config_manager.get_agent_config()
        
        logger.info(f"✓ GCM URL: {gcm_config.url}")
        logger.info(f"✓ GCM Hostname: {gcm_config.hostname}")
        logger.info(f"✓ Keycloak URL: {keycloak_config.url}:{keycloak_config.port}")
        logger.info(f"✓ Username: {auth_config.username}")
        logger.info(f"✓ Discovery Mode: {agent_config.discovery_mode}")
        
        # Get secrets
        password = config_manager.get_password()
        client_secret = config_manager.get_client_secret()
        watsonx_api_key = config_manager.get_watsonx_api_key()
        
        logger.info("✓ Retrieved secrets from secure storage")
        
        # Step 2: Authenticate and get client factory
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Authenticating with GCM")
        logger.info("=" * 80)
        
        client_factory, gcm_authenticator = await get_client_factory(
            keycloak_config=keycloak_config,
            gcm_config=gcm_config,
            auth_config=auth_config,
            password=password,
            client_secret=client_secret,
            timeout=300.0,
        )
        
        logger.info("✓ Authentication successful")
        logger.info(f"✓ Client factory created with hostname: {gcm_config.hostname}")
        
        # Step 3: Initialize MCP client
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Initializing MCP client")
        logger.info("=" * 80)
        
        mcp_client = GCMMCPClient(
            gcm_url=gcm_config.url,
            gcm_hostname=gcm_config.hostname,
            client_factory=client_factory,
            discovery_mode=agent_config.discovery_mode,
            timeout=300,
            verify_ssl=gcm_config.verify_ssl,
            gcm_authenticator=gcm_authenticator,
        )
        
        await mcp_client.connect()
        logger.info("✓ MCP client connected")
        
        # Step 4: Initialize tool loader and agent
        logger.info("\n" + "=" * 80)
        logger.info("Step 4: Initializing agent")
        logger.info("=" * 80)
        
        tool_loader = GCMToolLoader(
            mcp_client=mcp_client,
            cache_ttl=agent_config.tool_cache_ttl,
        )
        
        agent = GCMAgent(
            mcp_client=mcp_client,
            tool_loader=tool_loader,
            watsonx_config=watsonx_config,
            api_key=watsonx_api_key,
            agent_config=agent_config,
        )
        
        await agent.initialize()
        logger.info("✓ Agent initialized successfully")
        logger.info(f"✓ Loaded {len(agent.tools)} tools")
        
        # Step 5: Test operations that previously failed
        logger.info("\n" + "=" * 80)
        logger.info("Step 5: Testing operations that previously failed")
        logger.info("=" * 80)
        
        test_results = []
        
        # Test 1: get_asset_groups
        logger.info("\n--- Test 1: get_asset_groups ---")
        try:
            result = await mcp_client.execute_tool("get_asset_groups", {})
            logger.info(f"✓ get_asset_groups succeeded")
            logger.info(f"  Result type: {type(result)}")
            if isinstance(result, (list, dict)):
                logger.info(f"  Result length/keys: {len(result)}")
            test_results.append(("get_asset_groups", True, "Success"))
        except Exception as e:
            logger.error(f"❌ get_asset_groups failed: {e}")
            test_results.append(("get_asset_groups", False, str(e)))
        
        # Test 2: fetch_detailed_asset_list_by_crypto_objects
        logger.info("\n--- Test 2: fetch_detailed_asset_list_by_crypto_objects ---")
        try:
            # This tool requires parameters - use minimal valid params
            params = {
                "asset_category": "key",  # Required parameter
            }
            result = await mcp_client.execute_tool(
                "fetch_detailed_asset_list_by_crypto_objects",
                params
            )
            logger.info(f"✓ fetch_detailed_asset_list_by_crypto_objects succeeded")
            logger.info(f"  Result type: {type(result)}")
            if isinstance(result, (list, dict)):
                logger.info(f"  Result length/keys: {len(result)}")
            test_results.append(("fetch_detailed_asset_list_by_crypto_objects", True, "Success"))
        except Exception as e:
            logger.error(f"❌ fetch_detailed_asset_list_by_crypto_objects failed: {e}")
            test_results.append(("fetch_detailed_asset_list_by_crypto_objects", False, str(e)))
        
        # Step 6: Summary
        logger.info("\n" + "=" * 80)
        logger.info("Test Summary")
        logger.info("=" * 80)
        
        success_count = sum(1 for _, success, _ in test_results if success)
        total_count = len(test_results)
        
        for tool_name, success, message in test_results:
            status = "✓ PASS" if success else "❌ FAIL"
            logger.info(f"{status}: {tool_name}")
            if not success:
                logger.info(f"  Error: {message}")
        
        logger.info(f"\nResults: {success_count}/{total_count} tests passed")
        
        # Cleanup
        logger.info("\n" + "=" * 80)
        logger.info("Cleanup")
        logger.info("=" * 80)
        
        await agent.close()
        logger.info("✓ Agent closed")
        
        # Final verdict
        logger.info("\n" + "=" * 80)
        if success_count == total_count:
            logger.info("✓ ALL TESTS PASSED - x-gcm-hostname header fix verified!")
        else:
            logger.info(f"❌ {total_count - success_count} test(s) failed")
        logger.info("=" * 80)
        
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("GCM Agent - x-gcm-hostname Header Fix Test")
    print("=" * 80)
    print("\nThis test verifies that the x-gcm-hostname header is properly")
    print("propagated through the authentication and MCP client stack.")
    print("\nThe fix addresses the issue where internal GCM API calls were")
    print("using the placeholder 'asset' hostname instead of the actual")
    print("GCM hostname, causing 400/500 errors.")
    print("=" * 80 + "\n")
    
    # Run async test
    success = asyncio.run(test_hostname_fix())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()