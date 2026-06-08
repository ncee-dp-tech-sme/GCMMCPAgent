# GCM Agent Parameter Fix Documentation

**Date:** 2026-06-08  
**Issue:** Missing required parameters causing API validation errors  
**Status:** ✅ RESOLVED

## Problem Summary

The GCM MCP agent was failing to call Guardium APIs correctly because the LLM (WatsonX or OpenAI) was not providing **required parameters** that the GCM APIs expect. This resulted in Pydantic validation errors from the remote GCM MCP server.

### Example Error

```
ValidationError: 2 validation errors for call[fetch_asset_list]
params.body.page_number
  Field required [type=missing, input_value={'filters': {'asset_type'...}]
params.body.page_size
  Field required [type=missing, input_value={'filters': {'asset_type'...}]
```

### Root Cause

1. **LLM Knowledge Gap**: The LLM doesn't inherently know about GCM API requirements
2. **Missing Schema Guidance**: The system prompt didn't emphasize checking tool schemas for required parameters
3. **Common Pattern**: Many GCM list/fetch operations require pagination parameters (`page_number`, `page_size`)

## Solution Implemented

We implemented a **two-layer defense** strategy:

### Layer 1: Enhanced System Prompt (Proactive)

**File:** `gcm_agent/agent/prompts.py`

Added comprehensive parameter guidance to the system prompt:

```python
PARAMETER REQUIREMENTS - READ CAREFULLY:
Many GCM API tools require MANDATORY parameters that you MUST provide:

**Pagination Parameters (REQUIRED for list/fetch operations):**
- `page_number`: Integer, starting from 1 (use 1 for first page)
- `page_size`: Integer, number of items per page (use 50 as default, max 100)
- Example: {"page_number": 1, "page_size": 50}

**BEFORE calling ANY tool:**
1. If in discovery mode, use `get_schema` to see ALL required parameters
2. Check the schema's "required" field for mandatory parameters
3. Provide ALL required parameters, even if they seem optional
4. Use sensible defaults: page_number=1, page_size=50 for pagination
```

**Benefits:**
- Educates the LLM about parameter requirements
- Encourages use of `get_schema` tool in discovery mode
- Provides sensible default values
- Prevents errors before they happen

### Layer 2: Intelligent Parameter Defaults (Reactive)

**File:** `gcm_agent/mcp/client.py`

Added `_add_parameter_defaults()` method that automatically injects missing pagination parameters:

```python
def _add_parameter_defaults(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add intelligent defaults for common required parameters.
    
    Detects list/fetch operations and adds:
    - page_number: 1 (first page)
    - page_size: 50 (reasonable default)
    
    Handles nested structures: body, params, or top-level
    """
```

**Detection Logic:**
- Checks if tool name contains: `list`, `fetch`, `get_all`, `search`, `query`, `dashboard`
- Only adds parameters if they're missing
- Preserves existing values if provided by LLM
- Handles nested structures (`body`, `params`) and top-level parameters

**Benefits:**
- Automatic fallback when LLM forgets parameters
- Zero user intervention required
- Transparent operation (logs when defaults are added)
- Doesn't override explicit LLM choices

## How It Works Together

```
User Query: "Show me all keys"
    ↓
LLM generates tool call: fetch_asset_list(filters={...})
    ↓
Layer 1 (Prompt): LLM should have added page_number/page_size
    ↓
Layer 2 (Defaults): If missing, automatically add page_number=1, page_size=50
    ↓
Final call: fetch_asset_list(filters={...}, page_number=1, page_size=50)
    ↓
✅ API call succeeds
```

## Testing

**Test File:** `test_parameter_defaults.py`

Verified 5 scenarios:
1. ✅ Top-level parameters - adds defaults correctly
2. ✅ Nested body structure - adds to body object
3. ✅ Existing parameters - preserves user/LLM values
4. ✅ Non-list tools - doesn't add unnecessary pagination
5. ✅ Nested params structure - adds to params object

All tests passed successfully.

## Configuration

No configuration changes required. The fix is automatic and transparent.

### For Users

**No action needed.** The agent will now:
- Automatically add pagination parameters when missing
- Log when defaults are applied (visible in debug logs)
- Work correctly with both WatsonX and OpenAI LLMs

### For Developers

**To customize defaults**, edit `gcm_agent/mcp/client.py`:

```python
# Change default page size
if 'page_size' not in enhanced_args:
    enhanced_args['page_size'] = 100  # Change from 50 to 100
```

**To add more parameter defaults**, extend the `_add_parameter_defaults()` method:

```python
# Example: Add default sort order
if needs_pagination and 'sort_order' not in enhanced_args:
    enhanced_args['sort_order'] = 'asc'
```

## What Information to Provide to LLMs

When working with the GCM agent, you can help the LLM by:

### 1. Using Discovery Mode (Recommended)

Enable discovery mode to let the LLM explore tool schemas:

```python
config = AgentConfig(
    discovery_mode=True,  # Enable dynamic tool discovery
    max_iterations=20     # Allow enough iterations for schema checks
)
```

**Benefits:**
- LLM can use `get_schema` to see required parameters
- More accurate parameter selection
- Better error handling

### 2. Providing Context in Queries

Instead of:
```
"Show me all keys"
```

Try:
```
"Show me the first 50 keys (page 1)"
```

This helps the LLM understand pagination requirements.

### 3. Specifying Parameters Explicitly

For complex queries:
```
"Fetch asset list with filters for key type, page 1, 50 items per page"
```

### 4. Using Standard Mode for Simple Queries

If you know exactly which tool to use:

```python
config = AgentConfig(
    discovery_mode=False,  # Load all tools upfront
    max_iterations=10      # Faster for simple queries
)
```

## Common Patterns

### Pagination Parameters

**Always required for:**
- `list_*` tools (list_keys, list_certificates, etc.)
- `fetch_*` tools (fetch_asset_list, fetch_dashboard, etc.)
- `search_*` tools
- `query_*` tools
- `*_dashboard` tools

**Default values:**
- `page_number`: 1 (first page)
- `page_size`: 50 (reasonable default, max usually 100)

### Filter Parameters

Some tools require filter objects even if empty:

```python
# Correct
{"filters": {}, "page_number": 1, "page_size": 50}

# Incorrect (missing filters)
{"page_number": 1, "page_size": 50}
```

### Nested Structures

GCM APIs often use nested parameter structures:

```python
# Body structure
{
    "body": {
        "filters": {...},
        "page_number": 1,
        "page_size": 50
    }
}

# Params structure
{
    "params": {
        "filters": {...},
        "page_number": 1,
        "page_size": 50
    }
}
```

The fix handles all these structures automatically.

## Troubleshooting

### If you still see parameter errors:

1. **Check the error message** - What parameter is missing?
2. **Enable debug logging** - See what defaults are being added
3. **Use get_schema tool** - In discovery mode, check the tool's schema
4. **Check AGENTS.md** - Look for known issues with specific tools

### Debug Logging

Enable detailed logging to see parameter injection:

```python
import logging
logging.getLogger('gcm_agent.mcp').setLevel(logging.DEBUG)
```

You'll see messages like:
```
[INFO] Added default page_number=1 to tool 'fetch_asset_list' body
[INFO] Added default page_size=50 to tool 'fetch_asset_list' body
```

## Future Improvements

Potential enhancements:

1. **Schema-based validation** - Parse tool schemas to detect all required parameters
2. **Dynamic defaults** - Learn optimal page sizes from API responses
3. **Parameter suggestions** - Suggest missing parameters to LLM before calling
4. **Error recovery** - Automatically retry with defaults when validation fails

## Related Documentation

- **AGENTS.md** - Repository-specific agent guidance
- **docs/TROUBLESHOOTING.md** - General troubleshooting guide
- **docs/USER_GUIDE.md** - User-facing documentation
- **GCM_MCP_SERVER_EXECUTE_TOOL_BUG_REPORT.md** - Known server-side issues

## Summary

✅ **Problem:** LLM not providing required parameters (page_number, page_size)  
✅ **Solution:** Two-layer defense (enhanced prompt + automatic defaults)  
✅ **Testing:** All scenarios verified and passing  
✅ **Impact:** Zero user intervention, transparent operation  
✅ **Status:** Production-ready

The agent will now handle parameter requirements automatically while educating the LLM to make better choices in the future.