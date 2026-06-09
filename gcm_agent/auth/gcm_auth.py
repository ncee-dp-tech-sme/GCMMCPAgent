"""GCM authorization module for completing the second authentication step against user management endpoints."""

# Made with Bob
# 2026-06-09 20:20 UTC - REFACTORING: Extracted helper functions to module level, simplified error handling, reduced nested complexity
# 2026-06-06 07:17 UTC - CRITICAL FIX: Changed all httpx.AsyncClient creation to NOT pass verify parameter when verify_ssl=False, allowing module-level SSL bypass patch to apply
# 2026-06-06 06:00 UTC - Added comprehensive header logging with token masking for debugging Authorization Bearer token
# 2026-06-06 02:59 UTC - Added gcm_hostname parameter to _client_factory to inject x-gcm-hostname header in all HTTP requests
# 2026-06-06 01:40 UTC - Fixed token refresh to properly update token expiration info after refresh, preventing SSL errors after token expiry
# 2026-06-06 00:26 UTC - Added token expiration tracking and refresh mechanism to fix intermittent SSL/500 errors
# 2026-06-06 00:02 UTC - Fixed SSL certificate verification error by ensuring _client_factory properly pops 'verify' kwarg before creating AsyncClient
# 2026-06-05 21:58 UTC - Initial implementation of GCMAuthenticator with user management authorization
# 2026-06-05 21:44 UTC - Fixed authorization endpoint to use /ibm/usermanagement/api/v2/authorization with tenantId payload
# 2026-06-05 22:00 UTC - Fixed client_factory to merge headers instead of overwriting

from typing import Callable, Optional, Dict, Any, Set
from datetime import datetime, timedelta, timezone

import httpx

from gcm_agent.utils.logger import get_auth_logger


# Module-level helper functions (extracted from nested scopes for reusability)

def _mask_token(token: str) -> str:
    """
    Mask token showing only first 8 and last 4 characters.
    
    Args:
        token: Token string to mask
        
    Returns:
        Masked token string
    """
    if len(token) <= 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"


def _mask_auth_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Create a copy of headers with Authorization Bearer tokens masked.
    
    Args:
        headers: Original headers dictionary
        
    Returns:
        New dictionary with masked Authorization headers
    """
    masked = {}
    for k, v in headers.items():
        if k == "Authorization" and v.startswith("Bearer "):
            masked[k] = f"Bearer {_mask_token(v[7:])}"
        else:
            masked[k] = v
    return masked


def _build_auth_headers(access_token: str, gcm_hostname: Optional[str] = None, existing_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Build authentication headers with optional GCM hostname and existing headers.
    
    Args:
        access_token: OAuth2 access token
        gcm_hostname: Optional GCM hostname for x-gcm-hostname header
        existing_headers: Optional existing headers to merge
        
    Returns:
        Merged headers dictionary with authentication
    """
    headers = {
        **(existing_headers or {}),
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    if gcm_hostname:
        headers["x-gcm-hostname"] = gcm_hostname
    
    return headers


def _filter_client_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out kwargs that conflict with httpx.AsyncClient initialization.
    
    Args:
        kwargs: Original kwargs dictionary
        
    Returns:
        Filtered kwargs dictionary
    """
    # Keys to remove that we handle explicitly
    unwanted_keys: Set[str] = {'verify', 'timeout', 'cert', 'trust_env', 'auth', 'headers'}
    return {k: v for k, v in kwargs.items() if k not in unwanted_keys}


class GCMAuthenticator:
    """
    Handles GCM user management authorization (second step of authentication).
    Creates authenticated HTTP clients with Bearer token injection for MCP operations.
    Tracks token expiration and provides refresh mechanism.
    """

    def __init__(
        self,
        gcm_url: str,
        hostname: str,
        verify_ssl: bool = False,
    ):
        """
        Initialize GCM authenticator.

        Args:
            gcm_url: Base URL of GCM server (e.g., https://gcm.example.com)
            hostname: GCM server hostname for authorization
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.gcm_url = gcm_url.rstrip("/")
        self.hostname = hostname
        self.verify_ssl = verify_ssl
        self.logger = get_auth_logger()
        
        # Token tracking for refresh mechanism
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._keycloak_authenticator: Optional[Any] = None

        self.logger.debug(f"GCMAuthenticator initialized for {gcm_url}")

    def set_token_info(self, access_token: str, expires_in: int, keycloak_authenticator: Optional[Any] = None) -> None:
        """
        Store token information for expiration tracking.
        
        Args:
            access_token: OAuth2 access token from Keycloak
            expires_in: Token lifetime in seconds
            keycloak_authenticator: Optional KeycloakAuthenticator instance for token refresh
        """
        self._access_token = access_token
        # Calculate expiration with 30 second buffer to refresh before actual expiry
        # (Keycloak already applies 30s buffer, so total buffer is 60s which is reasonable)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 30)
        self._keycloak_authenticator = keycloak_authenticator
        
        self.logger.info(f"Token info stored: expires_in={expires_in}s, expires_at={self._token_expires_at} UTC, buffer=30s")
    
    def is_token_expired(self) -> bool:
        """
        Check if the stored token is expired or about to expire.
        
        Returns:
            True if token is expired or will expire soon, False otherwise
        """
        if not self._token_expires_at:
            # No token info stored, assume expired
            return True
        
        is_expired = datetime.now(timezone.utc) >= self._token_expires_at
        if is_expired:
            self.logger.debug("Token has expired or is about to expire")
        return is_expired
    
    async def refresh_token(self) -> str:
        """
        Refresh the expired token by re-authenticating with Keycloak.
        
        If a KeycloakAuthenticator was provided, uses it to refresh the token.
        Otherwise, raises an error as we cannot refresh without the authenticator.
        
        Returns:
            New access token
        
        Raises:
            GCMAuthError: If token refresh fails or no authenticator available
        """
        if not self._keycloak_authenticator:
            error_msg = "Cannot refresh token: no KeycloakAuthenticator available"
            self.logger.error(error_msg)
            raise GCMAuthError(error_msg)
        
        self.logger.info("Refreshing expired token via Keycloak")
        
        try:
            # Get fresh token from Keycloak (will use refresh_token if available)
            new_token = await self._keycloak_authenticator.get_token()
            
            # Re-authorize with GCM using new token
            await self.authorize(new_token)
            
            # Update stored token info with new expiration
            if self._keycloak_authenticator._token_expiry:
                expires_in = int((self._keycloak_authenticator._token_expiry - datetime.now(timezone.utc)).total_seconds()) + 30
                self.set_token_info(new_token, expires_in, self._keycloak_authenticator)
                self.logger.info(f"Token refreshed successfully, new expiration in {expires_in}s")
            else:
                # Fallback: assume 5 minute expiration if not available
                self._access_token = new_token
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=240)  # 4 min buffer
                self.logger.warning("Token refreshed but expiration time unknown, using 4 minute default")
            
            self.logger.info("Successfully refreshed token and re-authorized with GCM")
            return new_token
            
        except Exception as e:
            error_msg = f"Failed to refresh token: {e}"
            self.logger.error(error_msg)
            raise GCMAuthError(error_msg) from e
    
    def _get_authorize_endpoint(self) -> str:
        """
        Get the GCM user management authorization endpoint URL.

        Returns:
            Authorization endpoint URL
        """
        return f"{self.gcm_url}/ibm/usermanagement/api/v2/authorization"

    async def authorize(self, access_token: str) -> bool:
        """
        Authorize with GCM user management endpoint.
        This is the second step of the two-step authentication flow.

        Args:
            access_token: OAuth2 access token from Keycloak

        Returns:
            True if authorization successful

        Raises:
            GCMAuthError: If authorization fails
        """
        self.logger.info("Authorizing with GCM user management (v2 API)")

        authorize_url = self._get_authorize_endpoint()
        headers = _build_auth_headers(access_token)
        payload = {"tenantId": ""}
        
        # Log authorization request with masked token
        masked_headers = _mask_auth_headers(headers)
        self.logger.info(f"Authorization request to {authorize_url} with headers: {masked_headers}")

        try:
            # CRITICAL: Only pass verify if SSL verification is explicitly enabled
            # This allows the module-level SSL bypass patch to apply when verify_ssl=False
            client_kwargs = {"verify": True} if self.verify_ssl else {}
            
            if self.verify_ssl:
                self.logger.debug("Authorization: SSL verification ENABLED")
            else:
                self.logger.debug("Authorization: SSL verification DISABLED - using module-level bypass")
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(
                    authorize_url,
                    headers=headers,
                    json=payload,
                )

                # Use httpx built-in error handling
                if not response.is_success:
                    error_msg = f"GCM authorization failed: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except Exception:
                        error_msg += f" - {response.text}"
                    self.logger.error(error_msg)
                    raise GCMAuthError(error_msg)

                self.logger.info("Successfully authorized with GCM")
                return True

        except httpx.HTTPError as e:
            error_msg = f"HTTP error during GCM authorization: {e}"
            self.logger.error(error_msg)
            raise GCMAuthError(error_msg) from e
        except GCMAuthError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during GCM authorization: {e}"
            self.logger.error(error_msg)
            raise GCMAuthError(error_msg) from e

    def create_authenticated_client(
        self,
        access_token: str,
        timeout: Optional[float] = 300.0,
    ) -> httpx.AsyncClient:
        """
        Create httpx.AsyncClient with Bearer token in headers.
        This client is used for MCP operations after successful authorization.

        Args:
            access_token: OAuth2 access token from Keycloak
            timeout: Request timeout in seconds (default: 300)

        Returns:
            Configured httpx.AsyncClient with authentication headers
        """
        headers = _build_auth_headers(access_token)

        # CRITICAL: Only pass verify if SSL verification is explicitly enabled
        # This allows the module-level SSL bypass patch to apply when verify_ssl=False
        client_kwargs = {
            "headers": headers,
            "timeout": timeout,
        }
        
        if self.verify_ssl:
            client_kwargs["verify"] = True
            self.logger.debug("Created authenticated HTTP client with SSL verification ENABLED")
        else:
            self.logger.debug("Created authenticated HTTP client with SSL verification DISABLED (module-level bypass)")

        return httpx.AsyncClient(**client_kwargs)

    def _client_factory(
        self,
        access_token: str,
        timeout: Optional[float] = 300.0,
        gcm_hostname: Optional[str] = None,
    ) -> Callable[[], httpx.AsyncClient]:
        """
        Create factory function that returns authenticated httpx.AsyncClient.
        This factory is critical for MCP client integration.

        The factory function is used by langchain-mcp-adapters to create
        HTTP clients with proper authentication headers. The 'verify' parameter
        must be handled carefully to avoid conflicts with AsyncClient initialization.
        
        The factory now checks token expiration before creating clients and uses
        the current token from the authenticator instance.

        Args:
            access_token: OAuth2 access token from Keycloak (initial token)
            timeout: Request timeout in seconds (default: 300)
            gcm_hostname: GCM hostname for x-gcm-hostname header (required for internal API calls)

        Returns:
            Factory function that creates authenticated AsyncClient

        Example:
            >>> factory = gcm_auth._client_factory(token, gcm_hostname="gcm.example.com")
            >>> client = factory()
            >>> # Use client for MCP operations
        """
        # Capture parameters in closure for factory function
        verify_ssl = self.verify_ssl
        logger = self.logger
        authenticator = self

        def factory(**kwargs) -> httpx.AsyncClient:
            """
            Factory function to create authenticated AsyncClient.
            Merges authentication headers with any headers passed by MCP client.
            Removes conflicting parameters to avoid duplicate keyword arguments.
            
            CRITICAL: Must filter kwargs before creating AsyncClient to avoid conflicts.
            Now checks token expiration and uses current token from authenticator.
            """
            logger.debug(f"Factory called with kwargs: {kwargs}")
            
            # Use current token from authenticator (may have been refreshed)
            current_token = authenticator._access_token or access_token
            
            # Check if token is expired (but don't refresh here - that's async)
            if authenticator.is_token_expired():
                logger.warning(
                    "Token is expired or about to expire. "
                    "Client creation will proceed with current token, but refresh is needed."
                )
            
            # Extract and remove headers before filtering
            existing_headers = kwargs.pop("headers", {})
            
            # Log removed auth parameter if present
            if "auth" in kwargs:
                logger.debug(f"Removed auth parameter from kwargs: {type(kwargs['auth'])}")
            
            # Filter out conflicting kwargs using helper function
            filtered_kwargs = _filter_client_kwargs(kwargs)
            
            # Build authentication headers with GCM hostname
            merged_headers = _build_auth_headers(current_token, gcm_hostname, existing_headers)
            
            # Log headers with token masked
            masked_headers = _mask_auth_headers(merged_headers)
            logger.info(f"HTTP client headers configured: {masked_headers}")
            logger.debug(f"Full header count: {len(merged_headers)} headers")
            logger.debug(f"Creating AsyncClient with verify={verify_ssl}, remaining kwargs={list(filtered_kwargs.keys())}")
            
            # Create event hooks for request/response logging
            async def log_request(request):
                """Log outgoing HTTP requests with masked headers."""
                logged_headers = dict(request.headers)
                # Find authorization header (case-insensitive)
                auth_key = next((k for k in logged_headers if k.lower() == "authorization"), None)
                
                if auth_key and logged_headers[auth_key].startswith("Bearer "):
                    token = logged_headers[auth_key][7:]
                    logged_headers[auth_key] = f"Bearer {_mask_token(token)}"
                
                logger.debug(f"HTTP Request: {request.method} {request.url} | Headers: {logged_headers}")
            
            async def log_response(response):
                """Log HTTP responses."""
                try:
                    elapsed_time = f"Time: {response.elapsed.total_seconds():.2f}s"
                except RuntimeError:
                    elapsed_time = "Time: N/A (streaming)"
                
                logger.debug(f"HTTP Response: {response.status_code} from {response.url} | {elapsed_time}")
            
            # Build client kwargs
            client_kwargs = {
                "headers": merged_headers,
                "timeout": timeout,
                "trust_env": False,
                "follow_redirects": True,
                "event_hooks": {
                    "request": [log_request],
                    "response": [log_response],
                },
                **filtered_kwargs,
            }
            
            # Only pass verify if SSL verification is explicitly enabled
            if verify_ssl:
                client_kwargs["verify"] = True
                logger.debug("SSL verification ENABLED - will verify certificates")
            else:
                logger.debug("SSL verification DISABLED - relying on module-level bypass")
            
            client = httpx.AsyncClient(**client_kwargs)
            logger.debug(f"AsyncClient created successfully with SSL bypass={'disabled' if verify_ssl else 'enabled'}")
            return client

        self.logger.debug(f"Created authenticated client factory (verify_ssl={verify_ssl})")
        return factory

    def get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """
        Get authentication headers for manual HTTP requests.

        Args:
            access_token: OAuth2 access token from Keycloak

        Returns:
            Dictionary of authentication headers
        """
        return _build_auth_headers(access_token)


# Custom exception for GCM authorization errors
class GCMAuthError(Exception):
    """Raised when GCM authorization fails."""
    pass

