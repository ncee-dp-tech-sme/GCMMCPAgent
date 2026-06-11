#!/usr/bin/env python3
"""
Verification script for the secure configuration management system.
Tests basic functionality of logger, storage, and config manager.
"""

# Made with Bob
# 2026-06-05 19:54 UTC - Created verification script for config system

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_logger():
    """Test logger functionality."""
    print("=" * 60)
    print("Testing Logger Module")
    print("=" * 60)
    
    try:
        from gcm_agent.utils import get_logger, sanitize_sensitive_data
        
        # Create a test logger
        logger = get_logger("test_logger")
        logger.info("Logger initialized successfully")
        
        # Test sensitive data sanitization
        sensitive_msg = "password=secret123 api_key=abc123"
        sanitized = sanitize_sensitive_data(sensitive_msg)
        print(f"Original: {sensitive_msg}")
        print(f"Sanitized: {sanitized}")
        
        print("✓ Logger module working correctly\n")
        return True
    except Exception as e:
        print(f"✗ Logger module failed: {e}\n")
        return False


def test_storage():
    """Test secure storage functionality."""
    print("=" * 60)
    print("Testing Secure Storage Module")
    print("=" * 60)
    
    try:
        from gcm_agent.config import get_storage
        
        storage = get_storage()
        print(f"✓ Storage initialized with service: {storage.SERVICE_NAME}")
        
        # Test store and retrieve
        test_key = "test_credential"
        test_value = "test_value_123"
        
        storage.store_credential(test_key, test_value)
        print(f"✓ Stored test credential: {test_key}")
        
        retrieved = storage.get_credential(test_key)
        if retrieved == test_value:
            print(f"✓ Retrieved credential matches: {retrieved}")
        else:
            print(f"✗ Retrieved credential mismatch: {retrieved}")
            return False
        
        # Test deletion
        deleted = storage.delete_credential(test_key)
        if deleted:
            print(f"✓ Deleted test credential")
        
        # Verify deletion
        retrieved_after = storage.get_credential(test_key)
        if retrieved_after is None:
            print(f"✓ Credential properly deleted")
        else:
            print(f"✗ Credential still exists after deletion")
            return False
        
        print("✓ Secure storage module working correctly\n")
        return True
    except Exception as e:
        print(f"✗ Secure storage module failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_config_manager():
    """Test configuration manager functionality."""
    print("=" * 60)
    print("Testing Configuration Manager Module")
    print("=" * 60)
    
    try:
        from gcm_agent.config import (
            get_config_manager,
            GCMServerConfig,
            AuthConfig,
            WatsonXConfig,
            AgentConfig,
        )
        
        config_manager = get_config_manager()
        print("✓ ConfigManager initialized")
        
        # Test Pydantic models
        gcm_config = GCMServerConfig(
            url="https://gcm.example.com",
            hostname="gcm.example.com",
            keycloak_port=443,
            realm="master",
            verify_ssl=True,
        )
        print(f"✓ GCMServerConfig created: {gcm_config.url}")
        
        auth_config = AuthConfig(
            username="testuser",
            client_id="test-client",
        )
        print(f"✓ AuthConfig created: {auth_config.username}")
        
        watsonx_config = WatsonXConfig(
            project_id="test-project-123",
            model="ibm/granite-13b-chat-v2",
        )
        print(f"✓ WatsonXConfig created: {watsonx_config.project_id}")
        
        agent_config = AgentConfig(
            discovery_mode=True,
            max_iterations=10,
            timeout=300,
        )
        print(f"✓ AgentConfig created: discovery_mode={agent_config.discovery_mode}")
        
        # Test configuration storage
        config_manager.update_gcm_config(gcm_config)
        print("✓ Stored GCM configuration")
        
        config_manager.update_auth_config(
            auth_config,
            password="test_password",  # HashiCorpIgnore
            client_secret="test_secret",  # HashiCorpIgnore
        )
        print("✓ Stored auth configuration with credentials")
        
        config_manager.update_watsonx_config(
            watsonx_config,
            api_key="test_api_key",  # HashiCorpIgnore
        )
        print("✓ Stored WatsonX configuration with API key")
        
        config_manager.update_agent_config(agent_config)
        print("✓ Stored agent configuration")
        
        # Test retrieval
        retrieved_gcm = config_manager.get_gcm_config()
        print(f"✓ Retrieved GCM config: {retrieved_gcm.url}")
        
        retrieved_auth = config_manager.get_auth_config()
        print(f"✓ Retrieved auth config: {retrieved_auth.username}")
        
        password = config_manager.get_password()
        if password == "test_password":
            print("✓ Retrieved password correctly")
        else:
            print(f"✗ Password mismatch: {password}")
            return False
        
        # Test is_configured
        is_configured = config_manager.is_configured()
        print(f"✓ Configuration status: {is_configured}")
        
        # Clean up test data
        config_manager.reset_config()
        print("✓ Reset configuration (cleanup)")
        
        print("✓ Configuration manager module working correctly\n")
        return True
    except Exception as e:
        print(f"✗ Configuration manager module failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("GCM Agent Configuration System Verification")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Logger", test_logger()))
    results.append(("Secure Storage", test_storage()))
    results.append(("Config Manager", test_config_manager()))
    
    # Summary
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All verification tests passed!")
        return 0
    else:
        print("\n✗ Some verification tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())