"""Tests for table formatting utilities."""

# Made with Bob
# 2026-06-09 21:23 UTC - Initial test suite for table formatter

import pytest
from gcm_agent.utils.table_formatter import format_response_tables


def test_format_simple_table():
    """Test formatting a simple pipe-delimited table."""
    input_text = """Here are the results:

| Name | Age | City |
|------|-----|------|
| Alice | 30 | NYC |
| Bob | 25 | LA |

That's all the data."""
    
    result = format_response_tables(input_text)
    
    # Check that HTML table elements are present
    assert '<table' in result
    assert '<thead' in result
    assert '<tbody' in result
    assert '<th' in result
    assert '<td' in result
    assert 'Alice' in result
    assert 'Bob' in result
    assert 'NYC' in result
    assert 'LA' in result


def test_format_table_with_complex_headers():
    """Test formatting table with multi-word headers."""
    input_text = """| Asset ID | Type | Protocol | Mission-Criticality |
|----------|------|----------|---------------------|
| b591 | Database | HTTP | 3 |
| c892 | Server | HTTPS | 5 |"""
    
    result = format_response_tables(input_text)
    
    assert '<table' in result
    assert 'Asset ID' in result
    assert 'Mission-Criticality' in result
    assert 'b591' in result


def test_no_table_returns_original():
    """Test that text without tables is returned unchanged."""
    input_text = "This is just plain text without any tables."
    
    result = format_response_tables(input_text)
    
    assert result == input_text
    assert '<table' not in result


def test_empty_string():
    """Test handling of empty string."""
    result = format_response_tables("")
    assert result == ""


def test_none_input():
    """Test handling of None input."""
    result = format_response_tables(None)
    assert result is None


def test_table_with_long_content():
    """Test table with long cell content."""
    input_text = """| Column 1 | Column 2 |
|----------|----------|
| This is a very long piece of text that should wrap | Short |
| Another row | With more data |"""
    
    result = format_response_tables(input_text)
    
    assert '<table' in result
    assert 'max-width: 200px' in result  # Check word-wrap styling
    assert 'This is a very long piece of text' in result


def test_preserves_text_before_and_after_table():
    """Test that text before and after table is preserved."""
    input_text = """Introduction text here.

| Col1 | Col2 |
|------|------|
| A | B |

Conclusion text here."""
    
    result = format_response_tables(input_text)
    
    assert 'Introduction text here' in result
    assert 'Conclusion text here' in result
    assert '<table' in result


def test_alternating_row_colors():
    """Test that alternating row colors are applied."""
    input_text = """| Name | Value |
|------|-------|
| Row1 | Val1 |
| Row2 | Val2 |
| Row3 | Val3 |"""
    
    result = format_response_tables(input_text)
    
    # Check for alternating background colors
    assert '#f8f9fa' in result  # Even rows
    assert 'white' in result  # Odd rows


def test_table_styling():
    """Test that proper styling is applied to table."""
    input_text = """| Header |
|--------|
| Data |"""
    
    result = format_response_tables(input_text)
    
    # Check for key styling elements
    assert 'border-collapse: collapse' in result
    assert 'box-shadow' in result
    assert 'gradient' in result  # Header gradient
    assert 'overflow-x: auto' in result  # Scrollable container


if __name__ == "__main__":
    pytest.main([__file__, "-v"])