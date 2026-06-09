# Table Formatter Smart Detection Fix

**Date:** 2026-06-09 22:32 UTC  
**Issue:** Tables incorrectly hidden when listing assets with explanatory text  
**Status:** ✅ Fixed

## Problem Description

When querying for assets by hostname (e.g., "list all details of the asset with hostname kushaq.dev.fyre.ibm.com"), the agent would return a table with 21 assets, but the UI would only show details for the first asset. The table containing all 21 assets was being hidden by the smart detection logic.

### Root Cause

The smart detection logic in [`gcm_agent/utils/table_formatter.py`](../gcm_agent/utils/table_formatter.py) was too aggressive. It was designed to hide context tables when showing detail queries (e.g., "show details for asset X" after "list all assets"), but it was incorrectly triggering on list queries with explanatory text.

**Old Logic (Too Aggressive):**
- If 5+ meaningful lines exist after a table
- AND any of those lines contain `:` (field:value pairs)
- THEN hide the table and show only the after-table content

**The Bug:**
When listing assets, the response included:
```
| Asset ID | Hostname | IP | Port | Protocol | Asset type |
|----------|----------|----|----|----------|------------|
| asset-1  | kushaq... | ... | ...  | TCP      | Service    |
| asset-2  | kushaq... | ... | ...  | TCP      | Service    |

The list continues with the remaining 70 assets (not shown here for brevity).

If you need the full list, additional pages, or specific details for any asset (e.g., full metadata, associated crypto objects, or ticket information), just let me know!Asset ID: 0760d184-73ef-4dd8-8c0a-2622136c8381
Hostname: kushaq.dev.fyre.ibm.com
IP: 9.60.213.11
Port: 44417
Protocol: TCP
Asset type: Service
```

The logic saw:
1. ✓ 5+ meaningful lines after table
2. ✓ Lines with `:` (Asset ID:, Hostname:, etc.)
3. ❌ Incorrectly concluded this was detail content and hid the table

## The Fix

Made the smart detection more strict by requiring:

1. **10+ meaningful lines** (increased from 5) - ensures substantial content
2. **60%+ structured field:value pairs** - ensures content is PRIMARILY structured data, not mixed explanatory text

**New Logic (More Precise):**
```python
if len(meaningful_lines) >= 10:
    # Count lines that look like field:value pairs
    field_value_lines = 0
    for line in meaningful_lines[:15]:
        stripped = line.strip()
        # Match patterns like "Field: value" or "**Field**: value" or "**Field**"
        if (stripped.startswith('**') or 
            (': ' in stripped and not stripped.startswith('If ') and not stripped.startswith('The '))):
            field_value_lines += 1
    
    # If 60%+ of lines are structured field:value pairs, it's detail content
    if field_value_lines >= len(meaningful_lines[:15]) * 0.6:
        # Hide table, show only details
```

## Impact

### Before Fix
- ❌ List queries with explanatory text incorrectly hid tables
- ❌ Users saw only first asset details instead of full list
- ❌ Hostname searches showed 1 asset instead of 21

### After Fix
- ✅ List queries with explanatory text show tables correctly
- ✅ Detail queries still hide context tables (intended behavior)
- ✅ Short summaries after tables don't trigger hiding
- ✅ Mixed content with few field:value pairs shows tables

## Test Coverage

Created comprehensive test suite in [`tests/test_table_formatter_fix.py`](../tests/test_table_formatter_fix.py):

1. ✅ `test_list_query_with_explanatory_text_shows_table` - Verifies list queries show tables
2. ✅ `test_detail_query_hides_context_table` - Verifies detail queries hide context tables
3. ✅ `test_short_summary_after_table_shows_table` - Verifies short summaries don't trigger hiding
4. ✅ `test_mixed_content_with_few_field_values_shows_table` - Verifies mixed content shows tables

All tests pass ✓

## Files Modified

1. [`gcm_agent/utils/table_formatter.py`](../gcm_agent/utils/table_formatter.py) - Updated smart detection logic
2. [`tests/test_table_formatter_fix.py`](../tests/test_table_formatter_fix.py) - New test suite

## Verification

To verify the fix:

```bash
# Run tests
source venv/bin/activate
python -m pytest tests/test_table_formatter_fix.py -v

# Test in UI
python app.py
# Query: "list all details of the asset with hostname kushaq.dev.fyre.ibm.com"
# Expected: Table with all 21 assets displayed
```

## Related Issues

- Smart table detection feature: 2026-06-09 22:00 UTC
- Original implementation: 2026-06-09 21:22 UTC
- See [`docs/TABLE_FORMATTING.md`](TABLE_FORMATTING.md) for full feature documentation