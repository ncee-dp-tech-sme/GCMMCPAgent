"""Keycloak authentication module for obtaining OAuth2 access tokens for the GCM agent."""

# Made with Bob
# 2026-06-09 20:41 UTC - REFACTORING: Extracted helper methods, simplified error handling with raise_for_status(), reduced code duplication
# 2026-06-06 07:30 UTC - CRITICAL FIX: Changed httpx.AsyncClient creation to NOT pass verify parameter when verify_ssl=False, allowing module-level SSL bypass patch to apply (fixes intermittent SSL errors)
# 2026-06-05 21:58 UTC - Initial implementation of KeycloakAuthenticator with OAuth2 token management
# 2026-06-05 21:04 UTC - Updated to use separate Keycloak URL configuration

import base64
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone

import httpx

from gcm_agent.utils.logger import get_auth_logger


# Module-level helper functions

def _build_client_kwargs(verify_ssl: bool) -> Dict[str, Any]:
    """
    Build httpx.AsyncClient kwargs based on SSL verification setting.
    
    Args:
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        Dictionary of client kwargs
    """
    return {"verify": True} if verify_ssl else {}


class KeycloakAuthenticator:
    """
    Handles OAuth2 authentication with Keycloak server.
    Manages token retrieval, caching, validation, and refresh operations.
    """

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        username: str,
        password: str,
        client_secret: str,
        verify_ssl: bool = False,
    ):
        """
        Initialize Keycloak authenticator.

        Args:
            keycloak_url: Full Keycloak server URL including port (e.g., https://keycloak.example.com:443)
            realm: Keycloak realm name (default: "master")
            client_id: OAuth2 client ID
            username: User username for authentication
            password: User password for authentication
            client_secret: OAuth2 client secret
            verify_ssl: Whether to verify SSL certificates for Keycloak (default: True)
        """
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self.logger = get_auth_logger()

        # Token cache
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        self.logger.debug(
            f"KeycloakAuthenticator initialized for realm '{realm}' at {keycloak_url}"
        )

    def _get_token_endpoint(self) -> str:
        """
        Get the Keycloak token endpoint URL.

        Returns:
            Token endpoint URL
        """
        return f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

    def _cache_token(self, token_data: Dict[str, Any]) -> str:
        """
        Cache token data and calculate expiry.
        
        Args:
            token_data: Token response from Keycloak
            
        Returns:
            Access token string
        """
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        
        # Calculate token expiry (with 30 second buffer)
        expires_in = token_data.get("expires_in", 300)
        self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 30)
        
        self.logger.info(
            f"Token cached: expires_in={expires_in}s, expires_at={self._token_expiry} UTC"
        )
        return self._access_token

    async def _post_token_request(
        self,
        data: Dict[str, str],
        operation: str = "authentication"
    ) -> Dict[str, Any]:
        """
        Post token request to Keycloak and handle response.
        
        Args:
            data: Form data for token request
            operation: Operation name for logging (e.g., "authentication", "refresh")
            
        Returns:
            Token response data
            
        Raises:
            KeycloakAuthError: If request fails
        """
        token_url = self._get_token_endpoint()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            client_kwargs = _build_client_kwargs(self.verify_ssl)
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(token_url, headers=headers, data=data)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Keycloak {operation} failed: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail.get('error_description', error_detail.get('error', ''))}"
            except Exception:
                error_msg += f" - {e.response.text}"
            self.logger.error(error_msg)
            raise KeycloakAuthError(error_msg) from e
            
        except httpx.HTTPError as e:
            error_msg = f"HTTP error during Keycloak {operation}: {e}"
            self.logger.error(error_msg)
            raise KeycloakAuthError(error_msg) from e

    async def get_token(self) -> str:
        """
        Get OAuth2 access token from Keycloak.
        Returns cached token if still valid, otherwise requests new token.

        Returns:
            Access token string

        Raises:
            KeycloakAuthError: If authentication fails
        """
        # Return cached token if still valid
        if self._access_token and self.is_token_valid(self._access_token):
            self.logger.debug("Using cached access token")
            return self._access_token

        # Request new token
        self.logger.info("Requesting new access token from Keycloak")

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": "openid",
        }

        try:
            token_data = await self._post_token_request(data, "authentication")
            return self._cache_token(token_data)
            
        except KeyError as e:
            error_msg = f"Invalid token response from Keycloak: missing {e}"
            self.logger.error(error_msg)
            raise KeycloakAuthError(error_msg) from e

    async def refresh_token(self, refresh_token: Optional[str] = None) -> str:
        """
        Refresh expired access token using refresh token.

        Args:
            refresh_token: Refresh token (uses cached token if not provided)

        Returns:
            New access token string

        Raises:
            KeycloakAuthError: If token refresh fails
        """
        token_to_refresh = refresh_token or self._refresh_token

        if not token_to_refresh:
            self.logger.warning("No refresh token available, requesting new token")
            return await self.get_token()

        self.logger.info("Refreshing access token")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": token_to_refresh,
        }

        try:
            token_data = await self._post_token_request(data, "token refresh")
            return self._cache_token(token_data)
            
        except KeycloakAuthError:
            # If refresh fails, try getting new token
            self.logger.info("Refresh failed, requesting new token")
            return await self.get_token()

    def is_token_valid(self, token: str) -> bool:
        """
        Check if access token is still valid.
        Validates both expiry time and token structure.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        if not token:
            return False

        # Check cached expiry first
        if self._token_expiry and datetime.now(timezone.utc) >= self._token_expiry:
            self.logger.debug("Token expired based on cached expiry time")
            return False

        # Parse token to check expiry
        try:
            token_data = self._parse_token(token)
            exp = token_data.get("exp")

            if not exp:
                self.logger.warning("Token missing expiry claim")
                return False

            # Check if token is expired (with 30 second buffer)
            current_time = time.time()
            if current_time >= (exp - 30):
                self.logger.debug("Token expired based on JWT expiry claim")
                return False

            return True

        except Exception as e:
            self.logger.warning(f"Failed to validate token: {e}")
            return False

    def _parse_token(self, token: str) -> Dict[str, Any]:
        """
        Parse JWT token to extract claims.
        Uses base64 decoding to extract payload without full JWT validation.

        Args:
            token: JWT token string

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token format is invalid
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format")

            # Decode payload (second part)
            payload = parts[1]

            # Add padding if needed
            padding = 4 - (len(payload) % 4)
            if padding != 4:
                payload += "=" * padding

            # Decode base64
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)

            return claims

        except Exception as e:
            raise ValueError(f"Failed to parse JWT token: {e}") from e

    def get_token_expires_in(self) -> Optional[int]:
        """
        Get remaining token lifetime in seconds.
        
        Returns:
            Remaining seconds until token expiry (with buffer added back),
            or None if no token expiry is cached.
        """
        if not self._token_expiry:
            return None
        
        remaining = int((self._token_expiry - datetime.now(timezone.utc)).total_seconds())
        # Add back the 30s buffer that was subtracted during token storage
        return remaining + 30

    def clear_cache(self) -> None:
        """Clear cached tokens and expiry information."""
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None
        self.logger.debug("Token cache cleared")


# Custom exception for Keycloak authentication errors
class KeycloakAuthError(Exception):
    """Raised when Keycloak authentication fails."""
    pass
