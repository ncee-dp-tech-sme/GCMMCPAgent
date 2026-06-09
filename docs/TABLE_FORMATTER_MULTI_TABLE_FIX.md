# Table Formatter Multi-Table Detection Fix

**Date:** 2026-06-09 22:40 UTC  
**Issue:** Both broad list table AND filtered detail table displayed in same response  
**Status:** ✅ Fixed

## Problem Description

When querying for specific asset details after listing all assets (e.g., "show me all assets" followed by "show me details of the asset with hostname kushaq.dev.fyre.ibm.com"), the response would include:

1. **First table**: All 120 assets (showing first 50)
2. **Explanatory text**: "The response includes the first 50 assets (page1)..."
3. **Filter description**: "All IT assets whose hostname is kushaq.dev.fyre.ibm.com"
4. **Second table**: Just the 1 filtered asset

Both tables were being displayed, creating visual clutter and confusion.

### Root Cause

The smart detection logic in [`gcm_agent/utils/table_formatter.py`](../gcm_agent/utils/table_formatter.py) only checked for field:value content after the first table. It didn't detect when a **second, more specific table** existed in the response.

**Old Logic:**
- Find first table
- Check if content after table has 10+ lines with 60%+ field:value pairs
- If yes, hide first table and show details
- **Missing**: Detection of second table in the after-table content

**The Bug:**
When the response contained two tables:
```
[Table 1: All 120 assets - first 50 shown]

Total assets returned: 120
The response includes the first 50 assets...

All IT assets whose hostname is kushaq.dev.fyre.ibm.com

[Table 2: Just 1 filtered asset]
```

The logic saw:
1. ✓ First table detected
2. ✓ Content after table (explanatory text + second table)
3. ❌ Didn't detect second table, so showed BOTH tables
4. ❌ Result: User sees duplicate/redundant information

## The Fix

Added **multi-table detection** to check if a second table exists after the first table. If found, the first (broader) table is hidden and only the second (more specific) table is shown.

**New Logic:**
```python
# After finding first table, check for second table
second_table_info = _detect_table_structure(after_table_stripped)

if second_table_info:
    # Second table exists! This is likely a detail query where:
    # - First table = broad list (e.g., all 120 assets)
    # - Second table = filtered/specific result (e.g., 1 asset)
    # Hide first table, show only content after first table
    result_parts = []
    if before_table.strip():
        result_parts.append(before_table.strip())
    # Recursively format the after_table content (contains second table)
    formatted_after = format_response_tables(after_table_stripped)
    result_parts.append(formatted_after)
    return '\n\n'.join(result_parts)
```

## Impact

### Before Fix
- ❌ Both broad list table AND filtered detail table displayed
- ❌ Visual clutter with redundant information
- ❌ User sees 120 assets table + 1 asset table for same query
- ❌ Confusing which table is the actual answer

### After Fix
- ✅ Only the filtered/specific table is shown
- ✅ Explanatory text preserved ("All IT assets whose hostname is...")
- ✅ Clean, focused response showing only relevant data
- ✅ First table hidden when second more-specific table exists

## Test Coverage

Created comprehensive test suite in [`tests/test_multi_table_detection.py`](../tests/test_multi_table_detection.py):

1. ✅ `test_multi_table_hides_first_table` - Verifies first table hidden when second exists
2. ✅ `test_single_table_still_shown` - Verifies single table responses still work
3. ✅ `test_detail_query_with_field_values` - Verifies field:value detection still works

All tests pass ✓

## Files Modified

1. [`gcm_agent/utils/table_formatter.py`](../gcm_agent/utils/table_formatter.py) - Added multi-table detection (lines 145-157)
2. [`tests/test_multi_table_detection.py`](../tests/test_multi_table_detection.py) - New test suite

## Verification

To verify the fix:

```bash
# Run tests
source venv/bin/activate
python tests/test_multi_table_detection.py

# Test in UI
python app.py
# Query 1: "show me all assets"
# Expected: Table with all assets displayed
# Query 2: "show me details of the asset with hostname kushaq.dev.fyre.ibm.com"
# Expected: Only the filtered table (1 asset) displayed, not the broad list
```

## Related Issues

- Previous fix (field:value detection): 2026-06-09 22:32 UTC - [`TABLE_FORMATTER_FIX.md`](TABLE_FORMATTER_FIX.md)
- Smart table detection feature: 2026-06-09 22:00 UTC
- Original implementation: 2026-06-09 21:22 UTC
- See [`docs/TABLE_FORMATTING.md`](TABLE_FORMATTING.md) for full feature documentation

## Design Decision

The multi-table detection takes precedence over field:value detection because:
1. **More explicit signal**: Second table clearly indicates filtered/specific result
2. **Handles edge cases**: Works even when explanatory text doesn't have many field:value pairs
3. **Simpler logic**: "If second table exists, hide first" is easier to understand than percentage thresholds
4. **Better UX**: Users expect to see the most specific/relevant table, not all tables