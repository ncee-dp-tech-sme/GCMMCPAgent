"""Test multi-table detection in table formatter."""

# Made with Bob
# 2026-06-09 22:40 UTC - Test for multi-table scenario where first table should be hidden

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gcm_agent.utils.table_formatter import format_response_tables


def test_multi_table_hides_first_table():
    """Test that when two tables exist, the first (broader) table is hidden."""
    
    # Simulate response with:
    # 1. First table showing all 120 assets (first 50)
    # 2. Explanatory text about pagination
    # 3. Text about filtering
    # 4. Second table showing just 1 filtered asset
    response = """Here are all the assets:

| Asset ID | Type | Hostname | IP | Created at (UTC) | Updated at (UTC) |
|----------|------|----------|----|--------------------|---------------------|
| abc123 | Service | server1.example.com | 10.0.0.1 | 2026-05-27 22:04:20 | 2026-05-27 22:04:20 |
| def456 | Service | server2.example.com | 10.0.0.2 | 2026-05-27 22:04:20 | 2026-05-27 22:04:20 |
| ghi789 | Service | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 2026-05-27 22:04:20 | 2026-05-27 22:04:20 |

Total assets returned: 120

The response includes the first 50 assets (page1). If you need additional pages, let me know and I can fetch them for you.

All IT assets whose hostname is kushaq.dev.fyre.ibm.com

| Asset ID | Type | Hostname | IP | Created at (UTC) | Updated at (UTC) |
|----------|------|----------|----|--------------------|---------------------|
| ghi789 | Service | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 2026-05-27 22:04:20 | 2026-05-27 22:04:20 |
"""
    
    result = format_response_tables(response)
    
    # First table should be hidden
    assert 'server1.example.com' not in result, "First table should be hidden"
    assert 'server2.example.com' not in result, "First table should be hidden"
    
    # Second table should be shown (formatted as HTML)
    assert 'kushaq.dev.fyre.ibm.com' in result, "Second table should be shown"
    assert '<table' in result, "Second table should be formatted as HTML"
    
    # Explanatory text should be preserved
    assert 'All IT assets whose hostname is' in result, "Explanatory text should be preserved"
    
    print("✓ Multi-table detection test passed")


def test_single_table_still_shown():
    """Test that single table responses still work correctly."""
    
    response = """Here are all the assets:

| Asset ID | Type | Hostname |
|----------|------|----------|
| abc123 | Service | server1.example.com |
| def456 | Service | server2.example.com |

Total assets: 2
"""
    
    result = format_response_tables(response)
    
    # Table should be shown
    assert 'server1.example.com' in result, "Single table should be shown"
    assert 'server2.example.com' in result, "Single table should be shown"
    assert '<table' in result, "Table should be formatted as HTML"
    
    print("✓ Single table test passed")


def test_detail_query_with_field_values():
    """Test that detail queries with field:value pairs still hide context tables."""
    
    response = """Here are all the keys:

| Key ID | Name | Type |
|--------|------|------|
| key1 | MyKey1 | AES |
| key2 | MyKey2 | RSA |

**Key Details for MyKey1:**

**Key ID**: key1
**Name**: MyKey1
**Type**: AES-256
**Created**: 2026-05-27
**Status**: Active
**Algorithm**: AES
**Size**: 256 bits
**Usage**: Encryption
**Owner**: admin
**Description**: Production encryption key
"""
    
    result = format_response_tables(response)
    
    # First table should be hidden
    assert 'key2' not in result or '<table' not in result.split('key2')[0], \
        "Context table should be hidden when detail content exists"
    
    # Detail content should be shown
    assert '**Key ID**: key1' in result, "Detail content should be shown"
    assert 'AES-256' in result, "Detail content should be shown"
    
    print("✓ Detail query test passed")


if __name__ == '__main__':
    test_multi_table_hides_first_table()
    test_single_table_still_shown()
    test_detail_query_with_field_values()
    print("\n✅ All multi-table detection tests passed!")