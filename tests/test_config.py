"""Tests for secure configuration management and Fernet encryption-based storage behavior."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestSecureStorage:
    """Test secure storage functionality with Fernet encryption."""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_store_credential(self, temp_storage_dir):
        """Test storing credential with Fernet encryption."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('test_key', 'test_value')
        
        # Verify credential was stored
        assert storage.credential_exists('test_key')
        assert storage.get_credential('test_key') == 'test_value'
    
    def test_get_credential(self, temp_storage_dir):
        """Test retrieving credential from encrypted storage."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('test_key', 'test_value')
        
        value = storage.get_credential('test_key')
        assert value == 'test_value'
    
    def test_get_nonexistent_credential(self, temp_storage_dir):
        """Test retrieving non-existent credential returns None."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        value = storage.get_credential('nonexistent_key')
        
        assert value is None
    
    def test_delete_credential(self, temp_storage_dir):
        """Test deleting credential from encrypted storage."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('test_key', 'test_value')
        
        result = storage.delete_credential('test_key')
        assert result is True
        assert not storage.credential_exists('test_key')
    
    def test_delete_nonexistent_credential(self, temp_storage_dir):
        """Test deleting non-existent credential returns False."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        result = storage.delete_credential('nonexistent_key')
        
        assert result is False
    
    def test_list_credentials(self, temp_storage_dir):
        """Test listing all stored credentials."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('key1', 'value1')
        storage.store_credential('key2', 'value2')
        storage.store_credential('key3', 'value3')
        
        keys = storage.list_credentials()
        assert len(keys) == 3
        assert 'key1' in keys
        assert 'key2' in keys
        assert 'key3' in keys
    
    def test_credential_exists(self, temp_storage_dir):
        """Test checking if credential exists."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('test_key', 'test_value')
        
        assert storage.credential_exists('test_key')
        assert not storage.credential_exists('nonexistent_key')
    
    def test_clear_all_credentials(self, temp_storage_dir):
        """Test clearing all credentials."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('key1', 'value1')
        storage.store_credential('key2', 'value2')
        
        count = storage.clear_all_credentials()
        assert count == 2
        assert len(storage.list_credentials()) == 0
    
    def test_encryption_key_persistence(self, temp_storage_dir):
        """Test that encryption key persists across instances."""
        from gcm_agent.config.storage import SecureStorage
        
        # Create first instance and store credential
        storage1 = SecureStorage(storage_dir=temp_storage_dir)
        storage1.store_credential('test_key', 'test_value')
        
        # Create second instance and verify it can read the credential
        storage2 = SecureStorage(storage_dir=temp_storage_dir)
        value = storage2.get_credential('test_key')
        
        assert value == 'test_value'
    
    def test_file_permissions(self, temp_storage_dir):
        """Test that key and credentials files have restrictive permissions."""
        from gcm_agent.config.storage import SecureStorage
        import os
        import stat
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        storage.store_credential('test_key', 'test_value')
        
        key_file = Path(temp_storage_dir) / '.key'
        creds_file = Path(temp_storage_dir) / '.credentials.enc'
        
        # Check that files exist
        assert key_file.exists()
        assert creds_file.exists()
        
        # Check permissions (should be 0o600 - owner read/write only)
        key_perms = stat.S_IMODE(os.stat(key_file).st_mode)
        creds_perms = stat.S_IMODE(os.stat(creds_file).st_mode)
        
        assert key_perms == 0o600
        assert creds_perms == 0o600
    
    def test_invalid_key_raises_error(self, temp_storage_dir):
        """Test that invalid key raises ValueError."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        
        with pytest.raises(ValueError):
            storage.store_credential('', 'value')
        
        with pytest.raises(ValueError):
            storage.store_credential(None, 'value')
    
    def test_invalid_value_raises_error(self, temp_storage_dir):
        """Test that invalid value raises ValueError."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        
        with pytest.raises(ValueError):
            storage.store_credential('key', '')
        
        with pytest.raises(ValueError):
            storage.store_credential('key', None)
    
    def test_corrupted_credentials_file(self, temp_storage_dir):
        """Test handling of corrupted credentials file."""
        from gcm_agent.config.storage import SecureStorage, EncryptionError
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        
        # Write corrupted data to credentials file
        creds_file = Path(temp_storage_dir) / '.credentials.enc'
        with open(creds_file, 'wb') as f:
            f.write(b'corrupted data')
        
        # Attempting to read should raise EncryptionError
        with pytest.raises(EncryptionError):
            storage.get_credential('test_key')
    
    def test_migrate_from_env(self, temp_storage_dir):
        """Test migrating credentials from environment variables."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage(storage_dir=temp_storage_dir)
        
        env_vars = {
            'GCM_PASSWORD': 'secret123',  # HashiCorpIgnore
            'WATSONX_API_KEY': 'api_key_456',  # HashiCorpIgnore
            'GCM_CLIENT_SECRET': 'client_secret_789'  # HashiCorpIgnore
        }
        
        count = storage.migrate_from_env(env_vars)
        
        assert count == 3
        assert storage.get_credential('gcm_password') == 'secret123'
        assert storage.get_credential('watsonx_api_key') == 'api_key_456'
        assert storage.get_credential('gcm_client_secret') == 'client_secret_789'


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_config_manager_exists(self):
        """Test that ConfigManager class exists."""
        from gcm_agent.config.config_manager import ConfigManager
        
        assert ConfigManager is not None
    
    def test_config_models_exist(self):
        """Test that configuration models exist."""
        from gcm_agent.config.config_manager import (
            KeycloakConfig,
            GCMServerConfig,
            AuthConfig,
            WatsonXConfig,
            AgentConfig
        )
        
        assert KeycloakConfig is not None
        assert GCMServerConfig is not None
        assert AuthConfig is not None
        assert WatsonXConfig is not None
        assert AgentConfig is not None

    def test_watsonx_config_verify_ssl_field(self):
        """Test that WatsonXConfig supports SSL verification configuration."""
        from gcm_agent.config.config_manager import WatsonXConfig
        
        config = WatsonXConfig(
            project_id="test-project-id",
            model="ibm/granite-13b-chat-v2",
            verify_ssl=False,
        )
        
        assert config.verify_ssl is False


# Made with Bob
