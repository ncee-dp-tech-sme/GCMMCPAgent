"""Tests for secure configuration management and keyring-backed storage behavior."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSecureStorage:
    """Test secure storage functionality."""
    
    @patch('gcm_agent.config.storage.keyring')
    def test_store_credential(self, mock_keyring):
        """Test storing credential to keyring."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage()
        storage.store_credential('test_key', 'test_value')
        
        # Verify keyring.set_password was called
        assert mock_keyring.set_password.called
    
    @patch('gcm_agent.config.storage.keyring')
    def test_get_credential(self, mock_keyring):
        """Test retrieving credential from keyring."""
        from gcm_agent.config.storage import SecureStorage
        
        mock_keyring.get_password.return_value = 'test_value'
        
        storage = SecureStorage()
        value = storage.get_credential('test_key')
        
        assert value == 'test_value'
    
    @patch('gcm_agent.config.storage.keyring')
    def test_delete_credential(self, mock_keyring):
        """Test deleting credential from keyring."""
        from gcm_agent.config.storage import SecureStorage
        
        storage = SecureStorage()
        result = storage.delete_credential('test_key')
        
        assert mock_keyring.delete_password.called


class TestConfigManager:
    """Test configuration manager functionality."""
    
    def test_config_manager_exists(self):
        """Test that ConfigManager class exists."""
        from gcm_agent.config.config_manager import ConfigManager
        
        assert ConfigManager is not None
    
    def test_config_models_exist(self):
        """Test that configuration models exist."""
        from gcm_agent.config.config_manager import (
            GCMServerConfig,
            AuthConfig,
            WatsonXConfig,
            AgentConfig
        )
        
        assert GCMServerConfig is not None
        assert AuthConfig is not None
        assert WatsonXConfig is not None
        assert AgentConfig is not None


# Made with Bob
