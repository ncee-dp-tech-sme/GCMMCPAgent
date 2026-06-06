# JSON Parsing Error Fix - Investigation Report

## Date: 2026-06-06

## Summary
The reported "JSON parsing error" was actually a **discovery mode execute tool misuse issue**, not a JSON parsing problem. The LLM was incorrectly calling the `execute` tool for simple queries, causing errors from bugs in the GCM MCP server's execute tool implementation.

## Root Cause Analysis

### Reported Errors
```
Error calling tool 'execute': Expected `}`, found `)` at byte range 280..281
Error calling tool 'execute': Exception: Unknown tool: list_tools
Error calling tool 'execute': NameError: name 'params' is not defined
```

### Actual Problem
1. **Discovery mode was enabled** (default after recent fix)
2. **LLM was using `execute` tool incorrectly** for simple data retrieval queries
3. **Execute tool has bugs** on the GCM MCP server side:
   - Tries to call non-existent tools like `list_tools`
   - Has internal code bugs (`NameError: name 'params' is not defined`)

### Why This Happened
The discovery mode prompt instructed the LLM to use this workflow:
```
1. search_tools → 2. get_schema → 3. execute (WRONG!)
```

But for simple queries like "get all certificates", the correct workflow should be:
```
1. search_tools → 2. get_schema → 3. call tool DIRECTLY (not via execute)
```

## The Fix

### 1. Updated Discovery Mode Prompt (`gcm_agent/agent/prompts.py`)

**Added explicit guidelines:**
- ✅ **Simple queries**: Call tools directly after discovery
- ❌ **DO NOT** use execute tool for simple data retrieval
- ℹ️ **Execute tool**: Reserved for complex multi-step workflows only

**Added example workflow:**
```
For "get all certificates":
1. search_tools(query="certificate") → finds "list_certificates"
2. get_schema(tool_name="list_certificates") → understand parameters
3. list_certificates(params) → call DIRECTLY (not via execute)
```

### 2. Added Comprehensive JSON Logging (`gcm_agent/mcp/client.py`)

Added detailed logging to `execute_tool()` method to help debug future issues:
- Logs raw arguments before and after unwrapping
- Validates JSON serialization at each step
- Logs tool results with JSON parsing validation
- Identifies where malformed data originates (LLM, unwrapping, or tool response)

### 3. Updated Documentation (`AGENTS.md`)

Added section documenting:
- The root cause of execute tool misuse
- The fix applied to the prompt
- Recommendation to keep discovery mode disabled by default
- When to enable discovery mode (advanced scenarios only)

## Testing Instructions

To verify the fix works:

1. **Restart the agent** to load the updated prompt:
   ```bash
   python app.py
   ```

2. **Test the failing queries** in the Chat tab:
   - "get all certificates"
   - "Fetch the policy violations dashboard"
   - "get all assets"

3. **Expected behavior:**
   - LLM should call tools directly (not via execute)
   - No "Unknown tool" or "NameError" errors
   - Queries should return actual data

4. **Check logs** for the new JSON debugging output:
   - Look for "EXECUTE TOOL DEBUG" sections
   - Verify arguments are valid JSON
   - Verify tool results are valid JSON

## Recommendation

**Keep discovery mode DISABLED (default)** for most use cases because:
- ✅ Faster responses (all tools loaded upfront)
- ✅ More reliable (no execute tool bugs)
- ✅ Simpler workflow (direct tool calls)

**Enable discovery mode ONLY when:**
- Dynamic tool discovery is required
- Complex workflows need sandboxed execution
- RBAC enforcement at tool execution level is needed

## Files Modified

1. `gcm_agent/agent/prompts.py` - Updated discovery mode prompt
2. `gcm_agent/mcp/client.py` - Added JSON debugging logs
3. `AGENTS.md` - Documented the fix
4. `JSON_PARSING_ERROR_FIX.md` - This report

## Next Steps

1. Test the fix with the failing queries
2. If issues persist, check the JSON debugging logs
3. Consider disabling discovery mode if not needed
4. Report any remaining issues with log excerpts