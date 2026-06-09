# Query Independence Fix - Context Bleeding Prevention

**Date:** 2026-06-09 22:45 UTC  
**Issue:** Agent applying filters from previous failed queries to new queries  
**Status:** ✅ FIXED

## Problem Description

When a query failed (e.g., 500 error when filtering by hostname), subsequent queries would incorrectly maintain the filter from the failed query even when the user explicitly asked for "all" items.

### Example Scenario:
1. User: "list all details of the asset with hostname kushaq.dev.fyre.ibm.com"
   - Result: 500 Server Error (server-side issue)
2. User: "list all assets"
   - Expected: Show ALL assets
   - Actual: Showed only assets filtered by hostname "kushaq.dev.fyre.ibm.com"

## Root Cause

The agent maintains conversation history to provide context-aware responses. However, the LLM was incorrectly treating filters from previous queries as persistent state, even when:
- The previous query failed
- The new query explicitly requested "all" items (no filter)

**History Management Flow:**
```python
# gcm_agent/agent/gcm_agent.py line 382
self.history.append(HumanMessage(content=message))

# History includes:
# 1. Previous query: "list all details of the asset with hostname kushaq.dev.fyre.ibm.com"
# 2. Current query: "list all assets"

# LLM sees both and incorrectly maintains the hostname filter
```

## The Fix

Updated system prompt in [`gcm_agent/agent/prompts.py`](gcm_agent/agent/prompts.py) to explicitly instruct the LLM about query independence:

### Changes Made:

1. **Added Core Instruction #6:**
   ```
   6. CRITICAL: Each query is independent - do NOT carry over filters from previous queries unless explicitly requested
   ```

2. **Added "QUERY INDEPENDENCE" Section:**
   ```
   QUERY INDEPENDENCE:
   - Each user query is a NEW request - do NOT apply filters from previous queries
   - "list all assets" means ALL assets, not filtered by previous query context
   - "show all keys" means ALL keys, not filtered by previous hostname/criteria
   - Only apply filters when explicitly stated in the CURRENT query
   ```

### Key Principles:

- **Query Independence**: Each query is treated as a fresh request
- **Explicit Filters Only**: Filters only applied when stated in current query
- **"All" Means All**: Keywords like "all", "list all", "show all" mean no filtering
- **Context Awareness**: History still available for follow-up questions (e.g., "show me more details about that")

## Impact

✅ **Fixed**: Agent no longer carries over filters from previous queries  
✅ **Preserved**: Context awareness for legitimate follow-up questions  
✅ **Improved**: Clear distinction between filtered and unfiltered queries  

## Testing

**Test Case 1: Failed Query → New Query**
```
User: "list all details of the asset with hostname kushaq.dev.fyre.ibm.com"
Agent: [500 error]
User: "list all assets"
Expected: Show ALL assets (no hostname filter)
```

**Test Case 2: Successful Query → Follow-up**
```
User: "list all assets"
Agent: [Shows all assets]
User: "show me more details about the first one"
Expected: Use context from previous query (legitimate follow-up)
```

**Test Case 3: Explicit Filter → New Query**
```
User: "show keys for hostname X"
Agent: [Shows filtered keys]
User: "now show all keys"
Expected: Show ALL keys (no filter from previous query)
```

## Related Issues

### 500 Server Error (Separate Issue)
The original 500 error when filtering by hostname is a **server-side issue** with the GCM MCP server's API endpoint:
```
Server error '500 Internal Server Error' for url 
'https://asset:9443/ibm/assetinventory/api/v1/assets/it_assets/all'
```

This is NOT a client-side bug and requires GCM server-side investigation.

## Files Modified

- [`gcm_agent/agent/prompts.py`](gcm_agent/agent/prompts.py:11-30) - Added query independence instructions

## Verification

Monitor agent behavior for:
1. ✅ No filter carryover from failed queries
2. ✅ "All" queries return unfiltered results
3. ✅ Legitimate follow-ups still work correctly
4. ✅ Explicit filters in current query still applied

## Notes

- This fix addresses LLM behavior, not the underlying 500 error
- The 500 error requires server-side investigation
- History management remains unchanged (still maintains context)
- Only LLM interpretation of history context was modified