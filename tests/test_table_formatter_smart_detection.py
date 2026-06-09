"""Tests for smart table detection in table formatter."""

import pytest
from gcm_agent.utils.table_formatter import format_response_tables


def test_detail_query_hides_table():
    """Test that detail queries with field:value pairs hide the table and show only details."""
    response = """*The list shows the first 50 assets (out of 120 total). Each row includes the asset's unique ID, type, hostname (if available), IP address, environment, mission-criticality rating, and whether it is internet-facing.*

| Asset ID | Type | Hostname | IP Address | Environment | Mission Critical | Internet Facing |
|----------|------|----------|------------|-------------|------------------|-----------------|
| b59136db-aea4-4a15-9da1-3725d8fe87f3 | Database | app-qa-0yuk.infra.private | 10.20.30.40 | QA | 1 | FALSE |
| other-id | Service | other-host | 10.20.30.41 | PROD | 2 | TRUE |

**Asset ID:** b59136db-aea4-4a15-9da1-3725d8fe87f3

| Field | Value |
|-------|-------|
| Asset Type | Database |
| Asset Sub-type | PostgreSQL |
| Hostname | app-qa-0yuk.infra.private |
| IP Address | 10.20.30.40 |
| Environment | QA |
"""
    
    result = format_response_tables(response)
    
    # Should NOT contain the first table (list of assets)
    assert 'other-id' not in result
    assert 'other-host' not in result
    
    # Should contain the detail content
    assert 'Asset ID:' in result
    assert 'b59136db-aea4-4a15-9da1-3725d8fe87f3' in result
    assert 'Asset Type' in result
    assert 'PostgreSQL' in result
    
    # Should still format the details table as HTML
    assert '<table' in result
    assert 'Asset Sub-type' in result


def test_list_query_shows_table():
    """Test that list queries without detail content show the formatted table."""
    response = """Here are all the assets:

| Asset ID | Type | Hostname |
|----------|------|----------|
| id-1 | Database | host-1 |
| id-2 | Service | host-2 |
| id-3 | Application | host-3 |

*Total: 3 assets found*
"""
    
    result = format_response_tables(response)
    
    # Should contain formatted HTML table
    assert '<table' in result
    assert 'id-1' in result
    assert 'id-2' in result
    assert 'id-3' in result
    assert 'Database' in result
    assert 'Service' in result
    
    # Should contain the summary text
    assert 'Total: 3 assets found' in result


def test_table_with_short_summary_shows_table():
    """Test that tables with only short summaries (< 3 lines) still show the table."""
    response = """| Key ID | Name | Status |
|--------|------|--------|
| key-1 | Primary | Active |
| key-2 | Backup | Inactive |

Found 2 keys.
"""
    
    result = format_response_tables(response)
    
    # Should show the table since after-content is too short
    assert '<table' in result
    assert 'key-1' in result
    assert 'key-2' in result
    assert 'Found 2 keys' in result


def test_no_table_returns_original():
    """Test that responses without tables are returned unchanged."""
    response = "This is a simple response without any tables."
    result = format_response_tables(response)
    assert result == response


def test_detail_without_field_value_pairs_shows_table():
    """Test that content after table without field:value pairs still shows the table."""
    response = """| Asset ID | Type |
|----------|------|
| id-1 | Database |

This is some additional context.
It has multiple lines.
But no field:value pairs.
So it's probably just a summary.
"""
    
    result = format_response_tables(response)
    
    # Should show the table since no field:value pattern detected
    assert '<table' in result
    assert 'id-1' in result
    assert 'Database' in result
    assert 'additional context' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

# Made with Bob
