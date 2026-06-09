"""Table formatting utilities for improving data presentation in chat responses."""

# Made with Bob
# 2026-06-09 21:22 UTC - Initial implementation of table detection and HTML formatting
# 2026-06-09 21:37 UTC - Switched from HTML to enhanced markdown for Gradio compatibility
# 2026-06-09 21:55 UTC - Reverted to HTML with light theme styling for better readability in dark mode

import re
from typing import Optional, List, Tuple


def _detect_table_structure(text: str) -> Optional[Tuple[int, int]]:
    """
    Detect if text contains a table structure.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (header_line_index, separator_line_index) if table detected, None otherwise
    """
    lines = text.split('\n')
    
    # Look for pipe-delimited tables (markdown style)
    for i, line in enumerate(lines):
        if '|' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            # Check if next line is a separator (contains dashes and pipes)
            if '|' in next_line and '-' in next_line:
                return (i, i + 1)
    
    return None


def _parse_table_row(row: str) -> List[str]:
    """
    Parse a pipe-delimited table row into cells.
    
    Args:
        row: Table row string
        
    Returns:
        List of cell contents
    """
    # Remove leading/trailing pipes and split
    cells = [cell.strip() for cell in row.strip('|').split('|')]
    return cells


def _format_as_html_table(text: str, header_idx: int, separator_idx: int) -> str:
    """
    Convert pipe-delimited table to styled HTML table with light theme.
    
    Args:
        text: Original text containing table
        header_idx: Index of header row
        separator_idx: Index of separator row
        
    Returns:
        HTML formatted table with inline styles
    """
    lines = text.split('\n')
    
    # Extract table lines
    header_line = lines[header_idx]
    data_lines = []
    
    # Collect all data rows after separator
    for i in range(separator_idx + 1, len(lines)):
        if '|' in lines[i] and lines[i].strip():
            data_lines.append(lines[i])
        else:
            break
    
    # Parse header and data
    headers = _parse_table_row(header_line)
    
    # Build HTML table with light theme styling
    html_parts = [
        '<div style="overflow-x: auto; margin: 10px 0; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">',
        '<table style="width: 100%; border-collapse: collapse; background: white; color: #1a1a1a;">',
        '<thead>',
        '<tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">'
    ]
    
    # Add headers
    for header in headers:
        html_parts.append(
            f'<th style="padding: 12px 8px; text-align: left; font-weight: 600; '
            f'color: white; border-bottom: 2px solid #5a67d8;">{header}</th>'
        )
    
    html_parts.append('</tr>')
    html_parts.append('</thead>')
    html_parts.append('<tbody>')
    
    # Add data rows
    for idx, data_line in enumerate(data_lines):
        cells = _parse_table_row(data_line)
        row_bg = '#f8f9fa' if idx % 2 == 0 else 'white'
        html_parts.append(f'<tr style="background: {row_bg};">')
        
        for cell in cells:
            html_parts.append(
                f'<td style="padding: 10px 8px; border-bottom: 1px solid #e9ecef; '
                f'color: #1a1a1a; max-width: 200px; word-wrap: break-word;">{cell}</td>'
            )
        
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)


def format_response_tables(text: str) -> str:
    """
    Detect and format tables in response text.
    
    Args:
        text: Response text that may contain tables
        
    Returns:
        Text with tables formatted as styled HTML
    """
    if not text or '|' not in text:
        return text
    
    # Detect table structure
    table_info = _detect_table_structure(text)
    if not table_info:
        return text
    
    header_idx, separator_idx = table_info
    lines = text.split('\n')
    
    # Find where table ends
    table_end_idx = separator_idx + 1
    for i in range(separator_idx + 1, len(lines)):
        if '|' in lines[i] and lines[i].strip():
            table_end_idx = i + 1
        else:
            break
    
    # Split text into before table, table, and after table
    before_table = '\n'.join(lines[:header_idx])
    table_lines = '\n'.join(lines[header_idx:table_end_idx])
    after_table = '\n'.join(lines[table_end_idx:])
    
    # Format table as HTML
    formatted_table = _format_as_html_table(table_lines, 0, 1)
    
    # Combine parts
    result_parts = []
    if before_table.strip():
        result_parts.append(before_table.strip())
    result_parts.append(formatted_table)
    if after_table.strip():
        result_parts.append(after_table.strip())
    
    return '\n\n'.join(result_parts)


__all__ = ['format_response_tables']