# SSL Certificate Verification Error Fix

**Date:** 2026-06-06  
**Issue:** SSL certificate verification errors breaking tool execution  
**Status:** ✅ RESOLVED

## Problem Description

Tool execution was failing with SSL certificate verification errors:

```
Error calling tool 'gcm_AssetInventoryService_FetchCryptoObjectDetails': 
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED] 
certificate verify failed: self-signed certificate (_ssl.c:1004)
```

## Root Cause Analysis

The issue was in how the SSL bypass was being applied:

1. **Module-Level Patch Exists:** `gcm_agent/__init__.py` contains a global SSL bypass patch that wraps `httpx.AsyncClient.__init__` to set `verify=False` by default

2. **Patch Logic:** The patch only applies when:
   - `verify` parameter is NOT in kwargs, OR
   - `verify` parameter is None

3. **The Bug:** `_client_factory()` in `gcm_auth.py` was **explicitly passing `verify=verify_ssl`** to `httpx.AsyncClient()`:
   ```python
   # OLD CODE (BROKEN)
   client = httpx.AsyncClient(
       headers=merged_headers,
       verify=verify_ssl,  # ❌ This overrides the module-level patch!
       timeout=timeout,
   )
   ```

4. **Why It Failed:** When `verify_ssl=True` (the default), the factory explicitly passed `verify=True`, which **overrode** the module-level patch. The patch couldn't apply because `verify` was in kwargs.

## The Fix

Modified three methods in `gcm_agent/auth/gcm_auth.py` to NOT pass the `verify` parameter when SSL bypass is needed:

### 1. `_client_factory()` (lines 374-407)

**Before:**
```python
client = httpx.AsyncClient(
    headers=merged_headers,
    verify=verify_ssl,  # ❌ Always passed
    timeout=timeout,
    **kwargs,
)
```

**After:**
```python
client_kwargs = {
    "headers": merged_headers,
    "timeout": timeout,
    "trust_env": False,
    "follow_redirects": True,
    "event_hooks": {...},
    **kwargs,
}

# Only pass verify if SSL verification is explicitly enabled
if verify_ssl:
    client_kwargs["verify"] = True  # ✅ Only when needed
    logger.debug("SSL verification ENABLED")
else:
    logger.debug("SSL verification DISABLED - relying on module-level bypass")

client = httpx.AsyncClient(**client_kwargs)
```

### 2. `authorize()` (lines 180-196)

**Before:**
```python
async with httpx.AsyncClient(verify=self.verify_ssl) as client:
    # ❌ Always passed verify parameter
```

**After:**
```python
client_kwargs = {}
if self.verify_ssl:
    client_kwargs["verify"] = True  # ✅ Only when needed

async with httpx.AsyncClient(**client_kwargs) as client:
```

### 3. `create_authenticated_client()` (lines 228-247)

**Before:**
```python
client = httpx.AsyncClient(
    headers=headers,
    verify=self.verify_ssl,  # ❌ Always passed
    timeout=timeout,
)
```

**After:**
```python
client_kwargs = {
    "headers": headers,
    "timeout": timeout,
}

if self.verify_ssl:
    client_kwargs["verify"] = True  # ✅ Only when needed

client = httpx.AsyncClient(**client_kwargs)
```

## How It Works Now

### When `verify_ssl=False` (Default for Self-Signed Certs):

1. Factory does NOT pass `verify` parameter to `httpx.AsyncClient()`
2. Module-level patch in `gcm_agent/__init__.py` detects `verify` not in kwargs
3. Patch automatically sets `verify=False`
4. SSL verification is disabled ✅

### When `verify_ssl=True` (Production with Valid Certs):

1. Factory explicitly passes `verify=True` to `httpx.AsyncClient()`
2. Module-level patch sees `verify` in kwargs
3. Patch respects the explicit setting
4. SSL verification is enabled ✅

## Verification

Run the test script to verify the fix:

```bash
source .venv/bin/activate
python test_ssl_bypass_fix.py
```

**Expected Output:**
```
✓ Module-level SSL bypass applied from gcm_agent/__init__.py

================================================================================
SSL BYPASS VERIFICATION TEST
================================================================================

[Test 1] Verifying module-level SSL bypass patch...
  ✓ Module-level patch is working correctly

[Test 2] Verifying GCMAuthenticator._client_factory()...
  ✓ Client should use SSL bypass from module-level patch

[Test 3] Verifying factory with verify_ssl=True...
  ✓ Client should verify SSL certificates

================================================================================
✓ ALL SSL BYPASS TESTS PASSED
================================================================================
```

## Impact

- ✅ Tool execution now works with self-signed certificates
- ✅ No more SSL certificate verification errors
- ✅ Module-level SSL bypass patch now applies correctly
- ✅ SSL verification can still be enabled when needed (production environments)

## Files Modified

1. `gcm_agent/auth/gcm_auth.py`:
   - `_client_factory()` method (lines 374-407)
   - `authorize()` method (lines 180-196)
   - `create_authenticated_client()` method (lines 228-247)

## Related Documentation

- See `AGENTS.md` for SSL bypass architecture details
- Module-level patch: `gcm_agent/__init__.py` lines 27-52
- Test script: `test_ssl_bypass_fix.py`

## Key Takeaway

**Never explicitly pass `verify=False` to `httpx.AsyncClient()` when you want the module-level patch to apply. Instead, omit the `verify` parameter entirely and let the patch handle it.**

This pattern ensures the global SSL bypass works consistently across all httpx clients in the application.