"""Tests for tool usage analytics."""

# Made with Bob
# 2026-06-08 21:12 UTC - Phase 3: Tests for tool analytics functionality

import pytest
import time
from pathlib import Path
import json

from gcm_agent.mcp.tool_analytics import ToolAnalytics


@pytest.fixture
def analytics():
    """Create a fresh analytics instance for testing."""
    analytics = ToolAnalytics()
    analytics.reset_analytics()
    return analytics


@pytest.fixture
def analytics_with_data(analytics):
    """Create analytics instance with sample data."""
    # Record some tool uses
    analytics.record_tool_use("list_keys", success=True, duration=0.5)
    analytics.record_tool_use("list_keys", success=True, duration=0.6)
    analytics.record_tool_use("list_keys", success=False, duration=0.4)
    
    analytics.record_tool_use("get_certificate", success=True, duration=1.2)
    analytics.record_tool_use("get_certificate", success=True, duration=1.1)
    
    analytics.record_tool_use("create_key", success=True, duration=2.0)
    
    return analytics


class TestToolAnalytics:
    """Test suite for ToolAnalytics class."""
    
    def test_singleton_pattern(self):
        """Test that ToolAnalytics follows singleton pattern."""
        analytics1 = ToolAnalytics()
        analytics2 = ToolAnalytics()
        assert analytics1 is analytics2
    
    def test_record_tool_use(self, analytics):
        """Test recording tool usage."""
        analytics.record_tool_use("test_tool", success=True, duration=1.0)
        
        stats = analytics.get_tool_statistics("test_tool")
        assert stats["total_uses"] == 1
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert stats["success_rate"] == 100.0
        assert stats["avg_duration"] == 1.0
    
    def test_record_multiple_uses(self, analytics):
        """Test recording multiple tool uses."""
        analytics.record_tool_use("test_tool", success=True, duration=1.0)
        analytics.record_tool_use("test_tool", success=True, duration=2.0)
        analytics.record_tool_use("test_tool", success=False, duration=0.5)
        
        stats = analytics.get_tool_statistics("test_tool")
        assert stats["total_uses"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.1)
        assert stats["avg_duration"] == pytest.approx(1.17, rel=0.1)
    
    def test_get_most_used_tools(self, analytics_with_data):
        """Test getting most used tools."""
        most_used = analytics_with_data.get_most_used_tools(limit=3)
        
        assert len(most_used) == 3
        assert most_used[0][0] == "list_keys"
        assert most_used[0][1] == 3
        assert most_used[1][0] == "get_certificate"
        assert most_used[1][1] == 2
        assert most_used[2][0] == "create_key"
        assert most_used[2][1] == 1
    
    def test_get_tool_success_rate(self, analytics_with_data):
        """Test calculating tool success rate."""
        # list_keys: 2 success, 1 failure = 66.67%
        rate = analytics_with_data.get_tool_success_rate("list_keys")
        assert rate == pytest.approx(66.67, rel=0.1)
        
        # get_certificate: 2 success, 0 failure = 100%
        rate = analytics_with_data.get_tool_success_rate("get_certificate")
        assert rate == 100.0
        
        # Non-existent tool
        rate = analytics_with_data.get_tool_success_rate("nonexistent")
        assert rate == 0.0
    
    def test_get_tool_avg_duration(self, analytics_with_data):
        """Test calculating average tool duration."""
        # list_keys: (0.5 + 0.6 + 0.4) / 3 = 0.5
        avg = analytics_with_data.get_tool_avg_duration("list_keys")
        assert avg == pytest.approx(0.5, rel=0.1)
        
        # get_certificate: (1.2 + 1.1) / 2 = 1.15
        avg = analytics_with_data.get_tool_avg_duration("get_certificate")
        assert avg == pytest.approx(1.15, rel=0.1)
        
        # Non-existent tool
        avg = analytics_with_data.get_tool_avg_duration("nonexistent")
        assert avg is None
    
    def test_get_prioritized_tool_list(self, analytics_with_data):
        """Test getting prioritized tool list."""
        prioritized = analytics_with_data.get_prioritized_tool_list()
        
        # Should have all 3 tools
        assert len(prioritized) == 3
        
        # list_keys should be first (most used, good success rate, fast)
        assert prioritized[0] == "list_keys"
        
        # All tools should be present
        assert "list_keys" in prioritized
        assert "get_certificate" in prioritized
        assert "create_key" in prioritized
    
    def test_get_all_statistics(self, analytics_with_data):
        """Test getting statistics for all tools."""
        all_stats = analytics_with_data.get_all_statistics()
        
        assert len(all_stats) == 3
        assert "list_keys" in all_stats
        assert "get_certificate" in all_stats
        assert "create_key" in all_stats
        
        # Verify structure
        for tool_name, stats in all_stats.items():
            assert "tool_name" in stats
            assert "total_uses" in stats
            assert "successes" in stats
            assert "failures" in stats
            assert "success_rate" in stats
            assert "avg_duration" in stats
    
    def test_reset_analytics(self, analytics_with_data):
        """Test resetting analytics data."""
        # Verify data exists
        assert len(analytics_with_data.get_all_statistics()) == 3
        
        # Reset
        analytics_with_data.reset_analytics()
        
        # Verify data cleared
        assert len(analytics_with_data.get_all_statistics()) == 0
        assert analytics_with_data.get_most_used_tools() == []
    
    def test_persistence(self, analytics, tmp_path):
        """Test analytics persistence to disk."""
        # Override storage path for testing
        analytics._storage_path = tmp_path / "test_analytics.json"
        
        # Record some data
        analytics.record_tool_use("test_tool", success=True, duration=1.0)
        
        # Save
        analytics.save_analytics()
        
        # Verify file exists
        assert analytics._storage_path.exists()
        
        # Verify content
        with open(analytics._storage_path, 'r') as f:
            data = json.load(f)
        
        assert "usage_count" in data
        assert "test_tool" in data["usage_count"]
        assert data["usage_count"]["test_tool"] == 1
    
    def test_recent_usage_pattern(self, analytics):
        """Test recent usage pattern tracking."""
        # Record some uses
        analytics.record_tool_use("tool1", success=True)
        analytics.record_tool_use("tool2", success=True)
        analytics.record_tool_use("tool1", success=True)
        
        # Get pattern for last 24 hours
        pattern = analytics.get_recent_usage_pattern(hours=24)
        
        assert pattern["tool1"] == 2
        assert pattern["tool2"] == 1
    
    def test_record_without_duration(self, analytics):
        """Test recording tool use without duration."""
        analytics.record_tool_use("test_tool", success=True)
        
        stats = analytics.get_tool_statistics("test_tool")
        assert stats["total_uses"] == 1
        assert stats["avg_duration"] is None
        assert stats["execution_count"] == 0


class TestToolAnalyticsIntegration:
    """Integration tests for tool analytics."""
    
    def test_analytics_across_sessions(self, tmp_path):
        """Test that analytics persist across sessions."""
        storage_path = tmp_path / "analytics.json"
        
        # Session 1: Record data
        analytics1 = ToolAnalytics()
        analytics1._storage_path = storage_path
        analytics1.reset_analytics()
        analytics1.record_tool_use("tool1", success=True, duration=1.0)
        analytics1.save_analytics()
        
        # Session 2: Load data
        analytics2 = ToolAnalytics()
        analytics2._storage_path = storage_path
        analytics2._load_analytics()
        
        stats = analytics2.get_tool_statistics("tool1")
        assert stats["total_uses"] == 1
        assert stats["avg_duration"] == 1.0
    
    def test_concurrent_access(self, analytics):
        """Test thread-safe concurrent access."""
        import threading
        
        def record_uses():
            for _ in range(10):
                analytics.record_tool_use("concurrent_tool", success=True)
        
        # Create multiple threads
        threads = [threading.Thread(target=record_uses) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all uses recorded
        stats = analytics.get_tool_statistics("concurrent_tool")
        assert stats["total_uses"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])