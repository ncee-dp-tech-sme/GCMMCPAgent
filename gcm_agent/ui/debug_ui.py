"""Debug UI for observability and monitoring."""

# Made with Bob
# 2026-06-08 21:50 UTC - Created debugging dashboard for Phase 4 observability features
# 2026-06-09 21:03 UTC - Refactored create_ui: extracted _TAB_CONFIGS constant and _build_tab helper to eliminate 84% code duplication (94 lines → 15 lines)

import gradio as gr
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from gcm_agent.utils.logger import get_agent_logger
from gcm_agent.mcp.tool_analytics import ToolAnalytics


# Tab configuration: (emoji, title, description, fetch_function, output_type, has_filters)
_TAB_CONFIGS = [
    ("📋", "Recent Logs", "Recent Agent Logs", "get_recent_logs", "textbox", True),
    ("🛠️", "Tool Analytics", "Tool Usage Analytics", "get_tool_analytics_summary", "markdown", False),
    ("💰", "Token Usage", "Token Usage Statistics", "get_token_statistics", "markdown", False),
    ("⚡", "Performance", "Performance Metrics", "get_performance_statistics", "markdown", False),
]


class DebugUI:
    """
    Debugging dashboard for GCM Agent observability.
    
    Provides real-time monitoring of:
    - Recent logs (tool selection, execution, tokens, performance)
    - Tool usage analytics
    - Token usage statistics
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize debug UI."""
        self.logger = get_agent_logger()
        self.analytics = ToolAnalytics()
        self._log_buffer: List[Dict[str, Any]] = []
        self._max_logs = 100
    
    def add_log_entry(self, log_type: str, data: Dict[str, Any]) -> None:
        """
        Add a log entry to the buffer.
        
        Args:
            log_type: Type of log (tool_selection, tool_execution, token_usage, performance)
            data: Log data dictionary
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "type": log_type,
            "data": data
        }
        self._log_buffer.append(entry)
        
        # Keep only last N logs
        if len(self._log_buffer) > self._max_logs:
            self._log_buffer = self._log_buffer[-self._max_logs:]
    
    def get_recent_logs(self, log_type: Optional[str] = None, limit: int = 50) -> str:
        """
        Get recent logs formatted for display.
        
        Args:
            log_type: Filter by log type (None for all)
            limit: Maximum number of logs to return
        
        Returns:
            Formatted log string
        """
        logs = self._log_buffer
        
        # Filter by type if specified
        if log_type and log_type != "all":
            logs = [log for log in logs if log["type"] == log_type]
        
        # Get last N logs
        logs = logs[-limit:]
        
        if not logs:
            return "No logs available"
        
        # Format logs
        formatted = []
        for log in reversed(logs):  # Most recent first
            timestamp = log["timestamp"]
            log_type = log["type"]
            data = log["data"]
            
            formatted.append(f"[{timestamp}] {log_type.upper()}")
            formatted.append(json.dumps(data, indent=2))
            formatted.append("-" * 80)
        
        return "\n".join(formatted)
    
    def get_tool_analytics_summary(self) -> str:
        """
        Get tool usage analytics summary.
        
        Returns:
            Formatted analytics string
        """
        try:
            stats = self.analytics.get_all_statistics()
            
            if not stats:
                return "No tool usage data available yet"
            
            # Sort by usage count
            sorted_tools = sorted(
                stats.items(),
                key=lambda x: x[1]["usage_count"],
                reverse=True
            )
            
            lines = ["# Tool Usage Analytics\n"]
            lines.append(f"Total tools tracked: {len(stats)}\n")
            lines.append("\n## Most Used Tools\n")
            
            for tool_name, tool_stats in sorted_tools[:10]:
                lines.append(f"\n### {tool_name}")
                lines.append(f"- Usage count: {tool_stats['usage_count']}")
                lines.append(f"- Success rate: {tool_stats['success_rate']:.1f}%")
                lines.append(f"- Avg duration: {tool_stats['avg_duration']:.2f}s")
                lines.append(f"- Priority score: {tool_stats['priority_score']:.2f}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error loading analytics: {e}"
    
    def get_token_statistics(self) -> str:
        """
        Get token usage statistics from logs.
        
        Returns:
            Formatted token stats string
        """
        token_logs = [log for log in self._log_buffer if log["type"] == "token_usage"]
        
        if not token_logs:
            return "No token usage data available yet"
        
        total_prompt = sum(log["data"].get("prompt_tokens", 0) for log in token_logs)
        total_completion = sum(log["data"].get("completion_tokens", 0) for log in token_logs)
        total_tokens = sum(log["data"].get("total_tokens", 0) for log in token_logs)
        
        lines = ["# Token Usage Statistics\n"]
        lines.append(f"Total queries: {len(token_logs)}")
        lines.append(f"Total prompt tokens: {total_prompt:,}")
        lines.append(f"Total completion tokens: {total_completion:,}")
        lines.append(f"Total tokens: {total_tokens:,}")
        lines.append(f"\nAverage tokens per query: {total_tokens / len(token_logs):.0f}")
        
        # Get last cumulative value if available
        last_log = token_logs[-1]
        if "cumulative_session_tokens" in last_log["data"]:
            cumulative = last_log["data"]["cumulative_session_tokens"]
            lines.append(f"Cumulative session tokens: {cumulative:,}")
        
        return "\n".join(lines)
    
    def get_performance_statistics(self) -> str:
        """
        Get performance statistics from logs.
        
        Returns:
            Formatted performance stats string
        """
        perf_logs = [log for log in self._log_buffer if log["type"] == "performance"]
        
        if not perf_logs:
            return "No performance data available yet"
        
        durations = [log["data"].get("total_duration_ms", 0) for log in perf_logs]
        
        lines = ["# Performance Statistics\n"]
        lines.append(f"Total operations: {len(perf_logs)}")
        lines.append(f"Average duration: {sum(durations) / len(durations):.2f}ms")
        lines.append(f"Min duration: {min(durations):.2f}ms")
        lines.append(f"Max duration: {max(durations):.2f}ms")
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        p50 = sorted_durations[len(sorted_durations) // 2]
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)]
        
        lines.append(f"\nP50 (median): {p50:.2f}ms")
        lines.append(f"P95: {p95:.2f}ms")
        lines.append(f"P99: {p99:.2f}ms")
        
        return "\n".join(lines)
    
    def _build_tab(
        self,
        emoji: str,
        title: str,
        description: str,
        fetch_fn_name: str,
        output_type: str,
        has_filters: bool = False
    ) -> None:
        """
        Build a single debug tab with refresh functionality.
        
        Args:
            emoji: Tab emoji icon
            title: Tab title
            description: Tab description text
            fetch_fn_name: Name of method to fetch data
            output_type: Type of output component ("textbox" or "markdown")
            has_filters: Whether tab has filter controls (logs only)
        """
        with gr.Tab(f"{emoji} {title}"):
            gr.Markdown(f"### {description}")
            
            # Special handling for logs tab filters
            if has_filters:
                with gr.Row():
                    log_type_filter = gr.Dropdown(
                        choices=["all", "tool_selection", "tool_execution", "token_usage", "performance"],
                        value="all",
                        label="Filter by Type"
                    )
                    log_limit = gr.Slider(
                        minimum=10,
                        maximum=100,
                        value=50,
                        step=10,
                        label="Number of Logs"
                    )
                    refresh_btn = gr.Button("🔄 Refresh", variant="primary")
            else:
                refresh_btn = gr.Button("🔄 Refresh", variant="primary")
            
            # Create output component
            fetch_fn = getattr(self, fetch_fn_name)
            if output_type == "textbox":
                output = gr.Textbox(
                    label="Logs",
                    lines=20,
                    max_lines=30,
                    value=fetch_fn(),
                    interactive=False
                )
            else:
                output = gr.Markdown(value=fetch_fn())
            
            # Wire up refresh button
            if has_filters:
                refresh_btn.click(
                    fn=fetch_fn,
                    inputs=[log_type_filter, log_limit],
                    outputs=output
                )
            else:
                refresh_btn.click(fn=fetch_fn, outputs=output)
    
    def create_ui(self) -> gr.Blocks:
        """
        Create Gradio debug UI.
        
        Returns:
            Gradio Blocks interface
        """
        with gr.Blocks(title="GCM Agent Debug Dashboard") as debug_interface:
            gr.Markdown("# 🔍 GCM Agent Debug Dashboard")
            gr.Markdown("Monitor agent observability metrics, logs, and analytics")
            
            with gr.Tabs():
                for emoji, title, desc, fetch_fn, output_type, has_filters in _TAB_CONFIGS:
                    self._build_tab(emoji, title, desc, fetch_fn, output_type, has_filters)
            
            gr.Markdown("---")
            gr.Markdown("*Debug dashboard updates when you click refresh buttons*")
        
        return debug_interface


def create_debug_ui() -> gr.Blocks:
    """
    Create and return debug UI interface using the global instance.
    
    Returns:
        Gradio Blocks interface
    """
    debug_ui = get_debug_ui_instance()
    return debug_ui.create_ui()


# Global debug UI instance for integration with main app
_debug_ui_instance: Optional[DebugUI] = None


def get_debug_ui_instance() -> DebugUI:
    """
    Get or create global debug UI instance.
    
    Returns:
        DebugUI instance
    """
    global _debug_ui_instance
    if _debug_ui_instance is None:
        _debug_ui_instance = DebugUI()
    return _debug_ui_instance