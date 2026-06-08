"""Tool usage analytics for tracking and optimizing tool selection."""

# Made with Bob
# 2026-06-08 21:10 UTC - Initial implementation of tool usage analytics for Phase 3

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
import threading
from pathlib import Path

from gcm_agent.utils.logger import get_mcp_logger


class ToolAnalytics:
    """
    Track tool usage patterns to optimize tool loading and selection.
    
    Collects metrics on:
    - Tool execution frequency
    - Tool execution success/failure rates
    - Tool execution duration
    - Tool usage patterns over time
    
    Thread-safe singleton implementation for consistent analytics across sessions.
    """
    
    _instance: Optional["ToolAnalytics"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implement thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize analytics tracker."""
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self.logger = get_mcp_logger()
            
            # Tool usage counters
            self._usage_count: Dict[str, int] = defaultdict(int)
            self._success_count: Dict[str, int] = defaultdict(int)
            self._failure_count: Dict[str, int] = defaultdict(int)
            
            # Tool execution timing
            self._total_duration: Dict[str, float] = defaultdict(float)
            self._execution_count: Dict[str, int] = defaultdict(int)
            
            # Recent usage tracking (last 100 tool calls)
            self._recent_usage: List[Tuple[str, datetime, bool]] = []
            self._max_recent = 100
            
            # Persistence
            self._storage_path = Path.home() / ".gcm_agent" / "tool_analytics.json"
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing analytics
            self._load_analytics()
            
            self._initialized = True
            self.logger.debug("ToolAnalytics initialized")
    
    def record_tool_use(
        self,
        tool_name: str,
        success: bool = True,
        duration: Optional[float] = None
    ) -> None:
        """
        Record a tool execution.
        
        Args:
            tool_name: Name of the tool executed
            success: Whether execution was successful
            duration: Execution duration in seconds (optional)
        """
        with self._lock:
            # Update counters
            self._usage_count[tool_name] += 1
            
            if success:
                self._success_count[tool_name] += 1
            else:
                self._failure_count[tool_name] += 1
            
            # Update timing
            if duration is not None:
                self._total_duration[tool_name] += duration
                self._execution_count[tool_name] += 1
            
            # Update recent usage
            self._recent_usage.append((tool_name, datetime.now(), success))
            if len(self._recent_usage) > self._max_recent:
                self._recent_usage.pop(0)
            
            self.logger.debug(
                f"Recorded tool use: {tool_name} "
                f"(success={success}, duration={duration}s)"
            )
    
    def get_most_used_tools(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get most frequently used tools.
        
        Args:
            limit: Maximum number of tools to return
        
        Returns:
            List of (tool_name, usage_count) tuples, sorted by usage
        """
        with self._lock:
            sorted_tools = sorted(
                self._usage_count.items(),
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_tools[:limit]
    
    def get_tool_success_rate(self, tool_name: str) -> float:
        """
        Get success rate for a specific tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Success rate as percentage (0-100)
        """
        with self._lock:
            total = self._usage_count.get(tool_name, 0)
            if total == 0:
                return 0.0
            
            success = self._success_count.get(tool_name, 0)
            return (success / total) * 100
    
    def get_tool_avg_duration(self, tool_name: str) -> Optional[float]:
        """
        Get average execution duration for a tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Average duration in seconds, or None if no timing data
        """
        with self._lock:
            count = self._execution_count.get(tool_name, 0)
            if count == 0:
                return None
            
            total = self._total_duration.get(tool_name, 0.0)
            return total / count
    
    def get_recent_usage_pattern(
        self,
        hours: int = 24
    ) -> Dict[str, int]:
        """
        Get tool usage pattern for recent time period.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            Dictionary of tool_name -> usage_count for the period
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            pattern = defaultdict(int)
            
            for tool_name, timestamp, _ in self._recent_usage:
                if timestamp >= cutoff:
                    pattern[tool_name] += 1
            
            return dict(pattern)
    
    def get_tool_statistics(self, tool_name: str) -> Dict[str, any]:
        """
        Get comprehensive statistics for a tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Dictionary with usage, success rate, and timing stats
        """
        with self._lock:
            return {
                "tool_name": tool_name,
                "total_uses": self._usage_count.get(tool_name, 0),
                "successes": self._success_count.get(tool_name, 0),
                "failures": self._failure_count.get(tool_name, 0),
                "success_rate": self.get_tool_success_rate(tool_name),
                "avg_duration": self.get_tool_avg_duration(tool_name),
                "execution_count": self._execution_count.get(tool_name, 0),
            }
    
    def get_all_statistics(self) -> Dict[str, Dict[str, any]]:
        """
        Get statistics for all tracked tools.
        
        Returns:
            Dictionary mapping tool_name -> statistics
        """
        with self._lock:
            all_tools = set(self._usage_count.keys())
            return {
                tool: self.get_tool_statistics(tool)
                for tool in all_tools
            }
    
    def get_prioritized_tool_list(self) -> List[str]:
        """
        Get tools prioritized by usage frequency and success rate.
        
        Returns:
            List of tool names, sorted by priority (most important first)
        """
        with self._lock:
            # Calculate priority score for each tool
            # Score = usage_count * success_rate * (1 + avg_speed_bonus)
            scores = {}
            
            for tool_name in self._usage_count.keys():
                usage = self._usage_count[tool_name]
                success_rate = self.get_tool_success_rate(tool_name) / 100
                
                # Speed bonus: faster tools get slight priority
                avg_duration = self.get_tool_avg_duration(tool_name)
                speed_bonus = 0.0
                if avg_duration is not None and avg_duration > 0:
                    # Bonus inversely proportional to duration
                    # Max bonus of 0.5 for very fast tools (<1s)
                    speed_bonus = min(0.5, 1.0 / avg_duration)
                
                score = usage * success_rate * (1 + speed_bonus)
                scores[tool_name] = score
            
            # Sort by score descending
            sorted_tools = sorted(
                scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            return [tool for tool, _ in sorted_tools]
    
    def reset_analytics(self) -> None:
        """Reset all analytics data."""
        with self._lock:
            self._usage_count.clear()
            self._success_count.clear()
            self._failure_count.clear()
            self._total_duration.clear()
            self._execution_count.clear()
            self._recent_usage.clear()
            
            self.logger.info("Analytics data reset")
    
    def _load_analytics(self) -> None:
        """Load analytics from persistent storage."""
        try:
            if self._storage_path.exists():
                with open(self._storage_path, 'r') as f:
                    data = json.load(f)
                
                self._usage_count = defaultdict(int, data.get("usage_count", {}))
                self._success_count = defaultdict(int, data.get("success_count", {}))
                self._failure_count = defaultdict(int, data.get("failure_count", {}))
                self._total_duration = defaultdict(float, data.get("total_duration", {}))
                self._execution_count = defaultdict(int, data.get("execution_count", {}))
                
                self.logger.info(f"Loaded analytics from {self._storage_path}")
        except Exception as e:
            self.logger.warning(f"Failed to load analytics: {e}")
    
    def save_analytics(self) -> None:
        """Save analytics to persistent storage."""
        try:
            with self._lock:
                data = {
                    "usage_count": dict(self._usage_count),
                    "success_count": dict(self._success_count),
                    "failure_count": dict(self._failure_count),
                    "total_duration": dict(self._total_duration),
                    "execution_count": dict(self._execution_count),
                    "last_updated": datetime.now().isoformat(),
                }
                
                with open(self._storage_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.logger.debug(f"Saved analytics to {self._storage_path}")
        except Exception as e:
            self.logger.error(f"Failed to save analytics: {e}")