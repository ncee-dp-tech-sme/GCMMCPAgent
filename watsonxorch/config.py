"""Configuration management for WatsonX Orchestrate integration.

Made with Bob
2026-06-10 02:47 UTC - Initial implementation of orchestrate configuration
"""

from typing import Optional
from pydantic import BaseModel, Field
import os


class OrchestrateConfig(BaseModel):
    """Configuration for WatsonX Orchestrate integration."""
    
    # API Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="API server host address",
        example="0.0.0.0"
    )
    port: int = Field(
        default=8000,
        description="API server port",
        example=8000
    )
    
    # CORS Configuration
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS for cross-origin requests"
    )
    cors_origins: list = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins"
    )
    
    # Session Management
    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds (default: 1 hour)"
    )
    max_sessions: int = Field(
        default=100,
        description="Maximum number of concurrent sessions"
    )
    
    # Performance Configuration
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads"
    )
    request_timeout: int = Field(
        default=300,
        description="Request timeout in seconds (default: 5 minutes)"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    @classmethod
    def from_env(cls) -> "OrchestrateConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("ORCHESTRATE_HOST", "0.0.0.0"),
            port=int(os.getenv("ORCHESTRATE_PORT", "8000")),
            cors_enabled=os.getenv("ORCHESTRATE_CORS_ENABLED", "true").lower() == "true",
            cors_origins=os.getenv("ORCHESTRATE_CORS_ORIGINS", "*").split(","),
            session_timeout=int(os.getenv("ORCHESTRATE_SESSION_TIMEOUT", "3600")),
            max_sessions=int(os.getenv("ORCHESTRATE_MAX_SESSIONS", "100")),
            max_workers=int(os.getenv("ORCHESTRATE_MAX_WORKERS", "4")),
            request_timeout=int(os.getenv("ORCHESTRATE_REQUEST_TIMEOUT", "300")),
            log_level=os.getenv("ORCHESTRATE_LOG_LEVEL", "INFO"),
            log_format=os.getenv("ORCHESTRATE_LOG_FORMAT", "json"),
        )

# Made with Bob
