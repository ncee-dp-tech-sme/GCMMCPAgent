"""Tests for Keycloak token retrieval and GCM authorization flow validation."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from gcm_agent.auth.keycloak_auth import KeycloakAuthenticator
from gcm_agent.auth.gcm_auth import GCMAuthenticator


class TestKeycloakAuthenticator:
    """Test Keycloak authentication functionality."""
    
    @pytest.mark.asyncio
    @patch('gcm_agent.auth.keycloak_auth.httpx.AsyncClient')
    async def test_get_token_success(self, mock_client_class):
        """Test successful token retrieval from Keycloak."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_token_123',
            'token_type': 'Bearer',
            'expires_in': 300
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        auth = KeycloakAuthenticator(
            keycloak_url='https://keycloak.example.com',
            realm='master',
            client_id='test_client',
            username='testuser',
            password='testpass',
            client_secret='test_secret'
        )
        
        token = await auth.get_token()
        
        assert token == 'test_token_123'
        assert mock_client.post.called
    
    @pytest.mark.asyncio
    @patch('gcm_agent.auth.keycloak_auth.httpx.AsyncClient')
    async def test_get_token_failure(self, mock_client_class):
        """Test token retrieval failure handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        auth = KeycloakAuthenticator(
            keycloak_url='https://keycloak.example.com',
            realm='master',
            client_id='test_client',
            username='testuser',
            password='testpass',
            client_secret='test_secret'
        )
        
        with pytest.raises(Exception):
            await auth.get_token()


class TestGCMAuthenticator:
    """Test GCM authentication functionality."""
    
    @pytest.mark.asyncio
    @patch('gcm_agent.auth.gcm_auth.httpx.AsyncClient')
    async def test_authorize_success(self, mock_client_class):
        """Test successful GCM authorization."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'authorized',
            'user': 'testuser'
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        auth = GCMAuthenticator(
            gcm_url='https://gcm.example.com',
            hostname='gcm.example.com'
        )
        
        result = await auth.authorize('test_token_123')
        
        assert result is True
        assert mock_client.post.called
    
    @pytest.mark.asyncio
    @patch('gcm_agent.auth.gcm_auth.httpx.AsyncClient')
    async def test_authorize_failure(self, mock_client_class):
        """Test GCM authorization failure handling."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = 'Forbidden'
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        auth = GCMAuthenticator(
            gcm_url='https://gcm.example.com',
            hostname='gcm.example.com'
        )
        
        with pytest.raises(Exception):
            await auth.authorize('test_token_123', 'testuser')


# Made with Bob
