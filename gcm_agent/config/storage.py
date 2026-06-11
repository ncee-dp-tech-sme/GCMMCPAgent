"""Secure storage module for Fernet encryption-based persistence of sensitive GCM agent configuration values."""

# Made with Bob
# 2026-06-05 19:52 UTC - Initial implementation of keyring-based secure storage
# 2026-06-05 20:36 UTC - Replaced keyring with Fernet encryption-based storage

from cryptography.fernet import Fernet, InvalidToken
import json
import os
from pathlib import Path
from typing import Optional, List

from gcm_agent.utils.logger import get_config_logger


# Custom exceptions for storage operations
class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class EncryptionError(StorageError):
    """Raised when encryption/decryption operations fail."""
    pass


class CredentialNotFoundError(StorageError):
    """Raised when requested credential is not found."""
    pass


class FilePermissionError(StorageError):
    """Raised when file permission operations fail."""
    pass


class SecureStorage:
    """
    Fernet encryption-based secure storage for sensitive credentials.
    Stores encrypted credentials in ~/.gcm_agent/.credentials.enc with restrictive permissions.
    """

    SERVICE_NAME = "gcm-agent"

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize secure storage with Fernet encryption.
        
        Args:
            storage_dir: Directory to store encrypted credentials (default: ~/.gcm_agent)
        """
        self.logger = get_config_logger()
        
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.gcm_agent")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.key_file = self.storage_dir / ".key"
        self.credentials_file = self.storage_dir / ".credentials.enc"
        
        # Initialize or load encryption key
        self._key = self._load_or_create_key()
        self._fernet = Fernet(self._key)
        
        self.logger.debug(f"Initialized secure storage at: {self.storage_dir}")

    def _load_or_create_key(self) -> bytes:
        """
        Load existing encryption key or create new one.
        
        Returns:
            Encryption key bytes
            
        Raises:
            FilePermissionError: If unable to set file permissions
        """
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                self.logger.debug("Loaded existing encryption key")
                return key
            except Exception as e:
                self.logger.error(f"Failed to load encryption key: {e}")
                raise StorageError(f"Failed to load encryption key: {e}") from e
        else:
            try:
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Set restrictive permissions (owner read/write only)
                os.chmod(self.key_file, 0o600)
                self.logger.info("Generated new encryption key")
                return key
            except OSError as e:
                self.logger.error(f"Failed to set key file permissions: {e}")
                raise FilePermissionError(f"Failed to set key file permissions: {e}") from e
            except Exception as e:
                self.logger.error(f"Failed to create encryption key: {e}")
                raise StorageError(f"Failed to create encryption key: {e}") from e

    def _load_credentials(self) -> dict:
        """
        Load and decrypt credentials from file.
        
        Returns:
            Dictionary of credentials
            
        Raises:
            EncryptionError: If decryption fails
            StorageError: If file operations fail
        """
        if not self.credentials_file.exists():
            return {}
        
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                return {}
            
            decrypted_data = self._fernet.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            self.logger.debug(f"Loaded {len(credentials)} credentials from storage")
            return credentials
        except InvalidToken as e:
            self.logger.error("Failed to decrypt credentials: Invalid token or corrupted file")
            raise EncryptionError("Failed to decrypt credentials: Invalid token or corrupted file") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse credentials file: {e}")
            raise StorageError(f"Corrupted credentials file: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise StorageError(f"Failed to load credentials: {e}") from e

    def _save_credentials(self, credentials: dict) -> None:
        """
        Encrypt and save credentials to file.
        
        Args:
            credentials: Dictionary of credentials to save
            
        Raises:
            EncryptionError: If encryption fails
            FilePermissionError: If unable to set file permissions
            StorageError: If file operations fail
        """
        try:
            json_data = json.dumps(credentials).encode()
            encrypted_data = self._fernet.encrypt(json_data)
            
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.credentials_file, 0o600)
            self.logger.debug(f"Saved {len(credentials)} credentials to storage")
        except OSError as e:
            self.logger.error(f"Failed to set credentials file permissions: {e}")
            raise FilePermissionError(f"Failed to set credentials file permissions: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
            raise StorageError(f"Failed to save credentials: {e}") from e

    def store_credential(self, key: str, value: str) -> None:
        """
        Store a credential securely with encryption.

        Args:
            key: Credential identifier (e.g., "gcm_password")
            value: Credential value to store

        Raises:
            ValueError: If key or value is invalid
            StorageError: If storage operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        if not value or not isinstance(value, str):
            raise ValueError("Value must be a non-empty string")

        try:
            credentials = self._load_credentials()
            credentials[key] = value
            self._save_credentials(credentials)
            self.logger.info(f"Stored credential: {key}")
        except (EncryptionError, FilePermissionError) as e:
            raise
        except Exception as e:
            self.logger.error(f"Failed to store credential '{key}': {e}")
            raise StorageError(f"Failed to store credential '{key}'") from e

    def get_credential(self, key: str) -> Optional[str]:
        """
        Retrieve a credential from encrypted storage.

        Args:
            key: Credential identifier

        Returns:
            Credential value if found, None otherwise

        Raises:
            ValueError: If key is invalid
            StorageError: If retrieval operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        try:
            credentials = self._load_credentials()
            value = credentials.get(key)
            if value is not None:
                self.logger.debug(f"Retrieved credential: {key}")
            else:
                self.logger.debug(f"Credential not found: {key}")
            return value
        except (EncryptionError, FilePermissionError) as e:
            raise
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential '{key}': {e}")
            raise StorageError(f"Failed to retrieve credential '{key}'") from e

    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from encrypted storage.

        Args:
            key: Credential identifier

        Returns:
            True if credential was deleted, False if it didn't exist

        Raises:
            ValueError: If key is invalid
            StorageError: If deletion operation fails
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        try:
            credentials = self._load_credentials()
            if key in credentials:
                del credentials[key]
                self._save_credentials(credentials)
                self.logger.info(f"Deleted credential: {key}")
                return True
            else:
                self.logger.debug(f"Credential not found for deletion: {key}")
                return False
        except (EncryptionError, FilePermissionError) as e:
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete credential '{key}': {e}")
            raise StorageError(f"Failed to delete credential '{key}'") from e

    def list_credentials(self) -> List[str]:
        """
        List all stored credential keys.

        Returns:
            List of credential keys that exist in storage
            
        Raises:
            StorageError: If list operation fails
        """
        try:
            credentials = self._load_credentials()
            keys = list(credentials.keys())
            self.logger.debug(f"Found {len(keys)} stored credentials")
            return keys
        except (EncryptionError, FilePermissionError) as e:
            raise
        except Exception as e:
            self.logger.error(f"Failed to list credentials: {e}")
            raise StorageError(f"Failed to list credentials: {e}") from e

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
        Delete all stored credentials.

        Returns:
            Number of credentials deleted

        Raises:
            StorageError: If deletion operations fail
        """
        try:
            credentials = self._load_credentials()
            count = len(credentials)
            self._save_credentials({})
            self.logger.info(f"Cleared {count} credentials")
            return count
        except (EncryptionError, FilePermissionError) as e:
            raise
        except Exception as e:
            self.logger.error(f"Failed to clear credentials: {e}")
            raise StorageError(f"Failed to clear credentials: {e}") from e

    def migrate_from_env(self, env_vars: dict) -> int:
        """
        Migrate credentials from environment variables to secure storage.

        Args:
            env_vars: Dictionary of environment variable names to values

        Returns:
            Number of credentials migrated

        Example:
            storage.migrate_from_env({
                'GCM_PASSWORD': 'secret123', # HashiCorpIgnore
                'WATSONX_API_KEY': 'api_key_456'
            })
        """
        # Mapping of environment variable names to storage keys
        env_to_key_mapping = {
            "GCM_PASSWORD": "gcm_password",
            "PASSWORD": "gcm_password", # HashiCorpIgnore
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
        StorageError: If storage initialization fails
    """
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SecureStorage()
    return _storage_instance
