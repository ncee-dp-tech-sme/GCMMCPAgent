"""Secure storage module for keyring-backed persistence of sensitive GCM agent configuration values."""

# Made with Bob
# 2026-06-05 19:52 UTC - Initial implementation of keyring-based secure storage

import keyring
from typing import Optional, List
from keyring.errors import KeyringError, PasswordDeleteError

from gcm_agent.utils.logger import get_config_logger


# Custom exceptions for storage operations
class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class KeyringBackendError(StorageError):
    """Raised when keyring backend is unavailable or fails."""
    pass


class CredentialNotFoundError(StorageError):
    """Raised when requested credential is not found."""
    pass


class SecureStorage:
    """
    Keyring-based secure storage for sensitive credentials.
    Uses OS-level secure storage (Keychain on macOS, Credential Manager on Windows, Secret Service on Linux).
    """

    SERVICE_NAME = "gcm-agent"

    def __init__(self):
        """Initialize secure storage with logging."""
        self.logger = get_config_logger()
        self._verify_keyring_backend()

    def _verify_keyring_backend(self) -> None:
        """
        Verify that a keyring backend is available.
        Raises KeyringBackendError if no backend is available.
        """
        try:
            backend = keyring.get_keyring()
            self.logger.debug(f"Using keyring backend: {backend.__class__.__name__}")
        except Exception as e:
            self.logger.error(f"Failed to initialize keyring backend: {e}")
            raise KeyringBackendError(
                "No keyring backend available. Please install a keyring backend for your OS."
            ) from e

    def store_credential(self, key: str, value: str) -> None:
        """
        Store a credential securely in the keyring.

        Args:
            key: Credential identifier (e.g., "gcm_password")
            value: Credential value to store

        Raises:
            StorageError: If storage operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        if not value or not isinstance(value, str):
            raise ValueError("Value must be a non-empty string")

        try:
            keyring.set_password(self.SERVICE_NAME, key, value)
            self.logger.info(f"Stored credential: {key}")
        except KeyringError as e:
            self.logger.error(f"Failed to store credential '{key}': {e}")
            raise StorageError(f"Failed to store credential '{key}'") from e
        except Exception as e:
            self.logger.error(f"Unexpected error storing credential '{key}': {e}")
            raise StorageError(f"Unexpected error storing credential '{key}'") from e

    def get_credential(self, key: str) -> Optional[str]:
        """
        Retrieve a credential from the keyring.

        Args:
            key: Credential identifier

        Returns:
            Credential value if found, None otherwise

        Raises:
            StorageError: If retrieval operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        try:
            value = keyring.get_password(self.SERVICE_NAME, key)
            if value is not None:
                self.logger.debug(f"Retrieved credential: {key}")
            else:
                self.logger.debug(f"Credential not found: {key}")
            return value
        except KeyringError as e:
            self.logger.error(f"Failed to retrieve credential '{key}': {e}")
            raise StorageError(f"Failed to retrieve credential '{key}'") from e
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving credential '{key}': {e}")
            raise StorageError(f"Unexpected error retrieving credential '{key}'") from e

    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from the keyring.

        Args:
            key: Credential identifier

        Returns:
            True if credential was deleted, False if it didn't exist

        Raises:
            StorageError: If deletion operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        try:
            keyring.delete_password(self.SERVICE_NAME, key)
            self.logger.info(f"Deleted credential: {key}")
            return True
        except PasswordDeleteError:
            # Credential doesn't exist
            self.logger.debug(f"Credential not found for deletion: {key}")
            return False
        except KeyringError as e:
            self.logger.error(f"Failed to delete credential '{key}': {e}")
            raise StorageError(f"Failed to delete credential '{key}'") from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting credential '{key}': {e}")
            raise StorageError(f"Unexpected error deleting credential '{key}'") from e

    def list_credentials(self) -> List[str]:
        """
        List all stored credential keys for this service.

        Note: This method attempts to retrieve known credential keys.
        Keyring doesn't provide a native list operation, so we check
        for common credential keys used by the GCM agent.

        Returns:
            List of credential keys that exist in storage
        """
        # Known credential keys used by GCM agent
        known_keys = [
            "config",
            "gcm_password",
            "gcm_client_secret",
            "watsonx_api_key",
        ]

        existing_keys = []
        for key in known_keys:
            try:
                if self.get_credential(key) is not None:
                    existing_keys.append(key)
            except StorageError:
                # Skip keys that cause errors
                continue

        self.logger.debug(f"Found {len(existing_keys)} stored credentials")
        return existing_keys

    def credential_exists(self, key: str) -> bool:
        """
        Check if a credential exists in storage.

        Args:
            key: Credential identifier

        Returns:
            True if credential exists, False otherwise
        """
        try:
            return self.get_credential(key) is not None
        except StorageError:
            return False

    def clear_all_credentials(self) -> int:
        """
        Delete all stored credentials for this service.

        Returns:
            Number of credentials deleted

        Raises:
            StorageError: If deletion operations fail
        """
        credentials = self.list_credentials()
        deleted_count = 0

        for key in credentials:
            try:
                if self.delete_credential(key):
                    deleted_count += 1
            except StorageError as e:
                self.logger.warning(f"Failed to delete credential '{key}': {e}")
                # Continue deleting other credentials

        self.logger.info(f"Cleared {deleted_count} credentials")
        return deleted_count

    def migrate_from_env(self, env_vars: dict) -> int:
        """
        Migrate credentials from environment variables to secure storage.

        Args:
            env_vars: Dictionary of environment variable names to values

        Returns:
            Number of credentials migrated

        Example:
            storage.migrate_from_env({
                'GCM_PASSWORD': 'secret123',
                'WATSONX_API_KEY': 'api_key_456'
            })
        """
        # Mapping of environment variable names to storage keys
        env_to_key_mapping = {
            "GCM_PASSWORD": "gcm_password",
            "PASSWORD": "gcm_password",
            "GCM_CLIENT_SECRET": "gcm_client_secret",
            "CLIENT_SECRET": "gcm_client_secret",
            "WATSONX_API_KEY": "watsonx_api_key",
            "LLM_WATSONX_API_KEY": "watsonx_api_key",
        }

        migrated_count = 0
        for env_name, storage_key in env_to_key_mapping.items():
            if env_name in env_vars and env_vars[env_name]:
                try:
                    self.store_credential(storage_key, env_vars[env_name])
                    migrated_count += 1
                    self.logger.info(f"Migrated {env_name} to secure storage")
                except StorageError as e:
                    self.logger.warning(f"Failed to migrate {env_name}: {e}")

        return migrated_count


# Singleton instance for global access
_storage_instance: Optional[SecureStorage] = None


def get_storage() -> SecureStorage:
    """
    Get the singleton SecureStorage instance.

    Returns:
        SecureStorage instance

    Raises:
        KeyringBackendError: If keyring backend is unavailable
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SecureStorage()
    return _storage_instance
