"""API key authentication — skips Keycloak, uses raw key as Bearer token."""

# Made with Bob
# 2026-07-17 00:36 UTC - Initial implementation: APIKeyAuthenticator that returns raw API key as token


class APIKeyAuthenticator:
    """
    Minimal authenticator for API key mode.
    Replaces the Keycloak OAuth2 flow — the raw API key is used directly as the Bearer token.
    """

    def __init__(self, api_key: str):
        """
        Args:
            api_key: GCM API key to use as Bearer token
        """
        self.api_key = api_key

    def get_token(self) -> str:
        """Return the API key as the Bearer token (no network call needed)."""
        return self.api_key
