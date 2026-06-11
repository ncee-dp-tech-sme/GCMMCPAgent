"""Test debug UI integration with observability logging."""

# Made with Bob
# 2026-06-09 22:13 UTC - Created test to verify debug UI receives observability logs

import pytest
from unittest.mock import Mock, AsyncMock, patch
from gcm_agent.agent import create_gcm_agent
from gcm_agent.config.config_manager import (
    AgentSetupConfig,
    KeycloakConfig,
    GCMServerConfig,
    AuthConfig,
    AgentConfig,
    LLMProviderConfig,
    WatsonXConfig,
)
from gcm_agent.ui.debug_ui import DebugUI


@pytest.fixture
def mock_setup_config():
    """Create mock setup configuration."""
    return AgentSetupConfig(
        keycloak_config=KeycloakConfig(
            url="https://keycloak.example.com",
            realm="master",
            port=443,
        ),
        gcm_config=GCMServerConfig(
            url="https://gcm.example.com:9443",
            hostname="gcm.example.com",
            mcp_server_url="https://gcm.example.com:8080",
        ),
        auth_config=AuthConfig(
            username="testuser",
            client_id="test-client",
        ),
        agent_config=AgentConfig(
            discovery_mode=False,
            max_iterations=20,
        ),
        llm_config=LLMProviderConfig(
            provider="watsonx",
            watsonx_config=WatsonXConfig(
                url="https://watsonx.example.com",
                project_id="test-project",
                model="test-model",
                verify_ssl=False,
            ),
            watsonx_api_key="test-api-key",  # HashiCorpIgnore
        ),
        password="test-password",  # HashiCorpIgnore
        client_secret="test-secret",  # HashiCorpIgnore
    )


@pytest.mark.asyncio
async def test_debug_ui_passed_to_agent(mock_setup_config):
    """Test that debug_ui is properly passed through to agent."""
    # Create mock debug UI
    debug_ui = Mock(spec=DebugUI)
    debug_ui.add_log_entry = Mock()
    
    # Mock the MCP client creation
    with patch('gcm_agent.agent.create_gcm_mcp_client') as mock_create_mcp:
        mock_mcp_client = AsyncMock()
        mock_tool_loader = Mock()
        mock_tool_loader.load_tools = AsyncMock(return_value=[])
        mock_create_mcp.return_value = (mock_mcp_client, mock_tool_loader)
        
        # Mock LLM initialization
        with patch('gcm_agent.agent.gcm_agent.ChatWatsonx') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Create agent with debug_ui
            agent = await create_gcm_agent(mock_setup_config, debug_ui=debug_ui)
            
            # Verify debug_ui was passed to ObservabilityLogger
            assert agent.obs_logger._debug_ui is debug_ui
            
            # Cleanup
            await agent.close()


@pytest.mark.asyncio
async def test_debug_ui_receives_logs(mock_setup_config):
    """Test that debug_ui receives observability logs."""
    # Create mock debug UI
    debug_ui = Mock(spec=DebugUI)
    debug_ui.add_log_entry = Mock()
    
    # Mock the MCP client creation
    with patch('gcm_agent.agent.create_gcm_mcp_client') as mock_create_mcp:
        mock_mcp_client = AsyncMock()
        mock_tool_loader = Mock()
        mock_tool_loader.load_tools = AsyncMock(return_value=[])
        mock_create_mcp.return_value = (mock_mcp_client, mock_tool_loader)
        
        # Mock LLM initialization
        with patch('gcm_agent.agent.gcm_agent.ChatWatsonx') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Create agent with debug_ui
            agent = await create_gcm_agent(mock_setup_config, debug_ui=debug_ui)
            
            # Simulate logging a tool selection
            agent.obs_logger.log_tool_selection(
                query="test query",
                selected_tool="test_tool",
                reasoning="test reasoning",
            )
            
            # Verify debug_ui received the log
            debug_ui.add_log_entry.assert_called_once()
            call_args = debug_ui.add_log_entry.call_args
            assert call_args[0][0] == "tool_selection"
            assert "selected_tool" in call_args[0][1]
            assert call_args[0][1]["selected_tool"] == "test_tool"
            
            # Cleanup
            await agent.close()


@pytest.mark.asyncio
async def test_agent_works_without_debug_ui(mock_setup_config):
    """Test that agent works correctly when debug_ui is not provided."""
    # Mock the MCP client creation
    with patch('gcm_agent.agent.create_gcm_mcp_client') as mock_create_mcp:
        mock_mcp_client = AsyncMock()
        mock_tool_loader = Mock()
        mock_tool_loader.load_tools = AsyncMock(return_value=[])
        mock_create_mcp.return_value = (mock_mcp_client, mock_tool_loader)
        
        # Mock LLM initialization
        with patch('gcm_agent.agent.gcm_agent.ChatWatsonx') as mock_llm:
            mock_llm.return_value = Mock()
            
            # Create agent WITHOUT debug_ui (should default to None)
            agent = await create_gcm_agent(mock_setup_config)
            
            # Verify debug_ui is None
            assert agent.obs_logger._debug_ui is None
            
            # Verify logging still works (just goes to console)
            agent.obs_logger.log_tool_selection(
                query="test query",
                selected_tool="test_tool",
            )
            
            # Cleanup
            await agent.close()