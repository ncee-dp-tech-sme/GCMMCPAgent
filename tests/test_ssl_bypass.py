"""Test script to verify SSL bypass is applied at module import time.

This script verifies that:
1. The SSL bypass patch is applied when importing gcm_agent
2. httpx.AsyncClient instances are created with verify=False by default
3. The patch works for both explicit and implicit verify parameter usage
"""

import sys
import asyncio


async def test_ssl_bypass():
    """Test that SSL bypass is applied correctly."""
    print("=" * 70)
    print("Testing SSL Bypass at Module Import Time")
    print("=" * 70)
    
    # Test 1: Import gcm_agent and verify patch is applied
    print("\n[Test 1] Importing gcm_agent module...")
    import gcm_agent
    print("✓ gcm_agent imported successfully")
    
    # Test 2: Verify httpx.AsyncClient has been patched
    print("\n[Test 2] Checking if httpx.AsyncClient is patched...")
    import httpx
    
    # Check if the __init__ method has been replaced
    if httpx.AsyncClient.__init__.__name__ == '_ssl_bypass_init':
        print("✓ httpx.AsyncClient.__init__ is patched with _ssl_bypass_init")
    else:
        print(f"✗ httpx.AsyncClient.__init__ name: {httpx.AsyncClient.__init__.__name__}")
        return False
    
    # Test 3: Create client without verify parameter
    print("\n[Test 3] Creating AsyncClient without verify parameter...")
    async with httpx.AsyncClient() as client:
        # Access the internal _verify attribute to check if SSL is disabled
        if hasattr(client, '_verify'):
            verify_value = client._verify
            print(f"  Client._verify = {verify_value}")
            if verify_value is False:
                print("✓ SSL verification is disabled (verify=False)")
            else:
                print(f"✗ SSL verification is enabled (verify={verify_value})")
                return False
        else:
            print("  Note: Cannot directly access _verify attribute")
    
    # Test 4: Create client with verify=None
    print("\n[Test 4] Creating AsyncClient with verify=None...")
    async with httpx.AsyncClient(verify=None) as client:
        if hasattr(client, '_verify'):
            verify_value = client._verify
            print(f"  Client._verify = {verify_value}")
            if verify_value is False:
                print("✓ SSL verification is disabled (verify=False)")
            else:
                print(f"✗ SSL verification is enabled (verify={verify_value})")
                return False
    
    # Test 5: Verify explicit verify=True still works
    print("\n[Test 5] Creating AsyncClient with verify=True...")
    async with httpx.AsyncClient(verify=True) as client:
        if hasattr(client, '_verify'):
            verify_value = client._verify
            print(f"  Client._verify = {verify_value}")
            if verify_value is True:
                print("✓ SSL verification is enabled (verify=True) - explicit override works")
            else:
                print(f"✗ Expected verify=True but got {verify_value}")
                return False
    
    print("\n" + "=" * 70)
    print("All SSL bypass tests passed! ✓")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ssl_bypass())
    sys.exit(0 if success else 1)

# Made with Bob
