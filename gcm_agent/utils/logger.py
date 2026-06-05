"""Logging utilities module for structured, security-aware logging across the GCM agent."""

# Made with Bob
# 2026-06-05 19:52 UTC - Initial implementation of structured logging utility

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class StructuredLogger:
    """
    Structured logging utility with console and file logging support.
    Provides configurable log levels and formatted output with timestamps.
    """

    _loggers = {}  # Cache for logger instances

    @classmethod
    def get_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[str] = None,
        console: bool = True,
    ) -> logging.Logger:
        """
        Get or create a logger instance with specified configuration.

        Args:
            name: Logger name (typically module name)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for file logging
            console: Enable console logging (default: True)

        Returns:
            Configured logger instance
        """
        # Return cached logger if exists
        if name in cls._loggers:
            return cls._loggers[name]

        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs

        # Clear existing handlers
        logger.handlers.clear()

        # Create formatter with structured format
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Add console handler if enabled
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # Add file handler if log_file specified
        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

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
    def add_file_handler(cls, name: str, log_file: str, level: Optional[int] = None) -> None:
        """
        Add file handler to an existing logger.

        Args:
            name: Logger name
            log_file: File path for logging
            level: Optional logging level (uses logger's level if not specified)
        """
        if name not in cls._loggers:
            raise ValueError(f"Logger '{name}' not found")

        logger = cls._loggers[name]

        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(level if level is not None else logger.level)

        # Use same formatter as existing handlers
        if logger.handlers:
            file_handler.setFormatter(logger.handlers[0].formatter)
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    @classmethod
    def remove_file_handlers(cls, name: str) -> None:
        """
        Remove all file handlers from a logger.

        Args:
            name: Logger name
        """
        if name not in cls._loggers:
            return

        logger = cls._loggers[name]
        # Remove only file handlers, keep console handlers
        logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.FileHandler)]


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


# Pre-configured loggers for common modules
def get_config_logger() -> logging.Logger:
    """Get logger for configuration module."""
    return get_logger("gcm_agent.config", level=logging.INFO)


def get_auth_logger() -> logging.Logger:
    """Get logger for authentication module."""
    return get_logger("gcm_agent.auth", level=logging.INFO)


def get_mcp_logger() -> logging.Logger:
    """Get logger for MCP client module."""
    return get_logger("gcm_agent.mcp", level=logging.INFO)


def get_agent_logger() -> logging.Logger:
    """Get logger for agent module."""
    return get_logger("gcm_agent.agent", level=logging.INFO)


def get_ui_logger() -> logging.Logger:
    """Get logger for UI module."""
    return get_logger("gcm_agent.ui", level=logging.INFO)
