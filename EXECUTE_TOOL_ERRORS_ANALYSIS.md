# Execute Tool Errors - Root Cause Analysis

**Date:** 2026-06-06 06:14 UTC  
**Status:** ✅ Error 1 FIXED | ⚠️ Error 2 SERVER-SIDE ISSUE

## Executive Summary

Investigation of two reported errors in the GCM agent's `execute` tool reveals:

1. **Error 1 (TypeError: 'coroutine' object is not subscriptable)**: ✅ **ALREADY FIXED**
2. **Error 2 (SSL Certificate Verification)**: ⚠️ **SERVER-SIDE ISSUE - Cannot be fixed client-side**

## Error 1: TypeError: 'coroutine' object is not subscriptable

### Status: ✅ FIXED

### Root Cause
The `execute` tool in discovery mode was returning a coroutine object that needed to be awaited before attempting to unpack it as a tuple.

### The Fix
**File:** `gcm_agent/mcp/client.py`  
**Lines:** 522-527  
**Date:** 2026-06-06 04:38 UTC

```python
# Check if result is a coroutine (some tools may return coroutines)
# This can happen with the 'execute' tool in discovery mode
if inspect.iscoroutine(result):
    self.logger.debug(f"Tool '{tool_name}' returned a coroutine, awaiting it")
    result = await result
    self.logger.debug(f"After await - result type: {type(result)}")
```

### How It Works
1. After calling `tool.ainvoke()`, check if result is a coroutine
2. If yes, await it to get the actual result
3. Then proceed with tuple unpacking: `(content, artifact) = result`

### Verification
Test script `test_execute_tool_errors.py` confirms:
- ✅ Coroutines are properly detected and awaited
- ✅ Tuple unpacking works correctly after awaiting
- ✅ Content is correctly extracted from `(content, artifact)` tuple

## Error 2: SSL Certificate Verification Error

### Status: ⚠️ SERVER-SIDE ISSUE

### Error Message
```
Error calling tool 'gcm_AssetDiscoveryService_GetTransformations':
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: self-signed certificate (_ssl.c:1004)
```

### Root Cause Analysis

**Architecture:**
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
1. The `execute` tool is implemented **on the GCM MCP Server** (server-side), not in our client code
2. When `execute` runs a workflow, it makes **internal HTTP calls** to GCM API endpoints
3. These internal calls fail SSL verification because:
   - GCM uses self-signed certificates
   - MCP server has SSL verification enabled
   - MCP server's httpx/requests clients don't trust the self-signed cert

**Why Client-Side SSL Bypass Doesn't Help:**
- Our SSL bypass in `gcm_agent/__init__.py` only affects httpx clients created by **our code**
- The MCP server is a **separate Python process** running on the GCM server
- Our module-level patch doesn't affect the MCP server's process
- The SSL error occurs **inside the MCP server**, not in our client

### What We've Already Fixed (Client-Side)

✅ **Module-Level SSL Bypass** (`gcm_agent/__init__.py`)
- Patches `httpx.AsyncClient.__init__` globally
- Applied before any imports
- Affects all httpx clients in our code

✅ **GCM Auth Client Factory** (`gcm_agent/auth/gcm_auth.py`)
- Lines 374-407, 180-196, 228-247
- Only passes `verify=True` when explicitly needed
- Respects module-level SSL bypass

✅ **Keycloak Auth Client** (`gcm_agent/auth/keycloak_auth.py`)
- Lines 103-112, 173-182
- Only passes `verify=True` when explicitly needed
- Respects module-level SSL bypass

### What Cannot Be Fixed Client-Side

❌ **MCP Server Internal API Calls**
- The `execute` tool runs on the GCM MCP server
- Makes internal httpx/requests calls to GCM APIs
- These calls are server-side, not client-side
- Our client code cannot control them

### Solutions Required (Server-Side)

#### Option 1: Configure MCP Server (RECOMMENDED for Development)

Contact GCM administrator to configure the MCP server:

```yaml
# File: charts/aim-mcp-server/values.yaml (or similar)
backends:
  - name: gcm
    server: https://gcm.example.com:9443
    verify_ssl: false  # ← Add this configuration
```

#### Option 2: Install Proper SSL Certificates (RECOMMENDED for Production)

```bash
# 1. Obtain certificate from trusted CA
# 2. Install on GCM server
# 3. Configure GCM to use the certificate
# 4. Restart GCM services
```

#### Option 3: Add CA Certificate to MCP Server Trust Store

```bash
# If MCP server runs in container/pod
kubectl exec -it <mcp-server-pod> -- bash
cp /path/to/ca-cert.pem /usr/local/share/ca-certificates/gcm-ca.crt
update-ca-certificates
# Restart MCP server
```

## Testing

### Verify Client-Side Fixes
```bash
source .venv/bin/activate
python test_execute_tool_errors.py
```

**Expected Output:**
```
Tests Passed: 3/3
✅ ALL TESTS PASSED
```

### Verify SSL Bypass
```bash
source .venv/bin/activate
python test_ssl_bypass_verification.py
```

## Recommendations

### Immediate Action (Development/Testing)
1. **Error 1**: ✅ No action needed - already fixed
2. **Error 2**: Contact GCM administrator to:
   - Disable SSL verification in MCP server configuration
   - Or provide the CA certificate used by GCM
   - Or install proper SSL certificates on GCM

### Long-Term Solution (Production)
1. Install valid SSL certificates from trusted CA on GCM server
2. Remove all SSL bypass workarounds
3. Enable SSL verification everywhere (client + server)

## Related Documentation

- **Full SSL Analysis:** `SSL_BYPASS_MCP_SERVER_ISSUE.md`
- **Client SSL Fixes:** `SSL_BYPASS_FIX.md`
- **Keycloak SSL Fix:** `test_keycloak_ssl_bypass_fix.py`
- **Test Scripts:** `test_ssl_bypass_*.py`, `test_execute_tool_errors.py`

## Conclusion

**Error 1 (Coroutine Subscriptable):** ✅ **RESOLVED**
- Fixed in `gcm_agent/mcp/client.py` lines 522-527
- Coroutines are properly awaited before tuple unpacking
- Verified by test suite

**Error 2 (SSL Verification):** ⚠️ **REQUIRES SERVER-SIDE ACTION**
- Cannot be fixed from client code
- The `execute` tool runs on the GCM MCP Server (remote service)
- SSL errors occur during MCP server's internal API calls
- Requires GCM administrator to configure MCP server SSL settings

**Action Required:** Contact GCM administrator to configure the MCP server to bypass SSL verification or install proper SSL certificates.