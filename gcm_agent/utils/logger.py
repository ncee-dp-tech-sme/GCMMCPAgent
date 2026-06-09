"""Logging utilities module for structured, security-aware logging across the GCM agent."""

# Made with Bob
# 2026-06-05 19:52 UTC - Initial implementation of structured logging utility
# 2026-06-05 21:31 UTC - Added environment variable support for log level and file logging configuration
# 2026-06-08 21:45 UTC - Added structured logging for observability (Phase 4)
# 2026-06-08 21:56 UTC - Fixed import: use inspect.iscoroutinefunction instead of functools
# 2026-06-08 22:08 UTC - Integrated ObservabilityLogger with debug UI
# 2026-06-09 21:05 UTC - Refactored logger caching, handler setup, and performance timing

import logging
import logging.handlers
import sys
import os
import json
import time
import functools
import inspect
from pathlib import Path
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING, List
from datetime import datetime, timezone
import uuid

if TYPE_CHECKING:
    from gcm_agent.ui.debug_ui import DebugUI


class StructuredLogger:
    """
    Structured logging utility with console and file logging support.
    Provides configurable log levels and formatted output with timestamps.
    """

    _loggers = {}  # Cache for logger instances

    @staticmethod
    def _create_formatter() -> logging.Formatter:
        """Create standard formatter for handlers."""
        return logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    @staticmethod
    def _add_handler(
        logger: logging.Logger,
        handler: logging.Handler,
        level: int,
        formatter: logging.Formatter,
    ) -> None:
        """
        Configure and add a handler to a logger.
        
        Args:
            logger: Logger instance
            handler: Handler to add
            level: Logging level for handler
            formatter: Formatter for handler
        """
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    @classmethod
    def get_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        console: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB default
        backup_count: int = 5,
    ) -> logging.Logger:
        """
        Get or create a logger instance with specified configuration.
        Uses caching to avoid reconfiguring existing loggers.

        Args:
            name: Logger name (typically module name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for file logging
            console: Enable console logging (default: True)
            max_bytes: Maximum log file size before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)

        Returns:
            Configured logger instance
        """
        # Return cached logger if exists and already has handlers
        if name in cls._loggers:
            logger = cls._loggers[name]
            if logger.handlers:
                return logger

        # Create new logger or get existing one
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs

        # Skip reconfiguration if logger already has handlers
        if logger.handlers:
            cls._loggers[name] = logger
            return logger

        # Create formatter
        formatter = cls._create_formatter()

        # Add console handler if enabled
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            cls._add_handler(logger, console_handler, level, formatter)

        # Add rotating file handler if log_file specified
        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                mode="a",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            cls._add_handler(logger, file_handler, level, formatter)

        # Cache logger
        cls._loggers[name] = logger

        return logger

    @classmethod
    def set_level(cls, name: str, level: int) -> None:
        """
        Update logging level for an existing logger.

        Args:
            name: Logger name
            level: New logging level
        """
        if name in cls._loggers:
            logger = cls._loggers[name]
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)

    @classmethod
    def add_file_handler(
        cls,
        name: str,
        log_file: str,
        level: Optional[int] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """
        Add rotating file handler to an existing logger.

        Args:
            name: Logger name
            log_file: File path for logging
            level: Optional logging level (uses logger's level if not specified)
            max_bytes: Maximum log file size before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        if name not in cls._loggers:
            raise ValueError(f"Logger '{name}' not found")

        logger = cls._loggers[name]

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            mode="a",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        # Use same formatter as existing handlers or create new one
        formatter = (
            logger.handlers[0].formatter if logger.handlers else cls._create_formatter()
        )

        # Add handler using helper method
        cls._add_handler(logger, file_handler, level if level is not None else logger.level, formatter)

    @classmethod
    def remove_file_handlers(cls, name: str) -> None:
        """
        Remove all file handlers (including rotating file handlers) from a logger.

        Args:
            name: Logger name
        """
        if name not in cls._loggers:
            return

        logger = cls._loggers[name]
        # Remove file handlers and rotating file handlers, keep console handlers
        logger.handlers = [
            h for h in logger.handlers
            if not isinstance(h, (logging.FileHandler, logging.handlers.RotatingFileHandler))
        ]


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """
    Convenience function to get a logger instance.

    Args:
        name: Logger name (typically module name)
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging
        console: Enable console logging (default: True)

    Returns:
        Configured logger instance
    """
    return StructuredLogger.get_logger(name, level, log_file, console)


def sanitize_sensitive_data(message: str) -> str:
    """
    Sanitize sensitive data from log messages.
    Replaces common sensitive patterns with masked values.

    Args:
        message: Log message to sanitize

    Returns:
        Sanitized message
    """
    import re

    # Patterns to sanitize
    patterns = [
        (r"password['\"]?\s*[:=]\s*['\"]?([^'\"}\s,]+)", "password=***"),
        (r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([^'\"}\s,]+)", "api_key=***"),
        (r"secret['\"]?\s*[:=]\s*['\"]?([^'\"}\s,]+)", "secret=***"),
        (r"token['\"]?\s*[:=]\s*['\"]?([^'\"}\s,]+)", "token=***"),
        (r"bearer\s+([a-zA-Z0-9\-._~+/]+=*)", "bearer ***"),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def _get_log_level_from_env() -> int:
    """
    Get log level from environment variable.
    
    Returns:
        Logging level (default: INFO)
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_name, logging.INFO)


def _get_log_file_path(module_name: str) -> Optional[str]:
    """
    Get log file path from environment configuration.
    
    Args:
        module_name: Name of the module (e.g., 'gcm_agent.auth')
    
    Returns:
        Log file path if file logging is enabled, None otherwise
    """
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    
    if not log_to_file:
        return None
    
    log_dir = os.getenv("LOG_DIR", "logs")
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # Extract module suffix (e.g., 'auth' from 'gcm_agent.auth')
    module_suffix = module_name.split(".")[-1] if "." in module_name else module_name
    
    log_file = f"{log_dir}/{module_suffix}_{timestamp}.log"
    return log_file


# Pre-configured loggers for common modules
def get_config_logger() -> logging.Logger:
    """Get logger for configuration module."""
    level = _get_log_level_from_env()
    log_file = _get_log_file_path("gcm_agent.config")
    return get_logger("gcm_agent.config", level=level, log_file=log_file)


def get_auth_logger() -> logging.Logger:
    """Get logger for authentication module."""
    level = _get_log_level_from_env()
    log_file = _get_log_file_path("gcm_agent.auth")
    return get_logger("gcm_agent.auth", level=level, log_file=log_file)


def get_mcp_logger() -> logging.Logger:
    """Get logger for MCP client module."""
    level = _get_log_level_from_env()
    log_file = _get_log_file_path("gcm_agent.mcp")
    return get_logger("gcm_agent.mcp", level=level, log_file=log_file)


def get_agent_logger() -> logging.Logger:
    """Get logger for agent module."""
    level = _get_log_level_from_env()
    log_file = _get_log_file_path("gcm_agent.agent")
    return get_logger("gcm_agent.agent", level=level, log_file=log_file)



# Observability Features (Phase 4)

class ObservabilityLogger:
    """
    Enhanced logging for observability with structured JSON logging,
    tool selection reasoning, token tracking, and performance metrics.
    """
    
    def __init__(self, logger: logging.Logger, debug_ui: Optional['DebugUI'] = None):
        """
        Initialize observability logger.
        
        Args:
            logger: Base logger instance to use
            debug_ui: Optional debug UI instance for real-time log display
        """
        self.logger = logger
        self._session_id = str(uuid.uuid4())[:8]
        self._debug_ui = debug_ui
    
    def _send_to_debug_ui(self, log_type: str, data: Dict[str, Any]) -> None:
        """
        Send log entry to debug UI if available.
        
        Args:
            log_type: Type of log (tool_selection, tool_execution, token_usage, performance)
            data: Log data dictionary
        """
        if self._debug_ui is not None:
            try:
                self._debug_ui.add_log_entry(log_type, data)
            except Exception as e:
                self.logger.warning(f"Failed to send log to debug UI: {e}")
    
    def log_tool_selection(
        self,
        query: str,
        selected_tool: str,
        reasoning: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        confidence: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log tool selection with reasoning.
        
        Args:
            query: User query
            selected_tool: Name of selected tool
            reasoning: LLM's reasoning for tool selection
            alternatives: Alternative tools considered
            confidence: Confidence level (high/medium/low)
            metadata: Additional metadata
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": self._session_id,
            "event": "tool_selection",
            "query": query[:200],  # Truncate long queries
            "selected_tool": selected_tool,
            "reasoning": reasoning,
            "alternatives_considered": alternatives or [],
            "confidence": confidence or "unknown",
        }
        
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"TOOL_SELECTION: {json.dumps(log_data)}")
        self._send_to_debug_ui("tool_selection", log_data)
    
    def log_tool_execution(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        result_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log tool execution results.
        
        Args:
            tool_name: Name of executed tool
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
            result_summary: Brief summary of result
            metadata: Additional metadata
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": self._session_id,
            "event": "tool_execution",
            "tool_name": tool_name,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
        
        if error:
            log_data["error"] = error
        if result_summary:
            log_data["result_summary"] = result_summary[:200]  # Truncate
        if metadata:
            log_data["metadata"] = metadata
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"TOOL_EXECUTION: {json.dumps(log_data)}")
        self._send_to_debug_ui("tool_execution", log_data)
    
    def log_token_usage(
        self,
        query: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cumulative_tokens: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log token usage metrics.
        
        Args:
            query: User query
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens used
            cumulative_tokens: Cumulative session tokens
            estimated_cost_usd: Estimated cost in USD
            metadata: Additional metadata
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": self._session_id,
            "event": "token_usage",
            "query": query[:200],  # Truncate
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        
        if cumulative_tokens is not None:
            log_data["cumulative_session_tokens"] = cumulative_tokens
        if estimated_cost_usd is not None:
            log_data["estimated_cost_usd"] = round(estimated_cost_usd, 4)
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"TOKEN_USAGE: {json.dumps(log_data)}")
        self._send_to_debug_ui("token_usage", log_data)
    
    def log_performance_metrics(
        self,
        query: str,
        total_duration_ms: float,
        breakdown: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log performance metrics.
        
        Args:
            query: User query
            total_duration_ms: Total duration in milliseconds
            breakdown: Timing breakdown by operation
            metadata: Additional metadata
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "session_id": self._session_id,
            "event": "performance_metrics",
            "query": query[:200],  # Truncate
            "total_duration_ms": round(total_duration_ms, 2),
        }
        
        if breakdown:
            log_data["timings"] = {k: round(v, 2) for k, v in breakdown.items()}
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"PERFORMANCE: {json.dumps(log_data)}")
        self._send_to_debug_ui("performance", log_data)


def timed_operation(operation_name: Optional[str] = None, threshold_ms: float = 100.0) -> Callable:
    """
    Decorator to time operations and log performance metrics.
    Uses time.perf_counter() for higher-resolution timing.
    
    Args:
        operation_name: Name of operation (defaults to function name)
        threshold_ms: Minimum duration in milliseconds to log (default: 100ms)
    
    Returns:
        Decorated function
    
    Example:
        @timed_operation("load_tools", threshold_ms=50.0)
        async def load_tools(self):
            # ... operation code ...
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Cache logger once per decorator invocation
        logger = get_agent_logger()
        op_name = operation_name or func.__name__
        
        def _log_timing_and_execute(is_async: bool):
            """
            Helper function to handle timing and logging for both sync and async functions.
            
            Args:
                is_async: Whether the function is async
            
            Returns:
                Wrapper function
            """
            @functools.wraps(func)
            async def async_impl(*args, **kwargs):
                start_time = time.perf_counter()
                
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Log if duration exceeds threshold
                    if duration_ms > threshold_ms:
                        logger.debug(f"Operation '{op_name}' took {duration_ms:.2f}ms")
                    
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.warning(f"Operation '{op_name}' failed after {duration_ms:.2f}ms: {e}")
                    raise
            
            @functools.wraps(func)
            def sync_impl(*args, **kwargs):
                start_time = time.perf_counter()
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Log if duration exceeds threshold
                    if duration_ms > threshold_ms:
                        logger.debug(f"Operation '{op_name}' took {duration_ms:.2f}ms")
                    
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    logger.warning(f"Operation '{op_name}' failed after {duration_ms:.2f}ms: {e}")
                    raise
            
            return async_impl if is_async else sync_impl
        
        # Return appropriate wrapper based on function type
        return _log_timing_and_execute(inspect.iscoroutinefunction(func))
    
    return decorator


def get_observability_logger(name: str, debug_ui: Optional['DebugUI'] = None) -> ObservabilityLogger:
    """
    Get observability logger for a module.
    
    Args:
        name: Module name
        debug_ui: Optional debug UI instance for real-time log display
    
    Returns:
        ObservabilityLogger instance
    """
    base_logger = get_logger(name)
    return ObservabilityLogger(base_logger, debug_ui=debug_ui)

def get_ui_logger() -> logging.Logger:
    """Get logger for UI module."""
    level = _get_log_level_from_env()
    log_file = _get_log_file_path("gcm_agent.ui")
    return get_logger("gcm_agent.ui", level=level, log_file=log_file)
