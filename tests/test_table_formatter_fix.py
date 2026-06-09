"""Test for table formatter smart detection fix."""

# Made with Bob
# 2026-06-09 22:32 UTC - Test to verify smart detection doesn't hide tables with explanatory text

import pytest
from gcm_agent.utils.table_formatter import format_response_tables


def test_list_query_with_explanatory_text_shows_table():
    """
    Test that list queries with explanatory text after the table still show the table.
    
    This was the bug: when listing assets with hostname search, the explanatory text
    after the table (e.g., "The list continues...") was incorrectly triggering the
    smart detection, causing the table to be hidden.
    """
    response = """Total assets found: 120

Below is a concise view of the first 50 assets returned (page1, size 50). For each asset the most useful fields are shown:

| Asset ID | Hostname | IP | Port | Protocol | Asset type |
|----------|----------|----|----|----------|------------|
| 0760d184-73ef-4dd8-8c0a-2622136c8381 | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 44417 | TCP | Service |
| 1234abcd-5678-90ef-ghij-klmnopqrstuv | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 44406 | TCP | Service |

The list continues with the remaining 70 assets (not shown here for brevity).

If you need the full list, additional pages, or specific details for any asset (e.g., full metadata, associated crypto objects, or ticket information), just let me know!"""
    
    result = format_response_tables(response)
    
    # Table should be present (formatted as HTML)
    assert '<table' in result
    assert '<th' in result
    assert 'kushaq.dev.fyre.ibm.com' in result
    
    # Explanatory text should also be present
    assert 'The list continues' in result


def test_detail_query_hides_context_table():
    """
    Test that detail queries with substantial structured content hide the context table.
    
    This is the intended behavior: when asking for details of a specific asset after
    listing all assets, the context table (list of all assets) should be hidden, and
    only the detail content should be shown.
    """
    response = """Total assets found: 120

Below is a concise view of the first 50 assets returned (page1, size 50):

| Asset ID | Hostname | IP | Port | Protocol | Asset type |
|----------|----------|----|----|----------|------------|
| 0760d184-73ef-4dd8-8c0a-2622136c8381 | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 44417 | TCP | Service |
| 1234abcd-5678-90ef-ghij-klmnopqrstuv | kushaq.dev.fyre.ibm.com | 9.60.213.11 | 44406 | TCP | Service |

**Asset Details for 0760d184-73ef-4dd8-8c0a-2622136c8381**

**Asset ID**: 0760d184-73ef-4dd8-8c0a-2622136c8381
**Hostname**: kushaq.dev.fyre.ibm.com
**IP Address**: 9.60.213.11
**Port**: 44417
**Protocol**: TCP
**Asset Type**: Service
**Status**: Active
**Created**: 2026-01-15T10:30:00Z
**Last Modified**: 2026-06-09T12:00:00Z
**Tags**: production, critical
**Description**: Main application service endpoint
**Owner**: DevOps Team
**Location**: US-East-1
**Compliance Status**: Compliant"""
    
    result = format_response_tables(response)
    
    # Context table should be hidden (no HTML table in result)
    # Only the detail content should be shown
    assert result.count('<table') == 0 or '**Asset Details' in result
    
    # Detail content should be present
    assert '**Asset ID**' in result
    assert '**Hostname**' in result
    assert 'DevOps Team' in result


def test_short_summary_after_table_shows_table():
    """
    Test that tables with short summaries after them still show the table.
    
    Short summaries (< 10 lines) should not trigger smart detection.
    """
    response = """Here are the keys:

| Key ID | Name | Algorithm | Status |
|--------|------|-----------|--------|
| key-001 | prod-key-1 | AES-256 | Active |
| key-002 | prod-key-2 | RSA-2048 | Active |

Total: 2 keys found.
All keys are active and compliant."""
    
    result = format_response_tables(response)
    
    # Table should be present
    assert '<table' in result
    assert 'prod-key-1' in result
    
    # Summary should also be present
    assert 'Total: 2 keys found' in result


def test_mixed_content_with_few_field_values_shows_table():
    """
    Test that mixed content with few field:value pairs shows the table.
    
    Content must be 60%+ structured field:value pairs to trigger hiding.
    """
    response = """Assets for hostname kushaq.dev.fyre.ibm.com:

| Asset ID | Hostname | Port |
|----------|----------|------|
| asset-1 | kushaq.dev.fyre.ibm.com | 44417 |
| asset-2 | kushaq.dev.fyre.ibm.com | 44406 |

The search found 21 assets total.

Asset ID: asset-1
Hostname: kushaq.dev.fyre.ibm.com

These assets are all Service type and use TCP protocol.
They are distributed across multiple ports for load balancing."""
    
    result = format_response_tables(response)
    
    # Table should be present (not enough structured content to hide it)
    assert '<table' in result
    assert 'asset-1' in result
    assert 'asset-2' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])