"""Tests for Phase 3 tool loader enhancements."""

# Made with Bob
# 2026-06-08 21:13 UTC - Phase 3: Tests for tool loader prioritization and force refresh

import pytest
from unittest.mock import Mock, AsyncMock, patch
from langchain_core.tools import Tool

from gcm_agent.mcp.tool_loader import GCMToolLoader, ToolCache
from gcm_agent.mcp.tool_analytics import ToolAnalytics


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = Mock()
    client.discovery_mode = False
    client.get_tools = AsyncMock()
    return client


@pytest.fixture
def sample_tools():
    """Create sample tools for testing."""
    return [
        Tool(name="list_keys", description="List all keys", func=lambda: "keys"),
        Tool(name="get_certificate", description="Get certificate", func=lambda: "cert"),
        Tool(name="create_key", description="Create a key", func=lambda: "created"),
        Tool(name="delete_key", description="Delete a key", func=lambda: "deleted"),
    ]


@pytest.fixture
def tool_loader(mock_mcp_client):
    """Create a tool loader instance."""
    return GCMToolLoader(mock_mcp_client, cache_ttl=3600)


@pytest.fixture
def analytics_with_priority():
    """Create analytics with priority data."""
    analytics = ToolAnalytics()
    analytics.reset_analytics()
    
    # Record usage to establish priority
    # list_keys: most used, high success
    analytics.record_tool_use("list_keys", success=True, duration=0.5)
    analytics.record_tool_use("list_keys", success=True, duration=0.6)
    analytics.record_tool_use("list_keys", success=True, duration=0.4)
    
    # get_certificate: medium usage
    analytics.record_tool_use("get_certificate", success=True, duration=1.0)
    analytics.record_tool_use("get_certificate", success=True, duration=1.1)
    
    # create_key: low usage
    analytics.record_tool_use("create_key", success=True, duration=2.0)
    
    return analytics


class TestToolCache:
    """Test suite for ToolCache class."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ToolCache(ttl=3600)
        assert cache._ttl == 3600
        assert len(cache._cache) == 0
    
    def test_cache_set_and_get(self, sample_tools):
        """Test setting and getting cached tools."""
        cache = ToolCache(ttl=3600)
        
        cache.set("test_key", sample_tools)
        retrieved = cache.get("test_key")
        
        assert retrieved is not None
        assert len(retrieved) == len(sample_tools)
        assert retrieved[0].name == "list_keys"
    
    def test_cache_expiration(self, sample_tools):
        """Test cache expiration."""
        cache = ToolCache(ttl=1)  # 1 second TTL
        
        cache.set("test_key", sample_tools)
        
        # Should be available immediately
        assert cache.get("test_key") is not None
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("test_key") is None
    
    def test_cache_clear(self, sample_tools):
        """Test clearing cache."""
        cache = ToolCache(ttl=3600)
        
        cache.set("key1", sample_tools)
        cache.set("key2", sample_tools)
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_clear_key(self, sample_tools):
        """Test clearing specific cache key."""
        cache = ToolCache(ttl=3600)
        
        cache.set("key1", sample_tools)
        cache.set("key2", sample_tools)
        
        cache.clear_key("key1")
        
        assert cache.get("key1") is None
        assert cache.get("key2") is not None


class TestGCMToolLoader:
    """Test suite for GCMToolLoader class."""
    
    @pytest.mark.asyncio
    async def test_load_tools_with_cache(self, tool_loader, mock_mcp_client, sample_tools):
        """Test loading tools with caching."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # First load - should fetch from server
        tools1 = await tool_loader.load_tools()
        assert len(tools1) == 4
        assert mock_mcp_client.get_tools.call_count == 1
        
        # Second load - should use cache
        tools2 = await tool_loader.load_tools()
        assert len(tools2) == 4
        assert mock_mcp_client.get_tools.call_count == 1  # Still 1, not 2
    
    @pytest.mark.asyncio
    async def test_load_tools_force_refresh(self, tool_loader, mock_mcp_client, sample_tools):
        """Test force refresh bypasses cache."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # First load
        await tool_loader.load_tools()
        assert mock_mcp_client.get_tools.call_count == 1
        
        # Force refresh - should fetch again
        await tool_loader.load_tools(force_refresh=True)
        assert mock_mcp_client.get_tools.call_count == 2
    
    @pytest.mark.asyncio
    async def test_clear_cache_specific_key(self, tool_loader, mock_mcp_client, sample_tools):
        """Test clearing specific cache key."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # Load tools
        await tool_loader.load_tools()
        
        # Clear specific key
        tool_loader.clear_cache(key="all_tools")
        
        # Next load should fetch from server
        await tool_loader.load_tools()
        assert mock_mcp_client.get_tools.call_count == 2
    
    @pytest.mark.asyncio
    async def test_load_prioritized_tools_no_analytics(
        self, tool_loader, mock_mcp_client, sample_tools
    ):
        """Test prioritized loading with no analytics data."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # Reset analytics to have no data
        tool_loader.analytics.reset_analytics()
        
        # Load prioritized tools
        tools = await tool_loader.load_prioritized_tools()
        
        # Should return all tools in original order (no prioritization)
        assert len(tools) == 4
        assert tools[0].name == "list_keys"
    
    @pytest.mark.asyncio
    async def test_load_prioritized_tools_with_analytics(
        self, tool_loader, mock_mcp_client, sample_tools, analytics_with_priority
    ):
        """Test prioritized loading with analytics data."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # Use analytics with priority data
        tool_loader.analytics = analytics_with_priority
        
        # Load prioritized tools
        tools = await tool_loader.load_prioritized_tools()
        
        # Should return all tools
        assert len(tools) == 4
        
        # Most used tool (list_keys) should be first
        assert tools[0].name == "list_keys"
        
        # All tools should be present
        tool_names = [t.name for t in tools]
        assert "list_keys" in tool_names
        assert "get_certificate" in tool_names
        assert "create_key" in tool_names
        assert "delete_key" in tool_names
    
    @pytest.mark.asyncio
    async def test_load_prioritized_tools_force_refresh(
        self, tool_loader, mock_mcp_client, sample_tools, analytics_with_priority
    ):
        """Test prioritized loading with force refresh."""
        mock_mcp_client.get_tools.return_value = sample_tools
        tool_loader.analytics = analytics_with_priority
        
        # First load
        await tool_loader.load_prioritized_tools()
        assert mock_mcp_client.get_tools.call_count == 1
        
        # Force refresh
        await tool_loader.load_prioritized_tools(force_refresh=True)
        assert mock_mcp_client.get_tools.call_count == 2
    
    def test_get_tool_analytics_summary(self, tool_loader, analytics_with_priority):
        """Test getting analytics summary."""
        tool_loader.analytics = analytics_with_priority
        
        summary = tool_loader.get_tool_analytics_summary()
        
        assert "most_used" in summary
        assert "total_tools_tracked" in summary
        assert "recent_pattern" in summary
        assert "statistics" in summary
        
        # Verify most used
        assert len(summary["most_used"]) > 0
        assert summary["most_used"][0][0] == "list_keys"
        
        # Verify total tracked
        assert summary["total_tools_tracked"] == 3


class TestToolLoaderIntegration:
    """Integration tests for tool loader."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_mcp_client, sample_tools):
        """Test complete workflow: load, use, prioritize."""
        mock_mcp_client.get_tools.return_value = sample_tools
        
        # Create loader
        loader = GCMToolLoader(mock_mcp_client, cache_ttl=3600)
        
        # Reset analytics
        loader.analytics.reset_analytics()
        
        # Load tools
        tools = await loader.load_tools()
        assert len(tools) == 4
        
        # Simulate tool usage
        loader.analytics.record_tool_use("list_keys", success=True, duration=0.5)
        loader.analytics.record_tool_use("list_keys", success=True, duration=0.6)
        loader.analytics.record_tool_use("get_certificate", success=True, duration=1.0)
        
        # Load prioritized tools
        prioritized = await loader.load_prioritized_tools()
        
        # list_keys should be first (most used)
        assert prioritized[0].name == "list_keys"
        
        # Get analytics summary
        summary = loader.get_tool_analytics_summary()
        assert summary["most_used"][0][0] == "list_keys"
        assert summary["most_used"][0][1] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])