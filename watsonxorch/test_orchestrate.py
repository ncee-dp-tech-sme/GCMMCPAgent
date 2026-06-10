"""Unit tests for WatsonX Orchestrate integration.

Made with Bob
2026-06-10 02:49 UTC - Initial test implementation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from watsonxorch.models import AgentRequest, AgentResponse, HealthResponse, ErrorResponse
from watsonxorch.config import OrchestrateConfig
from watsonxorch.adapter import OrchestrateAdapter


class TestModels:
    """Test Pydantic models."""
    
    def test_agent_request_minimal(self):
        """Test AgentRequest with minimal fields."""
        request = AgentRequest(query="test query")
        assert request.query == "test query"
        assert request.context == {}
        assert request.session_id is None
        assert request.stream is False
    
    def test_agent_request_full(self):
        """Test AgentRequest with all fields."""
        request = AgentRequest(
            query="test query",
            context={"user": "admin"},
            session_id="sess_123",
            stream=True
        )
        assert request.query == "test query"
        assert request.context == {"user": "admin"}
        assert request.session_id == "sess_123"
        assert request.stream is True
    
    def test_agent_response(self):
        """Test AgentResponse model."""
        response = AgentResponse(
            result="test result",
            tools_used=["tool1", "tool2"],
            execution_time=1.23,
            session_id="sess_123"
        )
        assert response.result == "test result"
        assert response.tools_used == ["tool1", "tool2"]
        assert response.execution_time == 1.23
        assert response.session_id == "sess_123"
        assert response.timestamp is not None
        assert response.metadata == {}
    
    def test_health_response(self):
        """Test HealthResponse model."""
        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            components={"agent": "ready"}
        )
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.components == {"agent": "ready"}
        assert response.timestamp is not None
    
    def test_error_response(self):
        """Test ErrorResponse model."""
        response = ErrorResponse(
            error="TestError",
            message="Test error message"
        )
        assert response.error == "TestError"
        assert response.message == "Test error message"
        assert response.timestamp is not None
        assert response.details is None


class TestOrchestrateConfig:
    """Test OrchestrateConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestrateConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cors_enabled is True
        assert config.cors_origins == ["*"]
        assert config.session_timeout == 3600
        assert config.max_sessions == 100
        assert config.max_workers == 4
        assert config.request_timeout == 300
        assert config.log_level == "INFO"
        assert config.log_format == "json"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = OrchestrateConfig(
            host="127.0.0.1",
            port=9000,
            cors_enabled=False,
            log_level="DEBUG"
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.cors_enabled is False
        assert config.log_level == "DEBUG"
    
    @patch.dict('os.environ', {
        'ORCHESTRATE_HOST': '192.168.1.1',
        'ORCHESTRATE_PORT': '7000',
        'ORCHESTRATE_LOG_LEVEL': 'WARNING'
    })
    def test_from_env(self):
        """Test loading configuration from environment."""
        config = OrchestrateConfig.from_env()
        assert config.host == "192.168.1.1"
        assert config.port == 7000
        assert config.log_level == "WARNING"


class TestOrchestrateAdapter:
    """Test OrchestrateAdapter."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock GCM agent."""
        agent = Mock()
        agent.chat = AsyncMock(return_value="Test response")
        agent.stream_chat = AsyncMock()
        agent.history = []
        agent.agent_config = Mock(discovery_mode=False, max_iterations=20)
        agent.close = AsyncMock()
        return agent
    
    @pytest.fixture
    def adapter(self, mock_agent):
        """Create adapter with mock agent."""
        return OrchestrateAdapter(mock_agent)
    
    @pytest.mark.asyncio
    async def test_execute(self, adapter, mock_agent):
        """Test execute method."""
        request = AgentRequest(query="test query")
        response = await adapter.execute(request)
        
        assert isinstance(response, AgentResponse)
        assert response.result == "Test response"
        assert response.session_id is not None
        assert response.execution_time > 0
        mock_agent.chat.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_execute_with_context(self, adapter, mock_agent):
        """Test execute with context."""
        request = AgentRequest(
            query="test query",
            context={"user": "admin"},
            session_id="sess_123"
        )
        response = await adapter.execute(request)
        
        assert response.session_id == "sess_123"
        assert response.metadata["context_keys"] == ["user"]
    
    @pytest.mark.asyncio
    async def test_stream_execute(self, adapter, mock_agent):
        """Test streaming execution."""
        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        mock_agent.stream_chat.return_value = mock_stream()
        
        request = AgentRequest(query="test query", stream=True)
        chunks = []
        async for chunk in adapter.stream_execute(request):
            chunks.append(chunk)
        
        assert chunks == ["chunk1", "chunk2", "chunk3"]
        mock_agent.stream_chat.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_close(self, adapter, mock_agent):
        """Test adapter close."""
        await adapter.close()
        mock_agent.close.assert_called_once()
    
    def test_generate_session_id(self, adapter):
        """Test session ID generation."""
        session_id = adapter._generate_session_id()
        assert session_id.startswith("sess_")
        assert len(session_id) == 17  # "sess_" + 12 hex chars
    
    def test_extract_tools_used(self, adapter, mock_agent):
        """Test extracting tools from history."""
        # Mock message with tool calls
        mock_message = Mock()
        mock_tool_call = Mock()
        mock_tool_call.name = "test_tool"
        mock_message.tool_calls = [mock_tool_call]
        mock_agent.history = [mock_message]
        
        tools = adapter._extract_tools_used()
        assert tools == ["test_tool"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
