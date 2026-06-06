"""Top-level package for the GCM LangChain Agent.

This module applies a global SSL bypass patch to httpx.AsyncClient at import time.
This is necessary because:
1. The MCP protocol connection (SSE transport) creates its own httpx clients
2. The httpx_client_factory only affects GCM API calls, not MCP handshake
3. Self-signed certificates are common in enterprise GCM deployments

The SSL bypass is applied here at module-level so it affects ALL httpx clients
created anywhere in the application, including those created by the MCP library.
"""

# Made with Bob
# 2026-06-06 02:50 UTC - Added global SSL bypass patch at module import time to fix SSL verification errors

import httpx
import urllib3

# ============================================================================
# GLOBAL SSL BYPASS - Applied at module import time
# ============================================================================
# This patch ensures ALL httpx.AsyncClient instances (including those created
# by the MCP library for protocol connections) have SSL verification disabled
# by default. This is required for self-signed certificates in enterprise GCM.
# ============================================================================

# Store original httpx.AsyncClient.__init__ before patching
_original_httpx_init = httpx.AsyncClient.__init__


def _ssl_bypass_init(self, *args, **kwargs):
    """Global SSL bypass for self-signed certificates.
    
    Automatically sets verify=False if not explicitly provided.
    This affects both MCP protocol connections and GCM API calls.
    
    Args:
        *args: Positional arguments passed to httpx.AsyncClient.__init__
        **kwargs: Keyword arguments passed to httpx.AsyncClient.__init__
    
    Returns:
        Result of original httpx.AsyncClient.__init__
    """
    # If verify not explicitly set, disable SSL verification
    if 'verify' not in kwargs or kwargs.get('verify') is None:
        kwargs['verify'] = False
    
    return _original_httpx_init(self, *args, **kwargs)


# Apply patch globally - affects all httpx.AsyncClient instances
httpx.AsyncClient.__init__ = _ssl_bypass_init

# Disable SSL warnings to reduce noise in logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
