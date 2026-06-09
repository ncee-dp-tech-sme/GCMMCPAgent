"""Tests for chat_ui.py refactoring to verify correctness."""

# Made with Bob
# 2026-06-09 20:47 UTC - Created comprehensive tests for chat_ui refactoring

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from gcm_agent.ui.chat_ui import (
    _validate_base_config,
    _get_watsonx_config,
    _get_openai_config,
    _get_llm_provider_config,
    _handle_initialization_error,
    chat_response,
    AgentState,
)


class TestConfigurationValidation:
    """Test configuration validation helper functions."""
    
    def test_validate_base_config_not_configured(self):
        """Test validation when config is incomplete."""
        mock_config_manager = Mock()
        mock_config_manager.is_configured.return_value = False
        
        error_msg, configs = _validate_base_config(mock_config_manager)
        
        assert error_msg == "Configuration incomplete. Please configure the agent first."
        assert configs is None
    
    def test_validate_base_config_missing_credentials(self):
        """Test validation when credentials are missing."""
        mock_config_manager = Mock()
        mock_config_manager.is_configured.return_value = True
        mock_config_manager.get_keycloak_config.return_value = Mock()
        mock_config_manager.get_gcm_config.return_value = Mock()
        mock_config_manager.get_auth_config.return_value = Mock()
        mock_config_manager.get_agent_config.return_value = Mock()
        mock_config_manager.get_llm_config.return_value = Mock()
        mock_config_manager.get_password.return_value = None  # Missing
        mock_config_manager.get_client_secret.return_value = "secret"
        
        error_msg, configs = _validate_base_config(mock_config_manager)
        
        assert error_msg == "Missing GCM credentials. Please reconfigure the agent."
        assert configs is None
    
    def test_validate_base_config_success(self):
        """Test successful validation."""
        mock_config_manager = Mock()
        mock_config_manager.is_configured.return_value = True
        mock_config_manager.get_keycloak_config.return_value = Mock()
        mock_config_manager.get_gcm_config.return_value = Mock()
        mock_config_manager.get_auth_config.return_value = Mock()
        mock_config_manager.get_agent_config.return_value = Mock()
        mock_config_manager.get_llm_config.return_value = Mock()
        mock_config_manager.get_password.return_value = "password"
        mock_config_manager.get_client_secret.return_value = "secret"
        
        error_msg, configs = _validate_base_config(mock_config_manager)
        
        assert error_msg is None
        assert configs is not None
        assert 'keycloak' in configs
        assert 'gcm' in configs
        assert 'password' in configs
        assert 'client_secret' in configs


class TestProviderConfiguration:
    """Test LLM provider configuration helpers."""
    
    def test_get_watsonx_config_missing_api_key(self):
        """Test WatsonX config when API key is missing."""
        mock_config_manager = Mock()
        mock_config_manager.get_watsonx_config.return_value = Mock()
        mock_config_manager.get_watsonx_api_key.return_value = None
        
        error_msg, config = _get_watsonx_config(mock_config_manager)
        
        assert error_msg == "Missing WatsonX API key. Please reconfigure the agent."
        assert config is None
    
    def test_get_watsonx_config_success(self):
        """Test successful WatsonX config retrieval."""
        mock_config_manager = Mock()
        mock_watsonx_config = Mock()
        mock_config_manager.get_watsonx_config.return_value = mock_watsonx_config
        mock_config_manager.get_watsonx_api_key.return_value = "test-api-key"
        
        error_msg, config = _get_watsonx_config(mock_config_manager)
        
        assert error_msg is None
        assert config is not None
        assert config['config'] == mock_watsonx_config
        assert config['api_key'] == "test-api-key"
    
    def test_get_openai_config_missing_api_key(self):
        """Test OpenAI config when API key is missing."""
        mock_config_manager = Mock()
        mock_config_manager.get_openai_config.return_value = Mock()
        mock_config_manager.get_openai_api_key.return_value = None
        
        error_msg, config = _get_openai_config(mock_config_manager)
        
        assert error_msg == "Missing OpenAI API key. Please reconfigure the agent."
        assert config is None
    
    def test_get_openai_config_success(self):
        """Test successful OpenAI config retrieval."""
        mock_config_manager = Mock()
        mock_openai_config = Mock()
        mock_config_manager.get_openai_config.return_value = mock_openai_config
        mock_config_manager.get_openai_api_key.return_value = "test-api-key"
        
        error_msg, config = _get_openai_config(mock_config_manager)
        
        assert error_msg is None
        assert config is not None
        assert config['config'] == mock_openai_config
        assert config['api_key'] == "test-api-key"
    
    def test_get_llm_provider_config_unknown_provider(self):
        """Test handling of unknown provider."""
        mock_config_manager = Mock()
        
        error_msg, config = _get_llm_provider_config(mock_config_manager, "unknown")
        
        assert error_msg == "Unknown LLM provider: unknown"
        assert config is None
    
    def test_get_llm_provider_config_watsonx(self):
        """Test provider config routing for WatsonX."""
        mock_config_manager = Mock()
        mock_config_manager.get_watsonx_config.return_value = Mock()
        mock_config_manager.get_watsonx_api_key.return_value = "test-key"
        
        error_msg, config = _get_llm_provider_config(mock_config_manager, "watsonx")
        
        assert error_msg is None
        assert config is not None
        assert 'config' in config
        assert 'api_key' in config
    
    def test_get_llm_provider_config_openai(self):
        """Test provider config routing for OpenAI."""
        mock_config_manager = Mock()
        mock_config_manager.get_openai_config.return_value = Mock()
        mock_config_manager.get_openai_api_key.return_value = "test-key"
        
        error_msg, config = _get_llm_provider_config(mock_config_manager, "openai")
        
        assert error_msg is None
        assert config is not None
        assert 'config' in config
        assert 'api_key' in config


class TestErrorHandling:
    """Test consolidated error handling."""
    
    @pytest.mark.asyncio
    async def test_handle_initialization_error(self):
        """Test centralized error handling."""
        mock_agent_state = Mock(spec=AgentState)
        mock_agent_state.cleanup = AsyncMock()
        
        result = await _handle_initialization_error("Test error", mock_agent_state)
        
        assert result == "❌ Test error"
        assert mock_agent_state.error_message == "Test error"
        mock_agent_state.cleanup.assert_called_once()


class TestChatResponse:
    """Test chat response streaming with proper accumulation."""
    
    @pytest.mark.asyncio
    async def test_chat_response_accumulates_chunks(self):
        """Test that streaming chunks are accumulated, not overwritten."""
        # Create mock agent that streams chunks
        mock_agent = Mock()
        mock_agent.stream_chat = AsyncMock()
        
        # Simulate streaming 3 chunks
        async def mock_stream(message):
            yield "Hello "
            yield "world"
            yield "!"
        
        mock_agent.stream_chat.return_value = mock_stream("test")
        
        # Create agent state
        agent_state = AgentState()
        agent_state.agent = mock_agent
        agent_state.initialized = True
        
        # Process message
        history = []
        final_history = None
        
        async for hist, _ in chat_response("test message", history, agent_state):
            final_history = hist
        
        # Verify chunks were accumulated
        assert len(final_history) == 2  # User message + assistant response
        assert final_history[0]["role"] == "user"
        assert final_history[0]["content"] == "test message"
        assert final_history[1]["role"] == "assistant"
        assert final_history[1]["content"] == "Hello world!"  # Accumulated, not just "!"
    
    @pytest.mark.asyncio
    async def test_chat_response_empty_message(self):
        """Test handling of empty message."""
        history = []
        
        async for hist, msg in chat_response("", history):
            assert hist == []
            assert msg == ""
    
    @pytest.mark.asyncio
    async def test_chat_response_agent_not_ready(self):
        """Test handling when agent is not initialized."""
        agent_state = AgentState()
        agent_state.initialized = False
        
        history = []
        final_history = None
        
        async for hist, _ in chat_response("test", history, agent_state):
            final_history = hist
        
        assert len(final_history) == 2
        assert "not initialized" in final_history[1]["content"].lower()
    
    @pytest.mark.asyncio
    async def test_chat_response_agent_execution_error(self):
        """Test consolidated error handling for AgentExecutionError."""
        from gcm_agent.agent.gcm_agent import AgentExecutionError
        
        mock_agent = Mock()
        mock_agent.stream_chat = AsyncMock(side_effect=AgentExecutionError("Test error"))
        
        agent_state = AgentState()
        agent_state.agent = mock_agent
        agent_state.initialized = True
        
        history = []
        final_history = None
        
        async for hist, _ in chat_response("test", history, agent_state):
            final_history = hist
        
        assert len(final_history) == 2
        assert "Agent error" in final_history[1]["content"]
        assert "Test error" in final_history[1]["content"]
    
    @pytest.mark.asyncio
    async def test_chat_response_generic_exception(self):
        """Test consolidated error handling for generic exceptions."""
        mock_agent = Mock()
        mock_agent.stream_chat = AsyncMock(side_effect=ValueError("Generic error"))
        
        agent_state = AgentState()
        agent_state.agent = mock_agent
        agent_state.initialized = True
        
        history = []
        final_history = None
        
        async for hist, _ in chat_response("test", history, agent_state):
            final_history = hist
        
        assert len(final_history) == 2
        assert "Unexpected error" in final_history[1]["content"]
        assert "Generic error" in final_history[1]["content"]


class TestAgentState:
    """Test AgentState functionality."""
    
    def test_agent_state_initialization(self):
        """Test initial state."""
        state = AgentState()
        
        assert state.agent is None
        assert state.mcp_client is None
        assert state.tool_loader is None
        assert state.initialized is False
        assert state.error_message is None
    
    def test_is_ready_when_not_initialized(self):
        """Test is_ready returns False when not initialized."""
        state = AgentState()
        assert not state.is_ready()
    
    def test_is_ready_when_initialized(self):
        """Test is_ready returns True when properly initialized."""
        state = AgentState()
        state.agent = Mock()
        state.initialized = True
        
        assert state.is_ready()
    
    def test_get_status_error(self):
        """Test status with error."""
        state = AgentState()
        state.error_message = "Test error"
        
        status = state.get_status()
        assert "❌" in status
        assert "Test error" in status
    
    def test_get_status_ready(self):
        """Test status when ready."""
        state = AgentState()
        state.initialized = True
        
        status = state.get_status()
        assert "✅" in status
        assert "Ready" in status
    
    def test_get_status_not_initialized(self):
        """Test status when not initialized."""
        state = AgentState()
        
        status = state.get_status()
        assert "⚠️" in status
        assert "Not Initialized" in status
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup resets all state."""
        state = AgentState()
        mock_agent = Mock()
        mock_agent.close = AsyncMock()
        
        state.agent = mock_agent
        state.mcp_client = Mock()
        state.tool_loader = Mock()
        state.initialized = True
        state.error_message = "Some error"
        
        await state.cleanup()
        
        mock_agent.close.assert_called_once()
        assert state.agent is None
        assert state.mcp_client is None
        assert state.tool_loader is None
        assert state.initialized is False
        assert state.error_message is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])