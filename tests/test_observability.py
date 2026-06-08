"""Tests for Phase 4 observability features."""

# Made with Bob
# 2026-06-08 21:47 UTC - Created comprehensive test suite for observability features

import pytest
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from gcm_agent.utils.logger import (
    ObservabilityLogger,
    get_observability_logger,
    timed_operation,
)


class TestObservabilityLogger:
    """Test ObservabilityLogger class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_logger = Mock(spec=logging.Logger)
        self.obs_logger = ObservabilityLogger(self.base_logger)
    
    def test_initialization(self):
        """Test ObservabilityLogger initialization."""
        assert self.obs_logger.logger == self.base_logger
        assert len(self.obs_logger._session_id) == 8
    
    def test_log_tool_selection_basic(self):
        """Test basic tool selection logging."""
        self.obs_logger.log_tool_selection(
            query="list all keys",
            selected_tool="list_keys",
            reasoning="User wants to list keys",
            confidence="high"
        )
        
        # Verify logger.info was called
        assert self.base_logger.info.called
        call_args = self.base_logger.info.call_args[0][0]
        
        # Verify log format
        assert "TOOL_SELECTION:" in call_args
        
        # Parse JSON and verify content
        json_str = call_args.split("TOOL_SELECTION: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["event"] == "tool_selection"
        assert log_data["query"] == "list all keys"
        assert log_data["selected_tool"] == "list_keys"
        assert log_data["reasoning"] == "User wants to list keys"
        assert log_data["confidence"] == "high"
        assert "timestamp" in log_data
        assert "session_id" in log_data
    
    def test_log_tool_selection_with_alternatives(self):
        """Test tool selection logging with alternatives."""
        self.obs_logger.log_tool_selection(
            query="show keys",
            selected_tool="list_keys",
            alternatives=["search_keys", "get_key"],
            confidence="medium"
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        json_str = call_args.split("TOOL_SELECTION: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["alternatives_considered"] == ["search_keys", "get_key"]
        assert log_data["confidence"] == "medium"
    
    def test_log_tool_selection_truncates_long_query(self):
        """Test that long queries are truncated."""
        long_query = "a" * 300
        self.obs_logger.log_tool_selection(
            query=long_query,
            selected_tool="test_tool"
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        json_str = call_args.split("TOOL_SELECTION: ")[1]
        log_data = json.loads(json_str)
        
        assert len(log_data["query"]) == 200
    
    def test_log_tool_execution_success(self):
        """Test successful tool execution logging."""
        self.obs_logger.log_tool_execution(
            tool_name="list_keys",
            duration_ms=150.5,
            success=True,
            result_summary="Found 10 keys"
        )
        
        call_args = self.base_logger.log.call_args[0]
        level = call_args[0]
        message = call_args[1]
        
        assert level == logging.INFO
        assert "TOOL_EXECUTION:" in message
        
        json_str = message.split("TOOL_EXECUTION: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["event"] == "tool_execution"
        assert log_data["tool_name"] == "list_keys"
        assert log_data["duration_ms"] == 150.5
        assert log_data["success"] is True
        assert log_data["result_summary"] == "Found 10 keys"
    
    def test_log_tool_execution_failure(self):
        """Test failed tool execution logging."""
        self.obs_logger.log_tool_execution(
            tool_name="list_keys",
            duration_ms=50.0,
            success=False,
            error="Connection timeout"
        )
        
        call_args = self.base_logger.log.call_args[0]
        level = call_args[0]
        message = call_args[1]
        
        assert level == logging.ERROR
        
        json_str = message.split("TOOL_EXECUTION: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["success"] is False
        assert log_data["error"] == "Connection timeout"
    
    def test_log_token_usage_basic(self):
        """Test basic token usage logging."""
        self.obs_logger.log_token_usage(
            query="test query",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        assert "TOKEN_USAGE:" in call_args
        
        json_str = call_args.split("TOKEN_USAGE: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["event"] == "token_usage"
        assert log_data["prompt_tokens"] == 100
        assert log_data["completion_tokens"] == 50
        assert log_data["total_tokens"] == 150
    
    def test_log_token_usage_with_cost(self):
        """Test token usage logging with cost estimation."""
        self.obs_logger.log_token_usage(
            query="test query",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cumulative_tokens=5000,
            estimated_cost_usd=0.0150
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        json_str = call_args.split("TOKEN_USAGE: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["cumulative_session_tokens"] == 5000
        assert log_data["estimated_cost_usd"] == 0.0150
    
    def test_log_performance_metrics_basic(self):
        """Test basic performance metrics logging."""
        self.obs_logger.log_performance_metrics(
            query="test query",
            total_duration_ms=250.5
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        assert "PERFORMANCE:" in call_args
        
        json_str = call_args.split("PERFORMANCE: ")[1]
        log_data = json.loads(json_str)
        
        assert log_data["event"] == "performance_metrics"
        assert log_data["total_duration_ms"] == 250.5
    
    def test_log_performance_metrics_with_breakdown(self):
        """Test performance metrics logging with timing breakdown."""
        self.obs_logger.log_performance_metrics(
            query="test query",
            total_duration_ms=500.0,
            breakdown={
                "tool_selection_ms": 100.0,
                "tool_execution_ms": 350.0,
                "response_generation_ms": 50.0
            }
        )
        
        call_args = self.base_logger.info.call_args[0][0]
        json_str = call_args.split("PERFORMANCE: ")[1]
        log_data = json.loads(json_str)
        
        assert "timings" in log_data
        assert log_data["timings"]["tool_selection_ms"] == 100.0
        assert log_data["timings"]["tool_execution_ms"] == 350.0
        assert log_data["timings"]["response_generation_ms"] == 50.0


class TestTimedOperationDecorator:
    """Test timed_operation decorator."""
    
    @pytest.mark.asyncio
    async def test_async_function_timing(self):
        """Test timing of async functions."""
        @timed_operation("test_async_op")
        async def async_func():
            import asyncio
            await asyncio.sleep(0.1)
            return "result"
        
        result = await async_func()
        assert result == "result"
    
    def test_sync_function_timing(self):
        """Test timing of sync functions."""
        @timed_operation("test_sync_op")
        def sync_func():
            import time
            time.sleep(0.1)
            return "result"
        
        result = sync_func()
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_async_function_error_handling(self):
        """Test error handling in async functions."""
        @timed_operation("test_error_op")
        async def async_func_with_error():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await async_func_with_error()
    
    def test_sync_function_error_handling(self):
        """Test error handling in sync functions."""
        @timed_operation("test_error_op")
        def sync_func_with_error():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            sync_func_with_error()
    
    @pytest.mark.asyncio
    async def test_default_operation_name(self):
        """Test that function name is used when operation_name not provided."""
        @timed_operation()
        async def my_custom_function():
            return "result"
        
        result = await my_custom_function()
        assert result == "result"


class TestGetObservabilityLogger:
    """Test get_observability_logger function."""
    
    def test_returns_observability_logger(self):
        """Test that function returns ObservabilityLogger instance."""
        logger = get_observability_logger("test_module")
        assert isinstance(logger, ObservabilityLogger)
    
    def test_logger_has_correct_name(self):
        """Test that logger has correct module name."""
        logger = get_observability_logger("test_module")
        assert logger.logger.name == "test_module"


class TestIntegration:
    """Integration tests for observability features."""
    
    def test_full_logging_workflow(self):
        """Test complete logging workflow."""
        base_logger = Mock(spec=logging.Logger)
        obs_logger = ObservabilityLogger(base_logger)
        
        # Simulate tool selection
        obs_logger.log_tool_selection(
            query="list all keys",
            selected_tool="list_keys",
            reasoning="User wants to list keys",
            confidence="high"
        )
        
        # Simulate tool execution
        obs_logger.log_tool_execution(
            tool_name="list_keys",
            duration_ms=150.0,
            success=True,
            result_summary="Found 10 keys"
        )
        
        # Simulate token usage
        obs_logger.log_token_usage(
            query="list all keys",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        
        # Simulate performance metrics
        obs_logger.log_performance_metrics(
            query="list all keys",
            total_duration_ms=200.0,
            breakdown={
                "tool_selection_ms": 20.0,
                "tool_execution_ms": 150.0,
                "response_generation_ms": 30.0
            }
        )
        
        # Verify all logging methods were called
        assert base_logger.info.call_count == 3  # tool_selection, token_usage, performance
        assert base_logger.log.call_count == 1   # tool_execution
    
    def test_session_id_consistency(self):
        """Test that session_id is consistent across logs."""
        base_logger = Mock(spec=logging.Logger)
        obs_logger = ObservabilityLogger(base_logger)
        
        # Log multiple events
        obs_logger.log_tool_selection(query="test1", selected_tool="tool1")
        obs_logger.log_tool_execution(tool_name="tool1", duration_ms=100, success=True)
        obs_logger.log_token_usage(query="test1", prompt_tokens=50, completion_tokens=25, total_tokens=75)
        
        # Extract session_ids from all logs
        session_ids = []
        for call in base_logger.info.call_args_list:
            message = call[0][0]
            json_str = message.split(": ", 1)[1]
            log_data = json.loads(json_str)
            session_ids.append(log_data["session_id"])
        
        # Verify all session_ids are the same
        assert len(set(session_ids)) == 1
        assert len(session_ids[0]) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])