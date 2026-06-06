"""Configuration manager module for secure retrieval, validation, and caching of GCM agent settings."""

# Made with Bob
# 2026-06-05 19:53 UTC - Initial implementation of configuration manager with Pydantic models
# 2026-06-05 21:02 UTC - Separated Keycloak configuration and added independent SSL verification
# 2026-06-05 21:50 UTC - Added WatsonX URL configuration field
# 2026-06-06 02:43 UTC - Added WatsonX SSL verification configuration support
# 2026-06-06 04:26 UTC - Fixed "need more steps" issue: increased max_iterations to 20, disabled discovery_mode by default

import json
import threading
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator, ValidationError

from gcm_agent.config.storage import get_storage, StorageError
from gcm_agent.utils.logger import get_config_logger


# Custom exceptions for configuration operations
class ConfigurationError(Exception):
    """Base exception for configuration operations."""
    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration values are invalid."""
    pass


# Pydantic configuration models
class KeycloakConfig(BaseModel):
    """Configuration for Keycloak authentication server."""
    
    url: str = Field(..., description="Keycloak server URL (e.g., https://keycloak.example.com)")
    port: int = Field(default=443, ge=1, le=65535, description="Keycloak server port")
    realm: str = Field(default="master", description="Keycloak realm name")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates for Keycloak")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class GCMServerConfig(BaseModel):
    """Configuration for GCM MCP server."""
    
    url: str = Field(..., description="GCM server URL (e.g., https://gcm.example.com)")
    hostname: str = Field(..., description="GCM server hostname")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates for GCM")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")

    @validator("hostname")
    def validate_hostname(cls, v):
        """Validate hostname is not empty."""
        if not v or not v.strip():
            raise ValueError("Hostname cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class AuthConfig(BaseModel):
    """Configuration for authentication (passwords stored separately in keyring)."""
    
    username: str = Field(..., description="GCM username")
    client_id: str = Field(..., description="OAuth2 client ID")

    @validator("username", "client_id")
    def validate_not_empty(cls, v):
        """Validate fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class WatsonXConfig(BaseModel):
    """Configuration for WatsonX LLM (API key stored separately in keyring)."""
    
    url: str = Field(
        default="https://us-south.ml.cloud.ibm.com",
        description="WatsonX API URL"
    )
    project_id: str = Field(..., description="WatsonX project ID")
    model: str = Field(
        default="ibm/granite-13b-chat-v2",
        description="WatsonX model identifier"
    )
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates for WatsonX")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v.rstrip("/")

    @validator("project_id")
    def validate_project_id(cls, v):
        """Validate project ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Project ID cannot be empty")
        return v.strip()

    @validator("model")
    def validate_model(cls, v):
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI LLM (API key stored separately in keyring)."""
    
    model: str = Field(
        default="gpt-4o",
        description="OpenAI model identifier"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=128000,
        description="Maximum tokens in response"
    )

    @validator("model")
    def validate_model(cls, v):
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class LLMConfig(BaseModel):
    """Configuration for LLM provider selection."""
    
    provider: str = Field(
        default="watsonx",
        description="LLM provider (watsonx or openai)"
    )

    @validator("provider")
    def validate_provider(cls, v):
        """Validate provider is supported."""
        if v not in ["watsonx", "openai"]:
            raise ValueError("Provider must be 'watsonx' or 'openai'")
        return v.lower()

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class AgentConfig(BaseModel):
    """Configuration for agent behavior."""
    
    # Fix for "need more steps" issue: discovery_mode disabled by default for faster responses
    # Enable discovery_mode for complex queries that need dynamic tool loading
    discovery_mode: bool = Field(
        default=False,
        description="Enable discovery mode (dynamic tool loading). Disable for faster responses with all tools loaded upfront."
    )
    # Fix for "need more steps" issue: increased from 10 to 20 to handle broad queries
    # Discovery mode workflows need ~15-20 iterations for complex queries like "all keys/assets"
    max_iterations: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum agent iterations. Increased to handle broad queries like 'all keys/assets'."
    )
    timeout: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Agent timeout in seconds"
    )

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class ConfigManager:
    """
    Thread-safe singleton configuration manager.
    Manages secure storage and retrieval of GCM agent configuration.
    """

    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement thread-safe singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration manager."""
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self.logger = get_config_logger()
            self.storage = get_storage()
            self._config_cache: Optional[Dict[str, Any]] = None
            self._initialized = True
            self.logger.debug("ConfigManager initialized")

    def _load_config_from_storage(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from secure storage.

        Returns:
            Configuration dictionary or None if not found
        """
        try:
            config_json = self.storage.get_credential("config")
            if config_json:
                config = json.loads(config_json)
                self.logger.debug("Loaded configuration from storage")
                return config
            return None
        except (StorageError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None

    def _save_config_to_storage(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to secure storage.

        Args:
            config: Configuration dictionary

        Raises:
            StorageError: If save operation fails
        """
        try:
            config_json = json.dumps(config, indent=2)
            self.storage.store_credential("config", config_json)
            self._config_cache = config
            self.logger.info("Saved configuration to storage")
        except (StorageError, TypeError) as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise StorageError(f"Failed to save configuration: {e}") from e

    def load_config(self) -> bool:
        """
        Load configuration from storage into cache.

        Returns:
            True if configuration was loaded, False otherwise
        """
        self._config_cache = self._load_config_from_storage()
        return self._config_cache is not None

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save complete configuration to storage.

        Args:
            config: Configuration dictionary

        Raises:
            InvalidConfigError: If configuration is invalid
            StorageError: If save operation fails
        """
        # Validate configuration structure
        required_sections = ["keycloak", "gcm_server", "auth", "watsonx", "agent"]
        for section in required_sections:
            if section not in config:
                raise InvalidConfigError(f"Missing required section: {section}")

        self._save_config_to_storage(config)

    def get_keycloak_config(self) -> KeycloakConfig:
        """
        Get Keycloak server configuration.

        Returns:
            KeycloakConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "keycloak" not in self._config_cache:
            raise MissingConfigError("Keycloak configuration not found")

        try:
            return KeycloakConfig(**self._config_cache["keycloak"])
        except ValidationError as e:
            self.logger.error(f"Invalid Keycloak configuration: {e}")
            raise InvalidConfigError(f"Invalid Keycloak configuration: {e}") from e

    def get_gcm_config(self) -> GCMServerConfig:
        """
        Get GCM server configuration.

        Returns:
            GCMServerConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "gcm_server" not in self._config_cache:
            raise MissingConfigError("GCM server configuration not found")

        try:
            return GCMServerConfig(**self._config_cache["gcm_server"])
        except ValidationError as e:
            self.logger.error(f"Invalid GCM server configuration: {e}")
            raise InvalidConfigError(f"Invalid GCM server configuration: {e}") from e

    def get_auth_config(self) -> AuthConfig:
        """
        Get authentication configuration (without passwords).

        Returns:
            AuthConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "auth" not in self._config_cache:
            raise MissingConfigError("Authentication configuration not found")

        try:
            return AuthConfig(**self._config_cache["auth"])
        except ValidationError as e:
            self.logger.error(f"Invalid authentication configuration: {e}")
            raise InvalidConfigError(f"Invalid authentication configuration: {e}") from e

    def get_watsonx_config(self) -> WatsonXConfig:
        """
        Get WatsonX configuration (without API key).

        Returns:
            WatsonXConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "watsonx" not in self._config_cache:
            raise MissingConfigError("WatsonX configuration not found")

        try:
            return WatsonXConfig(**self._config_cache["watsonx"])
        except ValidationError as e:
            self.logger.error(f"Invalid WatsonX configuration: {e}")
            raise InvalidConfigError(f"Invalid WatsonX configuration: {e}") from e
    def get_llm_config(self) -> LLMConfig:
        """
        Get LLM provider configuration.

        Returns:
            LLMConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "llm" not in self._config_cache:
            # Return default LLM config if not found (watsonx)
            self.logger.debug("LLM configuration not found, using default (watsonx)")
            return LLMConfig()

        try:
            return LLMConfig(**self._config_cache["llm"])
        except ValidationError as e:
            self.logger.error(f"Invalid LLM configuration: {e}")
            raise InvalidConfigError(f"Invalid LLM configuration: {e}") from e

    def get_openai_config(self) -> OpenAIConfig:
        """
        Get OpenAI configuration (without API key).

        Returns:
            OpenAIConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "openai" not in self._config_cache:
            # Return default OpenAI config if not found
            self.logger.debug("OpenAI configuration not found, using defaults")
            return OpenAIConfig()

        try:
            return OpenAIConfig(**self._config_cache["openai"])
        except ValidationError as e:
            self.logger.error(f"Invalid OpenAI configuration: {e}")
            raise InvalidConfigError(f"Invalid OpenAI configuration: {e}") from e


    def get_agent_config(self) -> AgentConfig:
        """
        Get agent configuration.

        Returns:
            AgentConfig instance

        Raises:
            MissingConfigError: If configuration is not found
            InvalidConfigError: If configuration is invalid
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None or "agent" not in self._config_cache:
            # Return default agent config if not found
            self.logger.debug("Agent configuration not found, using defaults")
            return AgentConfig()

        try:
            return AgentConfig(**self._config_cache["agent"])
        except ValidationError as e:
            self.logger.error(f"Invalid agent configuration: {e}")
            raise InvalidConfigError(f"Invalid agent configuration: {e}") from e

    def update_gcm_config(self, config: GCMServerConfig) -> None:
        """
        Update GCM server configuration.

        Args:
            config: GCMServerConfig instance

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        self._config_cache["gcm_server"] = config.dict()
        self._save_config_to_storage(self._config_cache)
        self.logger.info("Updated GCM server configuration")

    def update_keycloak_config(self, config: KeycloakConfig) -> None:
        """
        Update Keycloak server configuration.

        Args:
            config: KeycloakConfig instance

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        self._config_cache["keycloak"] = config.dict()
        self._save_config_to_storage(self._config_cache)
        self.logger.info("Updated Keycloak configuration")

    def update_auth_config(self, config: AuthConfig, password: str, client_secret: str) -> None:
        """
        Update authentication configuration including sensitive credentials.

        Args:
            config: AuthConfig instance
            password: GCM user password
            client_secret: OAuth2 client secret

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        # Store non-sensitive config
        self._config_cache["auth"] = config.dict()
        self._save_config_to_storage(self._config_cache)

        # Store sensitive credentials separately
        self.storage.store_credential("gcm_password", password)
        self.storage.store_credential("gcm_client_secret", client_secret)
        self.logger.info("Updated authentication configuration")

    def update_watsonx_config(self, config: WatsonXConfig, api_key: str) -> None:
        """
        Update WatsonX configuration including API key.

        Args:
            config: WatsonXConfig instance
            api_key: WatsonX API key

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        # Store non-sensitive config
        self._config_cache["watsonx"] = config.dict()
        self._save_config_to_storage(self._config_cache)

        # Store API key separately
        self.storage.store_credential("watsonx_api_key", api_key)
        self.logger.info("Updated WatsonX configuration")

    def update_agent_config(self, config: AgentConfig) -> None:
        """
        Update agent configuration.

        Args:
            config: AgentConfig instance

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        self._config_cache["agent"] = config.dict()
        self._save_config_to_storage(self._config_cache)

    def update_llm_config(self, config: LLMConfig) -> None:
        """
        Update LLM provider configuration.

        Args:
            config: LLMConfig instance

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        self._config_cache["llm"] = config.dict()
        self._save_config_to_storage(self._config_cache)
        self.logger.info(f"Updated LLM configuration (provider={config.provider})")

    def update_openai_config(self, config: OpenAIConfig, api_key: str) -> None:
        """
        Update OpenAI configuration including API key.

        Args:
            config: OpenAIConfig instance
            api_key: OpenAI API key

        Raises:
            StorageError: If save operation fails
        """
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        # Store non-sensitive config
        self._config_cache["openai"] = config.dict()
        self._save_config_to_storage(self._config_cache)

        # Store API key separately
        self.storage.store_credential("openai_api_key", api_key)
        self.logger.info("Updated OpenAI configuration")
        self.logger.info("Updated agent configuration")

    def get_password(self) -> Optional[str]:
        """
        Get GCM user password from secure storage.

        Returns:
            Password if found, None otherwise
        """
        try:
            return self.storage.get_credential("gcm_password")
        except StorageError as e:
            self.logger.error(f"Failed to retrieve password: {e}")
            return None

    def get_client_secret(self) -> Optional[str]:
        """
        Get OAuth2 client secret from secure storage.

        Returns:
            Client secret if found, None otherwise
        """
        try:
            return self.storage.get_credential("gcm_client_secret")
        except StorageError as e:
            self.logger.error(f"Failed to retrieve client secret: {e}")
            return None

    def get_watsonx_api_key(self) -> Optional[str]:
        """
        Get WatsonX API key from secure storage.

        Returns:
            API key if found, None otherwise
        """
        try:
            return self.storage.get_credential("watsonx_api_key")
        except StorageError as e:
            self.logger.error(f"Failed to retrieve WatsonX API key: {e}")
            return None

    def get_openai_api_key(self) -> Optional[str]:
        """
        Get OpenAI API key from secure storage.

        Returns:
            API key if found, None otherwise
        """
        try:
            return self.storage.get_credential("openai_api_key")
        except StorageError as e:
            self.logger.error(f"Failed to retrieve OpenAI API key: {e}")
            return None
        except StorageError as e:
            self.logger.error(f"Failed to retrieve WatsonX API key: {e}")
            return None

    def is_configured(self) -> bool:
        """
        Check if all required configuration exists.

        Returns:
            True if fully configured, False otherwise
        """
        try:
            # Check non-sensitive config
            self.get_keycloak_config()
            self.get_gcm_config()
            self.get_auth_config()

            # Check sensitive credentials
            if not self.get_password():
                self.logger.debug("Missing GCM password")
                return False
            if not self.get_client_secret():
                self.logger.debug("Missing client secret")
                return False

            # Check LLM provider configuration
            llm_config = self.get_llm_config()
            if llm_config.provider == "watsonx":
                self.get_watsonx_config()
                if not self.get_watsonx_api_key():
                    self.logger.debug("Missing WatsonX API key")
                    return False
            elif llm_config.provider == "openai":
                self.get_openai_config()
                if not self.get_openai_api_key():
                    self.logger.debug("Missing OpenAI API key")
                    return False

            return True
        except (MissingConfigError, InvalidConfigError):
            return False

    def reset_config(self) -> None:
        """
        Clear all configuration from storage.

        Raises:
            StorageError: If deletion operations fail
        """
        try:
            count = self.storage.clear_all_credentials()
            self._config_cache = None
            self.logger.info(f"Reset configuration ({count} items cleared)")
        except StorageError as e:
            self.logger.error(f"Failed to reset configuration: {e}")
            raise

    def get_full_config(self) -> Dict[str, Any]:
        """
        Get complete configuration including sensitive values.
        WARNING: Use with caution - contains sensitive data.

        Returns:
            Complete configuration dictionary

        Raises:
            MissingConfigError: If configuration is incomplete
        """
        if not self.is_configured():
            raise MissingConfigError("Configuration is incomplete")

        return {
            "keycloak": self.get_keycloak_config().dict(),
            "gcm_server": self.get_gcm_config().dict(),
            "auth": {
                **self.get_auth_config().dict(),
                "password": self.get_password(),
                "client_secret": self.get_client_secret(),
            },
            "watsonx": {
                **self.get_watsonx_config().dict(),
                "api_key": self.get_watsonx_api_key(),
            },
            "agent": self.get_agent_config().dict(),
        }


# Singleton instance for global access
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the singleton ConfigManager instance.

    Returns:
        ConfigManager instance
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
