# SSL Bypass MCP Server Issue - Root Cause Analysis

**Date:** 2026-06-06 08:00 UTC  
**Status:** ❌ CRITICAL - MCP Server SSL Configuration Required

## Executive Summary

The SSL certificate verification error is **NOT a client-side issue**. Our client-side SSL bypass is working correctly. The error originates from the **GCM MCP Server** (remote service) when it makes internal HTTPS calls to GCM API endpoints.

## Error Context

```
Error calling tool 'gcm_AssetDiscoveryService_FetchDiscoveryProfiles': 
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED] 
certificate verify failed: self-signed certificate (_ssl.c:1004)
```

## Root Cause Analysis

### 1. Client-Side SSL Bypass ✅ WORKING

**Verification Results:**
```
Test 1: Client without verify parameter
  check_hostname = False
  verify_mode = 0
  ✓ SSL verification DISABLED

Test 3: Client with verify=True
  check_hostname = True
  verify_mode = 2
  ✓ SSL verification ENABLED (when requested)
```

**Conclusion:** The module-level SSL bypass patch in `gcm_agent/__init__.py` is functioning correctly. All httpx.AsyncClient instances created by our code have SSL verification disabled by default.

### 2. Architecture Understanding

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │────────▶│  MCP Server  │────────▶│  GCM APIs   │
│  (Our Code) │  HTTPS  │  (Remote)    │  HTTPS  │  (Backend)  │
└─────────────┘         └──────────────┘         └─────────────┘
     ✅                       ❌                        
  SSL Bypass            SSL Verification         Self-Signed
   Working                  Failing                  Certs
```

**The Problem:**
- **Connection 1** (Client → MCP Server): ✅ Our SSL bypass works
- **Connection 2** (MCP Server → GCM APIs): ❌ MCP server's internal calls fail

### 3. MCP Server Internal Behavior

When we call a tool like `gcm_AssetDiscoveryService_FetchDiscoveryProfiles`:

1. Client sends request to MCP server at `https://gcm.example.com/ibm/mcp/mcp`
2. MCP server receives the tool call
3. **MCP server makes internal HTTP request** to GCM API endpoint:
   ```
   GET https://gcm.example.com:9443/api/v1/discovery/profiles
   ```
4. **This internal request fails SSL verification** because:
   - GCM uses self-signed certificates
   - MCP server has SSL verification enabled
   - MCP server's httpx/requests client doesn't trust the self-signed cert

### 4. Why Client-Side SSL Bypass Doesn't Help

Our SSL bypass only affects:
- ✅ Our httpx.AsyncClient instances
- ✅ Connections from our code to the MCP server
- ❌ **NOT** the MCP server's internal HTTP clients
- ❌ **NOT** the MCP server's connections to GCM APIs

The MCP server is a **separate Python process** running on the GCM server. Our module-level patch doesn't affect it.

## Available Headers

We checked all documented headers for the GCM MCP server:

| Header | Purpose | Can Control SSL? |
|--------|---------|------------------|
| `x-mcp-code-mode` | Enable discovery mode | ❌ No |
| `x-gcm-hostname` | Provide hostname for internal URLs | ❌ No |
| `Authorization` | Bearer token authentication | ❌ No |

**Result:** There is **NO documented header** to control the MCP server's SSL verification behavior.

## Solutions

### Option 1: Configure MCP Server (RECOMMENDED)

The MCP server needs to be configured to bypass SSL verification for its internal API calls.

**Required Action:**
1. Access the GCM MCP server configuration
2. Locate the httpx/requests client configuration
3. Set `verify=False` or configure custom CA certificates
4. Restart the MCP server

**Configuration Location (Likely):**
```python
# In GCM MCP server code (server-side)
# File: charts/aim-mcp-server/values.yaml or similar

backends:
  - name: gcm
    server: https://gcm.example.com:9443
    verify_ssl: false  # ← Add this configuration
```

### Option 2: Install Proper SSL Certificates (PRODUCTION)

For production environments, install valid SSL certificates on the GCM server:

```bash
# 1. Obtain certificate from trusted CA
# 2. Install on GCM server
# 3. Configure GCM to use the certificate
# 4. Restart GCM services
```

### Option 3: Add CA Certificate to MCP Server Trust Store

If the MCP server runs in a container/pod:

```bash
# Add CA certificate to the MCP server's trust store
kubectl exec -it <mcp-server-pod> -- bash
cp /path/to/ca-cert.pem /usr/local/share/ca-certificates/gcm-ca.crt
update-ca-certificates
# Restart MCP server
```

## What We've Already Fixed

✅ **Client-Side SSL Bypass** (gcm_agent/__init__.py)
- Module-level httpx.AsyncClient patch
- Applied before any imports
- Verified working correctly

✅ **GCM Auth Client Factory** (gcm_agent/auth/gcm_auth.py)
- Respects module-level SSL bypass
- Only passes verify=True when explicitly needed

✅ **Keycloak Auth Client** (gcm_agent/auth/keycloak_auth.py)
- Respects module-level SSL bypass
- Only passes verify=True when explicitly needed

## What Still Needs Fixing

❌ **MCP Server Configuration**
- Server-side SSL verification for internal API calls
- Requires access to GCM MCP server configuration
- Cannot be fixed from client code

## Recommendations

### Immediate Action (Development/Testing)

Contact the GCM administrator to:
1. Disable SSL verification in the MCP server configuration
2. Or provide the CA certificate used by GCM
3. Or install proper SSL certificates on GCM

### Long-Term Solution (Production)

1. Install valid SSL certificates from a trusted CA on GCM server
2. Remove all SSL bypass workarounds
3. Enable SSL verification everywhere (client + server)

## Testing Commands

### Verify Client-Side SSL Bypass
```bash
source .venv/bin/activate
python test_ssl_bypass_verification.py
```

### Test MCP Server Connection
```bash
# This will fail with SSL error if MCP server has SSL verification enabled
source .venv/bin/activate
python -c "
import asyncio
from gcm_agent.mcp.client import GCMMCPClient
from gcm_agent.auth import get_client_factory

async def test():
    factory = get_client_factory(...)
    client = GCMMCPClient(gcm_url, gcm_hostname, factory)
    await client.connect()
    tools = await client.get_tools()
    print(f'Tools: {len(tools)}')

asyncio.run(test())
"
```

## Conclusion

**The SSL bypass failure is NOT a bug in our code.** Our client-side SSL bypass is working correctly. The issue is that the **GCM MCP Server** (a remote service we don't control) needs to be configured to bypass SSL verification for its internal API calls to GCM endpoints.

**Action Required:** Contact GCM administrator to configure the MCP server to bypass SSL verification or install proper SSL certificates.

## References

- Client SSL Bypass: `gcm_agent/__init__.py` (lines 1-55)
- MCP Client: `gcm_agent/mcp/client.py` (lines 182-195)
- GCM Auth: `gcm_agent/auth/gcm_auth.py` (lines 374-410)
- Keycloak Auth: `gcm_agent/auth/keycloak_auth.py` (lines 103-112, 173-182)
- Test Script: `test_ssl_bypass_verification.py`