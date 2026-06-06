#!/usr/bin/env python3
"""
Test script to verify the async/await fix for the execute tool.

This script validates that the fix in gcm_agent/mcp/client.py correctly
handles coroutine results from tool.ainvoke(), specifically for the 'execute'
tool in discovery mode.

The fix (lines 444-449 in client.py) detects and awaits coroutine results
to prevent TypeError: 'coroutine' object is not subscriptable.

Run: python test_execute_tool_fix.py
"""

# Made with Bob
# 2026-06-06 04:39 UTC - Created test script to verify async/await fix for execute tool

import asyncio
import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_execute_tool_fix():
    """Test the execute tool with discovery mode to verify async/await fix."""
    print("=" * 70)
    print("Execute Tool Async/Await Fix Verification")
    print("=" * 70)
    print()
    
    try:
        # Import required modules
        print("Step 1: Importing modules...")
        from gcm_agent.auth import get_client_factory
        from gcm_agent.mcp import create_gcm_mcp_client, GCMToolLoader
        from gcm_agent.config import get_config_manager
        from gcm_agent.config.storage import get_storage
        from gcm_agent.utils.logger import get_mcp_logger
        print("✓ Modules imported successfully")
        print()
        
        # Load configuration
        print("Step 2: Loading configuration from storage...")
        config_manager = get_config_manager()
        
        # Load configuration
        if not config_manager.load_config():
            print("✗ No configuration found. Please run the UI to configure the agent first.")
            print("  Run: python app.py")
            return False
        
        gcm_config = config_manager.get_gcm_config()
        keycloak_config = config_manager.get_keycloak_config()
        auth_config = config_manager.get_auth_config()
        agent_config = config_manager.get_agent_config()
        
        print(f"  GCM URL: {gcm_config.url}")
        print(f"  GCM Hostname: {gcm_config.hostname}")
        print(f"  Discovery Mode: {agent_config.discovery_mode}")
        print("✓ Configuration loaded")
        print()
        
        # Get credentials from secure storage
        print("Step 3: Retrieving credentials from secure storage...")
        storage = get_storage()
        password = storage.get_credential("password")
        client_secret = storage.get_credential("client_secret")
        
        if not password or not client_secret:
            print("✗ Credentials not found in secure storage")
            print("  Please run the UI to configure credentials first")
            return False
        
        print("✓ Credentials retrieved")
        print()
        
        # Override to enable discovery mode for this test
        if not agent_config.discovery_mode:
            print("Step 4: Enabling discovery mode for test...")
            agent_config.discovery_mode = True
            print("✓ Discovery mode enabled")
            print()
        else:
            print("Step 4: Discovery mode already enabled")
            print()
        
        # Authenticate
        print("Step 5: Authenticating with GCM...")
        client_factory, authenticator = await get_client_factory(
            keycloak_config=keycloak_config,
            gcm_config=gcm_config,
            auth_config=auth_config,
            password=password,
            client_secret=client_secret
        )
        print("✓ Authentication successful")
        print()
        
        # Create MCP client
        print("Step 6: Creating MCP client...")
        mcp_client = await create_gcm_mcp_client(
            gcm_config=gcm_config,
            client_factory=client_factory,
            discovery_mode=True,  # Force discovery mode
            authenticator=authenticator
        )
        print("✓ MCP client created")
        print()
        
        # Connect to MCP server
        print("Step 7: Connecting to MCP server...")
        await mcp_client.connect()
        print("✓ Connected to MCP server")
        print()
        
        # Load tools
        print("Step 8: Loading tools...")
        tool_loader = GCMToolLoader(mcp_client)
        tools = await tool_loader.load_tools()
        print(f"✓ Loaded {len(tools)} tools")
        
        # Find the execute tool
        execute_tool = None
        for tool in tools:
            if tool.name == "execute":
                execute_tool = tool
                break
        
        if not execute_tool:
            print("✗ Execute tool not found in discovery mode")
            print("  Available tools:", [t.name for t in tools])
            return False
        
        print(f"✓ Found execute tool: {execute_tool.name}")
        print()
        
        # Test the execute tool
        print("Step 9: Testing execute tool with async/await fix...")
        print("  Executing simple workflow: list_tools with tag 'asset'")
        
        # Create a simple workflow that uses list_tools
        workflow = {
            "tool_name": "list_tools",
            "arguments": {
                "tag": "asset"
            }
        }
        
        try:
            # This should trigger the async/await fix if the tool returns a coroutine
            result = await mcp_client.execute_tool("execute", workflow)
            
            # Verify result is not a coroutine object
            import inspect
            if inspect.iscoroutine(result):
                print("✗ FAILED: Result is still a coroutine object!")
                print("  The async/await fix did not work correctly.")
                return False
            
            print("✓ Execute tool returned actual result (not a coroutine)")
            print(f"  Result type: {type(result).__name__}")
            
            # Check if result contains expected data
            if isinstance(result, dict):
                print(f"  Result keys: {list(result.keys())}")
            elif isinstance(result, str):
                print(f"  Result length: {len(result)} characters")
            
            print()
            print("=" * 70)
            print("✓ TEST PASSED: Async/await fix working correctly!")
            print("=" * 70)
            print()
            print("Summary:")
            print("  • Execute tool successfully invoked")
            print("  • Result is not a coroutine object")
            print("  • Async/await fix in client.py (lines 444-449) is working")
            print()
            return True
            
        except TypeError as e:
            if "coroutine" in str(e).lower():
                print(f"✗ FAILED: TypeError with coroutine: {e}")
                print("  The async/await fix did not prevent the error.")
                return False
            else:
                raise
        
        finally:
            # Cleanup
            print("Step 10: Cleaning up...")
            await mcp_client.disconnect()
            print("✓ Disconnected from MCP server")
            print()
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_standard_tool():
    """Test a standard tool to ensure the fix doesn't break normal tools."""
    print("=" * 70)
    print("Standard Tool Verification (Regression Test)")
    print("=" * 70)
    print()
    
    try:
        from gcm_agent.auth import get_client_factory
        from gcm_agent.mcp import create_gcm_mcp_client, GCMToolLoader
        from gcm_agent.config import get_config_manager
        from gcm_agent.config.storage import get_storage
        
        config_manager = get_config_manager()
        if not config_manager.load_config():
            print("✗ No configuration found")
            return False
        
        gcm_config = config_manager.get_gcm_config()
        keycloak_config = config_manager.get_keycloak_config()
        auth_config = config_manager.get_auth_config()
        
        # Get credentials
        storage = get_storage()
        password = storage.get_credential("password")
        client_secret = storage.get_credential("client_secret")
        
        if not password or not client_secret:
            print("✗ Credentials not found")
            return False
        
        print("Authenticating...")
        client_factory, authenticator = await get_client_factory(
            keycloak_config=keycloak_config,
            gcm_config=gcm_config,
            auth_config=auth_config,
            password=password,
            client_secret=client_secret
        )
        
        print("Creating MCP client in standard mode...")
        mcp_client = await create_gcm_mcp_client(
            gcm_config=gcm_config,
            client_factory=client_factory,
            discovery_mode=False,  # Standard mode
            authenticator=authenticator
        )
        
        await mcp_client.connect()
        
        tool_loader = GCMToolLoader(mcp_client)
        tools = await tool_loader.load_tools()
        print(f"Loaded {len(tools)} tools in standard mode")
        
        # Try to execute a simple tool (list_assets)
        if any(t.name == "list_assets" for t in tools):
            print("Testing list_assets tool...")
            result = await mcp_client.execute_tool("list_assets", {
                "asset_category": "key"
            })
            
            import inspect
            if inspect.iscoroutine(result):
                print("✗ FAILED: Standard tool returned coroutine")
                return False
            
            print("✓ Standard tool works correctly")
            print()
        
        await mcp_client.disconnect()
        return True
        
    except Exception as e:
        print(f"✗ Standard tool test failed: {e}")
        return False


def main():
    """Main entry point."""
    print()
    print("Testing async/await fix for execute tool...")
    print()
    
    # Test 1: Execute tool in discovery mode
    success1 = asyncio.run(test_execute_tool_fix())
    
    # Test 2: Standard tool regression test
    success2 = asyncio.run(test_standard_tool())
    
    # Final summary
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Execute tool test: {'PASSED ✓' if success1 else 'FAILED ✗'}")
    print(f"Standard tool test: {'PASSED ✓' if success2 else 'FAILED ✗'}")
    print()
    
    if success1 and success2:
        print("✓ ALL TESTS PASSED")
        print()
        print("The async/await fix is working correctly:")
        print("  • Execute tool returns actual results, not coroutines")
        print("  • Standard tools continue to work normally")
        print("  • No regression introduced by the fix")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print()
        print("Please review the errors above and check:")
        print("  • gcm_agent/mcp/client.py lines 444-449")
        print("  • Tool invocation in execute_tool method")
        sys.exit(1)


if __name__ == "__main__":
    main()