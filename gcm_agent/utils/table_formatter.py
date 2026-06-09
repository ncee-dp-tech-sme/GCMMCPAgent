"""Table formatting utilities for improving data presentation in chat responses."""

# Made with Bob
# 2026-06-09 21:22 UTC - Initial implementation of table detection and HTML formatting
# 2026-06-09 21:37 UTC - Switched from HTML to enhanced markdown for Gradio compatibility

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


def _format_as_enhanced_markdown(text: str, header_idx: int, separator_idx: int) -> str:
    """
    Convert pipe-delimited table to enhanced markdown with better formatting.
    
    Args:
        text: Original text containing table
        header_idx: Index of header row
        separator_idx: Index of separator row
        
    Returns:
        Enhanced markdown formatted table
    """
    lines = text.split('\n')
    
    # Extract table lines (header + data rows)
    header_line = lines[header_idx]
    separator_line = lines[separator_idx]
    data_lines = []
    
    # Collect all data rows after separator
    for i in range(separator_idx + 1, len(lines)):
        if '|' in lines[i] and lines[i].strip():
            data_lines.append(lines[i])
        else:
            break  # Stop at first non-table line
    
    # Parse header and calculate column widths
    headers = _parse_table_row(header_line)
    col_widths = [len(h) for h in headers]
    
    # Update column widths based on data
    for data_line in data_lines:
        cells = _parse_table_row(data_line)
        for i, cell in enumerate(cells):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))
    
    # Add padding to widths
    col_widths = [w + 2 for w in col_widths]
    
    # Build formatted table
    formatted_lines = []
    
    # Add header with proper spacing
    header_cells = [h.center(col_widths[i]) for i, h in enumerate(headers)]
    formatted_lines.append('| ' + ' | '.join(header_cells) + ' |')
    
    # Add separator with proper width
    separator_cells = ['-' * w for w in col_widths]
    formatted_lines.append('|' + '|'.join(separator_cells) + '|')
    
    # Add data rows with proper spacing
    for data_line in data_lines:
        cells = _parse_table_row(data_line)
        # Pad cells to match header count
        while len(cells) < len(headers):
            cells.append('')
        formatted_cells = [cells[i].ljust(col_widths[i]) if i < len(cells) else ''.ljust(col_widths[i])
                          for i in range(len(headers))]
        formatted_lines.append('| ' + ' | '.join(formatted_cells) + ' |')
    
    return '\n'.join(formatted_lines)


def format_response_tables(text: str) -> str:
    """
    Detect and format tables in response text.
    
    Args:
        text: Response text that may contain tables
        
    Returns:
        Text with tables formatted as enhanced markdown
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
    
    # Format table as enhanced markdown
    formatted_table = _format_as_enhanced_markdown(table_lines, 0, 1)
    
    # Combine parts
    result_parts = []
    if before_table.strip():
        result_parts.append(before_table.strip())
    result_parts.append(formatted_table)
    if after_table.strip():
        result_parts.append(after_table.strip())
    
    return '\n\n'.join(result_parts)


__all__ = ['format_response_tables']