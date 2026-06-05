"""Configuration package for secure GCM agent settings management."""

# Made with Bob
# 2026-06-05 19:54 UTC - Added exports for configuration management
# 2026-06-05 20:40 UTC - Updated for Fernet encryption (removed KeyringBackendError, added EncryptionError, FilePermissionError)

from gcm_agent.config.storage import (
    SecureStorage,
    get_storage,
    StorageError,
    EncryptionError,
    FilePermissionError,
    CredentialNotFoundError,
)

from gcm_agent.config.config_manager import (
    ConfigManager,
    get_config_manager,
    GCMServerConfig,
    AuthConfig,
    WatsonXConfig,
    AgentConfig,
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
)

__all__ = [
    # Storage
    "SecureStorage",
    "get_storage",
    "StorageError",
    "EncryptionError",
    "FilePermissionError",
    "CredentialNotFoundError",
    # Config Manager
    "ConfigManager",
    "get_config_manager",
    "GCMServerConfig",
    "AuthConfig",
    "WatsonXConfig",
    "AgentConfig",
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
]
