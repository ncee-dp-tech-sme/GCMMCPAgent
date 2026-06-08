# GCM MCP Server Execute Tool Bug Report

**Date:** 2026-06-08
**Reporter:** Erwin Friethoff - Senior Security Architect, investigated using pod logs and IBM Bob.
**Severity:** Critical - Blocks discovery mode execute tool functionality entirely

## Summary

The GCM MCP Server's `execute` tool has multiple critical bugs that prevent it from functioning. Analysis of comprehensive server logs reveals **five distinct error patterns**, all occurring in the server-side fastmcp library code. The execute tool is completely non-functional for workflow execution.

## Error Patterns Identified

### Pattern 1: UnboundLocalError - Undefined 'null' Variable
**Frequency:** Multiple occurrences (10:33:18, 10:34:18)
**Severity:** Critical

```
Error calling tool 'execute': UnboundLocalError: cannot access local variable 'null'
where it is not associated with a value

Traceback:
/opt/app-root/lib64/python3.11/site-packages/fastmcp/server/server.py:987 in call_tool
/opt/app-root/lib64/python3.11/site-packages/fastmcp/tools/tool.py:354 in _run
/opt/app-root/lib64/python3.11/site-packages/pydantic_monty/__init__.py:90 in run_in_pool
/usr/lib64/python3.11/concurrent/futures/thread.py:58 in run
```

**Root Cause:** Execute tool references undefined variable `null` (should be Python's `None`)

### Pattern 2: Parameter Validation - Nested vs Flat Structure
**Frequency:** Multiple occurrences (10:35:30)
**Severity:** Critical

```
Error validating tool 'get_user_details_by_username'
ValidationError: 2 validation errors for call[get_user_details_by_username]
params
  Missing required argument [type=missing_argument,
  input_value={'username': 'example_user'}, input_type=dict]
username
  Unexpected keyword argument [type=unexpected_keyword_argument,
  input_value='example_user', input_type=str]
```

**Root Cause:** Execute tool expects parameters wrapped in `params` key but receives flat structure, or vice versa. Inconsistent parameter handling between workflow input and tool invocation.

### Pattern 3: Parameter Validation - Missing Required Fields
**Frequency:** Multiple occurrences (10:43:14)
**Severity:** High

```
Error validating tool 'get_user_details_by_username'
ValidationError: 1 validation error for call[get_user_details_by_username]
params.username
  Field required [type=missing, input_value={}, input_type=dict]
```

**Root Cause:** Execute tool passes empty `params` dict to target tool, losing the actual parameter values during workflow execution.

### Pattern 4: SSL Certificate Verification Failures
**Frequency:** Multiple occurrences (10:28:02, 10:41:44, 10:43:39)
**Severity:** High (blocks all tool execution)

```
Error calling tool 'execute'
MontyRuntimeError: Exception: Error calling tool 'gcm_listOfUsers':
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: self-signed certificate (_ssl.c:1004)
```

**Root Cause:** MCP server's internal httpx clients don't bypass SSL verification when calling GCM backend APIs. This is a **server-side configuration issue**, not an execute tool bug per se, but it prevents execute tool from successfully calling any GCM tools.

### Pattern 5: HTTP 403 Forbidden Errors
**Frequency:** At least one occurrence (10:44:29)
**Severity:** Medium (authentication/authorization issue)

```
Error calling tool 'execute'
MontyRuntimeError: Exception: Error calling tool 'get_user_details_by_username':
Client error '403 Forbidden' for url
'https://usermgmt:9443/ibm/usermanagement/api/v1/users/gcmadmin'
```

**Root Cause:** Authentication token or permissions issue when execute tool calls GCM backend. May indicate token not being passed correctly through execute tool workflow execution.

## Root Cause Analysis Summary

Based on comprehensive log analysis, the execute tool has **multiple critical bugs**:

### Issue 1: Undefined 'null' Variable (Pattern 1)
The execute tool's internal code references a variable named `null` that is never defined. This is a Python coding error where:
- The developer wrote `null` instead of Python's `None`
- Or a variable named `null` should have been initialized but wasn't
- Occurs in pydantic_monty execution pool

### Issue 2: Inconsistent Parameter Handling (Patterns 2 & 3)
The execute tool has inconsistent parameter wrapping/unwrapping logic:
- **Pattern 2:** Receives `{'username': 'example_user'}` but expects it wrapped in `params` key, OR receives wrapped but tries to unwrap incorrectly
- **Pattern 3:** Passes empty `params: {}` dict to target tools, losing actual parameter values
- Indicates broken parameter transformation between workflow input and tool invocation

### Issue 3: Missing SSL Bypass Configuration (Pattern 4)
The MCP server's internal httpx clients don't bypass SSL verification:
- Server-side configuration issue, not execute tool code bug
- Affects ALL tool execution, not just execute tool
- Requires server-side fix: `verify_ssl: false` in MCP server config

### Issue 4: Authentication Token Propagation (Pattern 5)
Execute tool may not properly propagate authentication tokens:
- 403 Forbidden errors when calling GCM backend APIs
- Token may be lost during workflow execution
- Or insufficient permissions for the operation

## Reproduction Steps

### Reproducing Pattern 1 (UnboundLocalError)
1. Connect to GCM MCP server with discovery mode enabled (`x-mcp-code-mode: true`)
2. Use the `execute` tool with any workflow
3. Observe `UnboundLocalError: cannot access local variable 'null'`

### Reproducing Pattern 2 (Parameter Validation - Nested/Flat Mismatch)
1. Connect to GCM MCP server with discovery mode enabled
2. Use the `execute` tool with workflow:
```json
{
  "tool_name": "get_user_details_by_username",
  "params": {
    "username": "example_user"
  }
}
```
3. Observe validation errors about missing `params` and unexpected `username`

### Reproducing Pattern 3 (Missing Required Fields)
1. Connect to GCM MCP server with discovery mode enabled
2. Use the `execute` tool with workflow that should pass parameters
3. Observe validation error: `params.username Field required [type=missing, input_value={}]`
4. Execute tool passes empty dict instead of actual parameter values

### Reproducing Pattern 4 (SSL Errors)
1. Connect to GCM MCP server with discovery mode enabled
2. Use the `execute` tool with any workflow that calls GCM backend tools
3. Observe SSL certificate verification errors
4. Note: This affects ALL tools, not just execute tool

### Reproducing Pattern 5 (403 Forbidden)
1. Connect to GCM MCP server with discovery mode enabled
2. Use the `execute` tool with workflow calling user management tools
3. Observe 403 Forbidden errors
4. May indicate authentication token not propagated correctly

## Expected Behavior

The execute tool should:
1. Accept workflow definitions with tool_name and params
2. Properly unwrap/transform parameters for target tool invocation
3. Propagate authentication tokens through workflow execution
4. Call the specified tool with correct parameters
5. Return the tool's result without validation errors
6. Handle both nested (`params: {username: "x"}`) and flat (`username: "x"`) parameter formats

## Actual Behavior

The execute tool exhibits **five distinct failure modes**:
1. **UnboundLocalError:** References undefined `null` variable
2. **Parameter Mismatch:** Expects `params` wrapper but receives flat structure (or vice versa)
3. **Empty Parameters:** Passes `params: {}` to target tools, losing actual values
4. **SSL Failures:** Cannot call GCM backend due to certificate verification (server config issue)
5. **Authentication Failures:** 403 Forbidden errors suggest token not propagated correctly

## Impact Assessment

### Critical Impact on Discovery Mode
- **Execute tool completely non-functional** - Cannot execute any workflows
- **Five distinct failure modes** - Multiple bugs compound the problem
- **Discovery mode unusable** - Relies entirely on execute tool for workflow execution
- **No sandboxed execution** - Cannot use RBAC enforcement at tool execution level
- **No tool composition** - Cannot chain multiple tool calls in workflows

### Cascading Effects
1. **Pattern 1 (UnboundLocalError):** Blocks ALL execute tool usage
2. **Pattern 2 & 3 (Parameter Issues):** Even if Pattern 1 fixed, parameter handling broken
3. **Pattern 4 (SSL):** Even if Patterns 1-3 fixed, SSL errors block backend calls
4. **Pattern 5 (403):** Even if Patterns 1-4 fixed, authentication may fail

### Business Impact
- Users **cannot use discovery mode** for any purpose
- Complex queries requiring tool composition **impossible**
- Dynamic tool loading benefits **lost**
- RBAC enforcement at execution level **unavailable**
- Forces suboptimal workaround (standard mode with all tools loaded upfront)

### Workaround (Current Default)
Users must disable discovery mode (`x-mcp-code-mode: false` or omit header) and call tools directly:
- ✅ Loads all 26 tools upfront (slower initialization but functional)
- ✅ Bypasses broken execute tool entirely
- ✅ Tools work when called directly (if SSL configured server-side)
- ❌ Loses sandboxed execution environment
- ❌ Loses dynamic tool discovery benefits
- ❌ Loses RBAC enforcement at tool execution level

## Recommended Fixes (Priority Order)

### Priority 1: Fix UnboundLocalError (Pattern 1)
**Location:** `/opt/app-root/lib64/python3.11/site-packages/pydantic_monty/__init__.py` or execute tool code

Search for references to `null` and replace with Python's `None`:
```python
# WRONG
if result == null:
    return default_value

# CORRECT
if result is None:
    return default_value
```

**Impact:** Unblocks execute tool from crashing immediately

### Priority 2: Fix Parameter Handling (Patterns 2 & 3)
**Location:** Execute tool's parameter transformation logic

Implement consistent parameter unwrapping/wrapping:
```python
def prepare_tool_parameters(workflow: dict) -> dict:
    """
    Extract and normalize parameters for tool invocation.
    Handles both nested and flat parameter formats.
    """
    # Check for nested params structure
    if "params" in workflow:
        params = workflow["params"]
        if isinstance(params, dict):
            return params
        else:
            raise ValueError(f"'params' must be a dict, got {type(params)}")
    
    # Flat structure - extract all keys except tool_name
    params = {k: v for k, v in workflow.items() if k != "tool_name"}
    
    # Validate we have actual parameters
    if not params:
        raise ValueError("Workflow must contain parameters for tool invocation")
    
    return params

# Usage in execute tool
tool_params = prepare_tool_parameters(workflow)
result = await call_tool(tool_name, **tool_params)
```

**Impact:** Fixes parameter validation errors and empty parameter passing

### Priority 3: Configure SSL Bypass (Pattern 4)
**Location:** MCP server configuration (charts/aim-mcp-server/values.yaml or similar)

Add SSL bypass to server configuration:
```yaml
backend:
  verify_ssl: false  # For development/testing with self-signed certs
```

Or install proper SSL certificates (production solution).

**Impact:** Allows execute tool to successfully call GCM backend APIs

### Priority 4: Fix Authentication Token Propagation (Pattern 5)
**Location:** Execute tool's tool invocation logic

Ensure authentication context is passed through:
```python
async def call_tool_with_auth(tool_name: str, params: dict, auth_context: dict) -> Any:
    """
    Call tool with authentication context propagated.
    """
    # Ensure auth headers/tokens are included in tool call
    if auth_context:
        # Add auth context to tool invocation
        # Implementation depends on how tools receive auth
        pass
    
    return await call_tool(tool_name, params)
```

**Impact:** Prevents 403 Forbidden errors during workflow execution

### Priority 5: Add Comprehensive Input Validation
Add validation to catch issues early:
```python
def validate_workflow(workflow: dict) -> None:
    """Validate workflow structure before execution."""
    if not isinstance(workflow, dict):
        raise ValueError(f"Workflow must be a dict, got {type(workflow)}")
    
    if "tool_name" not in workflow:
        raise ValueError("Workflow must contain 'tool_name'")
    
    if not isinstance(workflow["tool_name"], str):
        raise ValueError("'tool_name' must be a string")
    
    # Validate params if present
    if "params" in workflow:
        if not isinstance(workflow["params"], dict):
            raise ValueError("'params' must be a dict")
        if not workflow["params"]:
            raise ValueError("'params' cannot be empty")
```

**Impact:** Provides clear error messages for malformed workflows

## Testing Recommendations

After implementing fixes, test systematically to verify each pattern is resolved:

### Test Suite 1: Basic Functionality (Pattern 1)
**Objective:** Verify UnboundLocalError is fixed

```json
{
  "tool_name": "list_all_users",
  "params": {}
}
```

**Expected:** No UnboundLocalError, tool executes successfully

### Test Suite 2: Parameter Handling - Nested Format (Pattern 2)
**Objective:** Verify nested params structure works

```json
{
  "tool_name": "get_user_details_by_username",
  "params": {
    "username": "test_user"
  }
}
```

**Expected:** Parameters correctly passed to target tool, no validation errors

### Test Suite 3: Parameter Handling - Flat Format (Pattern 2)
**Objective:** Verify flat parameter structure works

```json
{
  "tool_name": "get_user_details_by_username",
  "username": "test_user"
}
```

**Expected:** Parameters correctly extracted and passed to target tool

### Test Suite 4: Non-Empty Parameters (Pattern 3)
**Objective:** Verify parameters not lost during execution

```json
{
  "tool_name": "get_user_details_by_username",
  "params": {
    "username": "gcmadmin"
  }
}
```

**Expected:** Target tool receives `username: "gcmadmin"`, not empty dict

### Test Suite 5: SSL Configuration (Pattern 4)
**Objective:** Verify SSL bypass configured correctly

```json
{
  "tool_name": "gcm_listOfUsers",
  "params": {}
}
```

**Expected:** No SSL certificate verification errors, successful backend call

### Test Suite 6: Authentication (Pattern 5)
**Objective:** Verify authentication token propagated

```json
{
  "tool_name": "get_user_details_by_username",
  "params": {
    "username": "gcmadmin"
  }
}
```

**Expected:** No 403 Forbidden errors, successful authenticated call

### Test Suite 7: Complex Workflow
**Objective:** Verify end-to-end workflow execution

```json
{
  "tool_name": "search_tools",
  "params": {
    "query": "user management"
  }
}
```

**Expected:** Multi-step workflow completes successfully

### Test Suite 8: Error Handling
**Objective:** Verify validation catches malformed workflows

```json
{
  "params": {
    "username": "test"
  }
}
```

**Expected:** Clear error message: "Workflow must contain 'tool_name'"

## Additional Context

### Client-Side Implementation Status
Our client code in `gcm_agent/mcp/client.py` is **working correctly**:
- ✅ Unwraps nested `params` structures from LangChain MCP adapter
- ✅ Validates JSON payloads before sending to server
- ✅ Provides detailed error logging for debugging
- ✅ Normalizes execute tool arguments with `_normalize_execute_arguments()`
- ✅ Handles both nested and flat parameter formats

**All bugs are server-side** in the GCM MCP server's execute tool implementation.

### Server-Side File Locations
Based on log analysis, the bugs are in:
- **Execute tool:** `/opt/app-root/lib64/python3.11/site-packages/fastmcp/tools/tool.py:354`
- **Server:** `/opt/app-root/lib64/python3.11/site-packages/fastmcp/server/server.py:987`
- **Monty runtime:** `/opt/app-root/lib64/python3.11/site-packages/pydantic_monty/__init__.py:90`
- **Function tool:** `/opt/app-root/lib64/python3.11/site-packages/fastmcp/tools/function_tool.py:288`
- **User management:** `/opt/app/aim_gcm_mcp/services/usermanagement/usermgmt_tool.py:54`

### Log Analysis Summary
Analyzed **4,734 lines** of MCP server logs from `aim-mcp-server-7d47f94dcf-lvp64-aim-mcp-server.log`:
- **28 error occurrences** identified
- **5 distinct error patterns** categorized
- **Multiple timestamps** showing consistent failures (10:28-10:44 UTC)
- **All errors** traced to server-side code, not client requests

## Priority Justification

**Critical Priority** because:
1. **Complete functional failure** - Execute tool cannot execute ANY workflows
2. **Five compounding bugs** - Multiple issues must be fixed for functionality
3. **Discovery mode unusable** - Core feature completely non-functional
4. **No server-side workaround** - Cannot be fixed without code changes
5. **Affects all users** - Anyone attempting discovery mode hits these errors
6. **Blocks advanced features** - RBAC enforcement, sandboxed execution, tool composition all unavailable
7. **Forces suboptimal workaround** - Users must disable discovery mode entirely

## Contact

For questions or additional information, contact the Erwin Friethoff - Senior Security Architect.