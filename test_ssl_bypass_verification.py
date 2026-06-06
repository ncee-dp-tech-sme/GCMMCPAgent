#!/usr/bin/env python3
"""
Test script to verify SSL bypass is actually working.

This script creates httpx clients and checks if SSL verification is truly disabled.
"""

import sys
import asyncio

print("=" * 80)
print("SSL BYPASS VERIFICATION TEST")
print("=" * 80)
print()

# Import gcm_agent first (applies SSL bypass)
print("Step 1: Import gcm_agent (applies SSL bypass)")
import gcm_agent
print("  ✓ gcm_agent imported")
print()

# Import httpx
print("Step 2: Import httpx and check patch")
import httpx

# Check if our patch is applied
print(f"  httpx.AsyncClient.__init__.__name__ = {httpx.AsyncClient.__init__.__name__}")
print()

# Test SSL bypass
print("Step 3: Test SSL bypass with actual client creation")

async def test_clients():
    """Test different client configurations."""
    
    # Test 1: Client without verify parameter (should use SSL bypass)
    print("  Test 1: Client without verify parameter")
    try:
        client1 = httpx.AsyncClient()
        # Check the actual verify setting
        print(f"    client._transport = {type(client1._transport)}")
        if hasattr(client1._transport, '_pool'):
            pool = client1._transport._pool
            print(f"    pool._ssl_context = {pool._ssl_context}")
            if pool._ssl_context:
                print(f"    check_hostname = {pool._ssl_context.check_hostname}")
                print(f"    verify_mode = {pool._ssl_context.verify_mode}")
        await client1.aclose()
        print("    ✓ Client created successfully")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()
    
    # Test 2: Client with verify=False (explicit)
    print("  Test 2: Client with verify=False (explicit)")
    try:
        client2 = httpx.AsyncClient(verify=False)
        if hasattr(client2._transport, '_pool'):
            pool = client2._transport._pool
            print(f"    pool._ssl_context = {pool._ssl_context}")
        await client2.aclose()
        print("    ✓ Client created successfully")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()
    
    # Test 3: Client with verify=True (should enable SSL)
    print("  Test 3: Client with verify=True (should enable SSL)")
    try:
        client3 = httpx.AsyncClient(verify=True)
        if hasattr(client3._transport, '_pool'):
            pool = client3._transport._pool
            print(f"    pool._ssl_context = {pool._ssl_context}")
            if pool._ssl_context:
                print(f"    check_hostname = {pool._ssl_context.check_hostname}")
                print(f"    verify_mode = {pool._ssl_context.verify_mode}")
        await client3.aclose()
        print("    ✓ Client created successfully")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    print()
    
    # Test 4: Try to connect to a self-signed cert endpoint
    print("  Test 4: Try to connect to self-signed cert (should succeed with bypass)")
    try:
        # Use a known self-signed cert endpoint (badssl.com)
        client4 = httpx.AsyncClient()
        response = await client4.get("https://self-signed.badssl.com/", timeout=5.0)
        print(f"    ✓ Connection succeeded! Status: {response.status_code}")
        await client4.aclose()
    except httpx.ConnectError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            print(f"    ✗ SSL verification FAILED - bypass not working!")
            print(f"    Error: {e}")
        else:
            print(f"    ✗ Connection error (not SSL): {e}")
    except Exception as e:
        print(f"    ✗ Unexpected error: {e}")

asyncio.run(test_clients())

print()
print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

# Made with Bob
