"""Authentication package for GCM Keycloak token retrieval and GCM authorization flows."""

# Made with Bob
# 2026-06-05 21:59 UTC - Implemented custom exceptions, authenticate_gcm helper, and exports
# 2026-06-05 21:04 UTC - Updated to use separate KeycloakConfig and GCMServerConfig

from typing import Tuple, Optional
import httpx

from gcm_agent.config.config_manager import KeycloakConfig, GCMServerConfig, AuthConfig
from gcm_agent.auth.keycloak_auth import KeycloakAuthenticator, KeycloakAuthError
from gcm_agent.auth.gcm_auth import GCMAuthenticator, GCMAuthError
from gcm_agent.utils.logger import get_auth_logger


# Custom exceptions for authentication operations
class AuthenticationError(Exception):
    """Base exception for authentication operations."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""
    pass


async def authenticate_gcm(
    keycloak_config: KeycloakConfig,
    gcm_config: GCMServerConfig,
    auth_config: AuthConfig,
    password: str,
    client_secret: str,
) -> Tuple[str, httpx.AsyncClient]:
    """
    Complete two-step authentication flow for GCM.
    
    This implements the critical authentication pattern described in AGENTS.md:
    1. Obtain OAuth2 token from Keycloak FIRST
    2. Authorize with GCM user management endpoint
    3. Create authenticated client with token in headers
    
    Both steps are required - missing either causes silent auth failure.
    
    Args:
        keycloak_config: Keycloak server configuration
        gcm_config: GCM server configuration
        auth_config: Authentication configuration (username, client_id)
        password: GCM user password
        client_secret: OAuth2 client secret
    
    Returns:
        Tuple of (access_token, authenticated_client)
        - access_token: OAuth2 access token for subsequent requests
        - authenticated_client: httpx.AsyncClient with Bearer token in headers
    
    Raises:
        KeycloakAuthError: If Keycloak authentication fails
        GCMAuthError: If GCM authorization fails
        AuthenticationError: If authentication flow fails
    
    Example:
        >>> token, client = await authenticate_gcm(
        ...     keycloak_config, gcm_config, auth_config, password, client_secret
        ... )
        >>> # Use client for MCP operations
        >>> # Token can be used for manual requests or token refresh
    """
    logger = get_auth_logger()
    logger.info("Starting two-step GCM authentication flow")
    
    try:
        # Step 1: Get Keycloak OAuth2 token
        logger.info("Step 1: Authenticating with Keycloak")
        keycloak_url = f"{keycloak_config.url}:{keycloak_config.port}"
        
        keycloak = KeycloakAuthenticator(
            keycloak_url=keycloak_url,
            realm=keycloak_config.realm,
            client_id=auth_config.client_id,
            username=auth_config.username,
            password=password,
            client_secret=client_secret,
            verify_ssl=keycloak_config.verify_ssl,
        )
        
        access_token = await keycloak.get_token()
        logger.info("Step 1 complete: Successfully obtained Keycloak token")
        
        # Step 2: Authorize with GCM user management
        logger.info("Step 2: Authorizing with GCM user management")
        gcm_auth = GCMAuthenticator(
            gcm_url=gcm_config.url,
            hostname=gcm_config.hostname,
            verify_ssl=gcm_config.verify_ssl,
        )
        
        await gcm_auth.authorize(access_token, auth_config.username)
        logger.info("Step 2 complete: Successfully authorized with GCM")
        
        # Step 3: Create authenticated client for MCP operations
        logger.info("Step 3: Creating authenticated HTTP client")
        authenticated_client = gcm_auth.create_authenticated_client(access_token)
        logger.info("Step 3 complete: Authenticated client ready")
        
        logger.info("Two-step authentication flow completed successfully")
        return access_token, authenticated_client
        
    except KeycloakAuthError as e:
        logger.error(f"Keycloak authentication failed: {e}")
        raise
    except GCMAuthError as e:
        logger.error(f"GCM authorization failed: {e}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error during authentication flow: {e}"
        logger.error(error_msg)
        raise AuthenticationError(error_msg) from e


async def get_client_factory(
    keycloak_config: KeycloakConfig,
    gcm_config: GCMServerConfig,
    auth_config: AuthConfig,
    password: str,
    client_secret: str,
    timeout: Optional[float] = 300.0,
):
    """
    Get authenticated client factory for MCP integration.
    
    This function completes the two-step auth flow and returns a factory
    function that creates httpx.AsyncClient instances with proper authentication.
    
    The factory is critical for langchain-mcp-adapters integration, as it
    handles the 'verify' parameter conflict and injects Bearer tokens.
    
    Args:
        keycloak_config: Keycloak server configuration
        gcm_config: GCM server configuration
        auth_config: Authentication configuration
        password: GCM user password
        client_secret: OAuth2 client secret
        timeout: Request timeout in seconds (default: 300)
    
    Returns:
        Factory function that creates authenticated AsyncClient instances
    
    Raises:
        KeycloakAuthError: If Keycloak authentication fails
        GCMAuthError: If GCM authorization fails
        AuthenticationError: If authentication flow fails
    
    Example:
        >>> factory = await get_client_factory(
        ...     keycloak_config, gcm_config, auth_config, password, client_secret
        ... )
        >>> # Pass factory to MCP client
        >>> mcp_client = MCPClient(client_factory=factory)
    """
    logger = get_auth_logger()
    logger.info("Getting authenticated client factory for MCP integration")
    
    # Complete authentication flow
    access_token, _ = await authenticate_gcm(
        keycloak_config, gcm_config, auth_config, password, client_secret
    )
    
    # Create GCM authenticator to get factory
    logger.debug(f"Creating GCM authenticator with verify_ssl={gcm_config.verify_ssl}")
    gcm_auth = GCMAuthenticator(
        gcm_url=gcm_config.url,
        hostname=gcm_config.hostname,
        verify_ssl=gcm_config.verify_ssl,
    )
    
    factory = gcm_auth._client_factory(access_token, timeout)
    logger.info(f"Client factory created successfully with verify_ssl={gcm_config.verify_ssl}")
    
    return factory


# Export all public classes and functions
__all__ = [
    # Authenticators
    "KeycloakAuthenticator",
    "GCMAuthenticator",
    # Exceptions
    "AuthenticationError",
    "KeycloakAuthError",
    "GCMAuthError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    # Helper functions
    "authenticate_gcm",
    "get_client_factory",
]
