"""GCM authorization module for completing the second authentication step against user management endpoints."""

# Made with Bob
# 2026-06-05 21:58 UTC - Initial implementation of GCMAuthenticator with user management authorization
# 2026-06-05 21:44 UTC - Fixed authorization endpoint to use /ibm/usermanagement/api/v2/authorization with tenantId payload
# 2026-06-05 22:00 UTC - Fixed client_factory to merge headers instead of overwriting

from typing import Callable, Optional, Dict, Any

import httpx

from gcm_agent.utils.logger import get_auth_logger


class GCMAuthenticator:
    """
    Handles GCM user management authorization (second step of authentication).
    Creates authenticated HTTP clients with Bearer token injection for MCP operations.
    """

    def __init__(
        self,
        gcm_url: str,
        hostname: str,
        verify_ssl: bool = True,
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

        self.logger.debug(f"GCMAuthenticator initialized for {gcm_url}")

    def _get_authorize_endpoint(self) -> str:
        """
        Get the GCM user management authorization endpoint URL.

        Returns:
            Authorization endpoint URL
        """
        return f"{self.gcm_url}/ibm/usermanagement/api/v2/authorization"

    async def authorize(self, access_token: str, username: str) -> bool:
        """
        Authorize with GCM user management endpoint.
        This is the second step of the two-step authentication flow.

        Args:
            access_token: OAuth2 access token from Keycloak
            username: GCM username for authorization (not used in v2 API)

        Returns:
            True if authorization successful

        Raises:
            GCMAuthError: If authorization fails
        """
        self.logger.info(f"Authorizing with GCM user management (v2 API)")

        authorize_url = self._get_authorize_endpoint()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "tenantId": ""
        }

        try:
            async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                response = await client.post(
                    authorize_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code not in (200, 201, 204):
                    error_msg = f"GCM authorization failed: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except Exception:
                        error_msg += f" - {response.text}"
                    self.logger.error(error_msg)
                    raise GCMAuthError(error_msg)

                self.logger.info(f"Successfully authorized user '{username}' with GCM")
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
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        client = httpx.AsyncClient(
            headers=headers,
            verify=self.verify_ssl,
            timeout=timeout,
        )

        self.logger.debug("Created authenticated HTTP client")
        return client

    def _client_factory(
        self,
        access_token: str,
        timeout: Optional[float] = 300.0,
    ) -> Callable[[], httpx.AsyncClient]:
        """
        Create factory function that returns authenticated httpx.AsyncClient.
        This factory is critical for MCP client integration.

        The factory function is used by langchain-mcp-adapters to create
        HTTP clients with proper authentication headers. The 'verify' parameter
        must be handled carefully to avoid conflicts with AsyncClient initialization.

        Args:
            access_token: OAuth2 access token from Keycloak
            timeout: Request timeout in seconds (default: 300)

        Returns:
            Factory function that creates authenticated AsyncClient

        Example:
            >>> factory = gcm_auth._client_factory(token)
            >>> client = factory()
            >>> # Use client for MCP operations
        """
        verify_ssl = self.verify_ssl

        def factory(**kwargs) -> httpx.AsyncClient:
            """
            Factory function to create authenticated AsyncClient.
            Merges authentication headers with any headers passed by MCP client.
            """
            # Remove 'verify' from kwargs if present to avoid conflicts
            kwargs.pop("verify", None)
            
            # Get existing headers from kwargs if any
            existing_headers = kwargs.pop("headers", {})
            
            # Merge with authentication headers (our auth headers take precedence)
            merged_headers = {
                **existing_headers,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            return httpx.AsyncClient(
                headers=merged_headers,
                verify=verify_ssl,
                timeout=timeout,
                **kwargs,
            )

        self.logger.debug("Created authenticated client factory")
        return factory

    def get_auth_headers(self, access_token: str) -> Dict[str, str]:
        """
        Get authentication headers for manual HTTP requests.

        Args:
            access_token: OAuth2 access token from Keycloak

        Returns:
            Dictionary of authentication headers
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }


# Custom exception for GCM authorization errors
class GCMAuthError(Exception):
    """Raised when GCM authorization fails."""
    pass
