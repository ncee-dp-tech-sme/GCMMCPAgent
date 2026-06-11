#!/usr/bin/env python3
"""
Test script to verify Keycloak SSL bypass fix.

This test verifies that KeycloakAuthenticator respects the module-level SSL bypass
patch when verify_ssl=False, fixing the intermittent SSL certificate verification errors.

Root Cause:
- keycloak_auth.py was explicitly passing verify=self.verify_ssl to httpx.AsyncClient()
- When verify_ssl=True (default), this overrode the module-level SSL bypass patch
- Result: Intermittent SSL errors depending on which code path created the client

The Fix:
- Changed get_token() and refresh_token() to only pass verify=True when verify_ssl=True
- When verify_ssl=False, no verify parameter is passed, allowing module-level patch to apply
- Pattern matches gcm_auth.py implementation
"""

import asyncio
import sys
from unittest.mock import Mock, patch, AsyncMock

# Import gcm_agent first to apply SSL bypass patch
import gcm_agent
from gcm_agent.auth.keycloak_auth import KeycloakAuthenticator


async def test_keycloak_ssl_bypass():
    """Test that KeycloakAuthenticator respects module-level SSL bypass."""
    
    print("=" * 80)
    print("Testing Keycloak SSL Bypass Fix")
    print("=" * 80)
    
    # Test 1: Verify module-level SSL bypass is active
    print("\n[Test 1] Verifying module-level SSL bypass is active...")
    import httpx
    
    if httpx.AsyncClient.__init__.__name__ == '_ssl_bypass_init':
        print("✓ Module-level SSL bypass patch is active")
    else:
        print("✗ Module-level SSL bypass patch is NOT active")
        return False
    
    # Test 2: Test KeycloakAuthenticator with verify_ssl=False
    print("\n[Test 2] Testing KeycloakAuthenticator with verify_ssl=False...")
    
    # Track httpx.AsyncClient calls
    client_calls = []
    original_init = httpx.AsyncClient.__init__
    
    def track_client_init(self, *args, **kwargs):
        client_calls.append({
            'args': args,
            'kwargs': kwargs,
            'verify': kwargs.get('verify', 'NOT_SET')
        })
        return original_init(self, *args, **kwargs)
    
    with patch.object(httpx.AsyncClient, '__init__', track_client_init):
        # Create authenticator with verify_ssl=False
        auth = KeycloakAuthenticator(
            keycloak_url="https://keycloak.example.com:443",
            realm="master",
            client_id="test-client",
            username="testuser",
            password="testpass",  # HashiCorpIgnore
            client_secret="test-secret",  # HashiCorpIgnore
            verify_ssl=False  # Should NOT pass verify parameter
        )
        
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "refresh_token": "refresh_token_456",
            "expires_in": 300
        }
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock, return_value=mock_response):
            try:
                # Call get_token - should NOT pass verify parameter
                token = await auth.get_token()
                print(f"  ✓ get_token() succeeded, token: {token[:20]}...")
                
                # Check that verify was NOT passed (module-level patch should apply)
                get_token_call = client_calls[-1]
                if get_token_call['verify'] == 'NOT_SET':
                    print(f"  ✓ get_token() did NOT pass verify parameter (correct)")
                else:
                    print(f"  ✗ get_token() passed verify={get_token_call['verify']} (should not pass it)")
                    return False
                
            except Exception as e:
                print(f"  ✗ get_token() failed: {e}")
                return False
        
        # Test refresh_token
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock, return_value=mock_response):
            try:
                # Call refresh_token - should NOT pass verify parameter
                token = await auth.refresh_token()
                print(f"  ✓ refresh_token() succeeded, token: {token[:20]}...")
                
                # Check that verify was NOT passed
                refresh_call = client_calls[-1]
                if refresh_call['verify'] == 'NOT_SET':
                    print(f"  ✓ refresh_token() did NOT pass verify parameter (correct)")
                else:
                    print(f"  ✗ refresh_token() passed verify={refresh_call['verify']} (should not pass it)")
                    return False
                
            except Exception as e:
                print(f"  ✗ refresh_token() failed: {e}")
                return False
    
    # Test 3: Test KeycloakAuthenticator with verify_ssl=True
    print("\n[Test 3] Testing KeycloakAuthenticator with verify_ssl=True...")
    
    client_calls.clear()
    
    with patch.object(httpx.AsyncClient, '__init__', track_client_init):
        # Create authenticator with verify_ssl=True
        auth = KeycloakAuthenticator(
            keycloak_url="https://keycloak.example.com:443",
            realm="master",
            client_id="test-client",
            username="testuser",
            password="testpass",  # HashiCorpIgnore
            client_secret="test-secret",  # HashiCorpIgnore
            verify_ssl=True  # Should pass verify=True
        )
        
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock, return_value=mock_response):
            try:
                # Call get_token - should pass verify=True
                token = await auth.get_token()
                print(f"  ✓ get_token() succeeded with verify_ssl=True")
                
                # Check that verify=True was passed
                get_token_call = client_calls[-1]
                if get_token_call['verify'] is True:
                    print(f"  ✓ get_token() passed verify=True (correct)")
                else:
                    print(f"  ✗ get_token() passed verify={get_token_call['verify']} (should be True)")
                    return False
                
            except Exception as e:
                print(f"  ✗ get_token() failed: {e}")
                return False
        
        # Test refresh_token with verify_ssl=True
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock, return_value=mock_response):
            try:
                # Call refresh_token - should pass verify=True
                token = await auth.refresh_token()
                print(f"  ✓ refresh_token() succeeded with verify_ssl=True")
                
                # Check that verify=True was passed
                refresh_call = client_calls[-1]
                if refresh_call['verify'] is True:
                    print(f"  ✓ refresh_token() passed verify=True (correct)")
                else:
                    print(f"  ✗ refresh_token() passed verify={refresh_call['verify']} (should be True)")
                    return False
                
            except Exception as e:
                print(f"  ✗ refresh_token() failed: {e}")
                return False
    
    print("\n" + "=" * 80)
    print("✓ All tests passed!")
    print("=" * 80)
    print("\nSummary:")
    print("- Module-level SSL bypass patch is active")
    print("- KeycloakAuthenticator with verify_ssl=False does NOT pass verify parameter")
    print("- Module-level patch applies automatically when verify not specified")
    print("- KeycloakAuthenticator with verify_ssl=True correctly passes verify=True")
    print("- Fix eliminates intermittent SSL certificate verification errors")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_keycloak_ssl_bypass())
    sys.exit(0 if success else 1)

# Made with Bob
