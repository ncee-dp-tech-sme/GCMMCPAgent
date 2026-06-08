#!/usr/bin/env python3
"""
Test script to diagnose SSL bypass import order issue.

This script verifies whether the SSL bypass patch in gcm_agent/__init__.py
is being applied before httpx is imported by langchain_mcp_adapters.
"""

import sys
import importlib

print("=" * 80)
print("SSL BYPASS IMPORT ORDER DIAGNOSTIC")
print("=" * 80)
print()

# Track what's imported
print("Step 1: Check initial state")
print(f"  httpx in sys.modules: {'httpx' in sys.modules}")
print(f"  langchain_mcp_adapters in sys.modules: {'langchain_mcp_adapters' in sys.modules}")
print(f"  gcm_agent in sys.modules: {'gcm_agent' in sys.modules}")
print()

# Import gcm_agent (should apply SSL bypass patch)
print("Step 2: Import gcm_agent (should apply SSL bypass)")
import gcm_agent
print(f"  ✓ gcm_agent imported")
print(f"  httpx in sys.modules: {'httpx' in sys.modules}")
print()

# Check if SSL bypass was applied
print("Step 3: Verify SSL bypass patch")
import httpx
original_init = httpx.AsyncClient.__init__

# Check if it's our patched version
if hasattr(original_init, '__name__') and 'ssl_bypass' in original_init.__name__:
    print(f"  ✓ SSL bypass patch APPLIED")
else:
    print(f"  ✗ SSL bypass patch NOT APPLIED")
    print(f"  Current __init__: {original_init}")
print()

# Now import langchain_mcp_adapters
print("Step 4: Import langchain_mcp_adapters")
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    print(f"  ✓ langchain_mcp_adapters imported")
except Exception as e:
    print(f"  ✗ Failed to import: {e}")
print()

# Test if SSL bypass works
print("Step 5: Test SSL bypass functionality")
import asyncio

async def test_ssl_bypass():
    """Test if httpx.AsyncClient respects SSL bypass."""
    # Create client without explicit verify parameter
    client1 = httpx.AsyncClient()
    print(f"  Client without verify param: verify={client1._transport._pool._ssl_context is None or not client1._transport._pool._ssl_context.check_hostname}")
    await client1.aclose()
    
    # Create client with verify=True (should override)
    client2 = httpx.AsyncClient(verify=True)
    print(f"  Client with verify=True: verify={client2._transport._pool._ssl_context is not None and client2._transport._pool._ssl_context.check_hostname}")
    await client2.aclose()
    
    # Create client with verify=False (explicit)
    client3 = httpx.AsyncClient(verify=False)
    print(f"  Client with verify=False: verify={client3._transport._pool._ssl_context is None or not client3._transport._pool._ssl_context.check_hostname}")
    await client3.aclose()

try:
    asyncio.run(test_ssl_bypass())
except Exception as e:
    print(f"  ✗ Test failed: {e}")

print()
print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)

# Made with Bob
