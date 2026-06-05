"""Tests for MCP client behavior, token injection, and tool loading workflows."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.mcp.tool_loader import GCMToolLoader


class TestGCMMCPClient:
    """Test GCM MCP client functionality."""
    
    @pytest.mark.asyncio
    @patch('gcm_agent.mcp.client.MultiServerMCPClient')
    async def test_initialize_client(self, mock_mcp_class):
        """Test MCP client initialization."""
        mock_mcp = AsyncMock()
        mock_mcp_class.return_value = mock_mcp
        
        mock_factory = Mock()
        client = GCMMCPClient(
            gcm_url='https://gcm.example.com',
            client_factory=mock_factory
        )
        
        await client.connect()
        
        assert mock_mcp_class.called
    
    @pytest.mark.asyncio
    @patch('gcm_agent.mcp.client.MultiServerMCPClient')
    async def test_get_tools(self, mock_mcp_class):
        """Test retrieving tools from MCP server."""
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_tool.description = 'Test tool description'
        
        mock_mcp = AsyncMock()
        mock_mcp.get_tools.return_value = [mock_tool]
        mock_mcp_class.return_value = mock_mcp
        
        mock_factory = Mock()
        client = GCMMCPClient(
            gcm_url='https://gcm.example.com',
            client_factory=mock_factory
        )
        
        await client.connect()
        tools = await client.get_tools()
        
        assert len(tools) == 1
        assert tools[0].name == 'test_tool'
    
    @pytest.mark.asyncio
    @patch('gcm_agent.mcp.client.MultiServerMCPClient')
    async def test_discovery_mode(self, mock_mcp_class):
        """Test discovery mode configuration."""
        mock_mcp = AsyncMock()
        mock_mcp_class.return_value = mock_mcp
        
        mock_factory = Mock()
        client = GCMMCPClient(
            gcm_url='https://gcm.example.com',
            client_factory=mock_factory,
            discovery_mode=True
        )
        
        assert client.discovery_mode is True


class TestGCMToolLoader:
    """Test tool loading functionality."""
    
    @pytest.mark.asyncio
    async def test_load_tools(self):
        """Test loading tools from MCP client."""
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_client.get_tools.return_value = [mock_tool]
        
        loader = GCMToolLoader(mock_client)
        tools = await loader.load_tools()
        
        assert len(tools) == 1
        assert tools[0].name == 'test_tool'
    
    @pytest.mark.asyncio
    async def test_load_tools_empty(self):
        """Test loading tools when none are available."""
        mock_client = AsyncMock()
        mock_client.get_tools.return_value = []
        
        loader = GCMToolLoader(mock_client)
        tools = await loader.load_tools()
        
        assert len(tools) == 0
    
    @pytest.mark.asyncio
    async def test_tool_loader_caching(self):
        """Test that tool loader uses caching."""
        mock_client = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = 'test_tool'
        mock_client.get_tools.return_value = [mock_tool]
        
        loader = GCMToolLoader(mock_client)
        
        # Load tools twice
        tools1 = await loader.load_tools()
        tools2 = await loader.load_tools()
        
        # Should only call get_tools once due to caching
        assert mock_client.get_tools.call_count == 1
        assert len(tools1) == 1
        assert len(tools2) == 1


# Made with Bob
