# Table Formatting Feature

## Overview

The GCM Agent now automatically detects and formats tabular data in responses for improved readability. When the agent returns data in pipe-delimited table format (markdown tables), it is automatically converted to styled HTML tables.

## Implementation Date
2026-06-09 21:22 UTC

## Problem Solved

Previously, when the agent returned tabular data (e.g., lists of keys, assets, or policy violations), the tables were displayed as plain text with poor readability:
- Vertically oriented column headers
- Cramped text difficult to scan
- No visual hierarchy or grouping
- Poor spacing and alignment

## Solution

### Automatic Table Detection
The system automatically detects pipe-delimited markdown tables in agent responses:
```
| Column1 | Column2 | Column3 |
|---------|---------|---------|
| Value1  | Value2  | Value3  |
```

### HTML Table Formatting
Detected tables are converted to styled HTML tables with:
- **Professional styling**: Gradient header background (purple gradient)
- **Improved readability**: Proper padding, borders, and spacing
- **Alternating row colors**: White and light gray for easy scanning
- **Responsive design**: Horizontal scrolling for wide tables
- **Word wrapping**: Long content wraps within cells (max 200px width)
- **Box shadow**: Subtle shadow for depth

## Technical Details

### Files Modified

1. **`gcm_agent/utils/table_formatter.py`** (NEW)
   - Core table detection and formatting logic
   - Functions:
     - `format_response_tables()`: Main entry point
     - `_detect_table_structure()`: Detects pipe-delimited tables
     - `_parse_table_row()`: Parses table rows into cells
     - `_format_as_html_table()`: Converts to styled HTML

2. **`gcm_agent/ui/chat_ui.py`** (MODIFIED)
   - Integrated table formatter into chat response streaming
   - Added `format_response_tables()` import
   - Applied formatting to accumulated response chunks
   - Updated chatbot component to enable HTML rendering

3. **`gcm_agent/utils/__init__.py`** (MODIFIED)
   - Exported `format_response_tables` for easy access

### Styling Details

**Header Styling:**
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
color: white;
padding: 12px 8px;
font-weight: 600;
```

**Row Styling:**
- Even rows: `#f8f9fa` (light gray)
- Odd rows: `white`
- Border: `1px solid #e9ecef`
- Padding: `10px 8px`

**Table Container:**
- Overflow: `auto` (horizontal scrolling)
- Box shadow: `0 1px 3px rgba(0,0,0,0.1)`
- Margin: `10px 0`

## Usage

The feature works automatically - no configuration needed. When the agent returns tabular data:

**Before (Plain Text):**
```
| Name | Age | City |
|------|-----|------|
| Alice | 30 | NYC |
| Bob | 25 | LA |
```

**After (Styled HTML Table):**
Renders as a professional-looking table with:
- Purple gradient header
- Alternating row colors
- Proper spacing and alignment
- Responsive scrolling

## Testing

Test suite: `tests/test_table_formatter.py`

Tests cover:
- Simple table formatting
- Complex multi-word headers
- Long cell content with word wrapping
- Text preservation before/after tables
- Alternating row colors
- Empty/None input handling
- Non-table text (returns unchanged)

## Performance Impact

- **Minimal overhead**: Table detection is O(n) where n = number of lines
- **Streaming compatible**: Formatting applied to accumulated chunks
- **No blocking**: Formatting happens synchronously but is fast (<1ms for typical tables)

## Browser Compatibility

HTML tables render in all modern browsers. Gradio's chatbot component supports HTML rendering when configured with:
```python
chatbot = gr.Chatbot(
    type="messages",
    render_markdown=True,
)
```

## Future Enhancements

Potential improvements:
1. Support for CSV-style tables (comma-separated)
2. Sortable columns (JavaScript-based)
3. Column width auto-adjustment
4. Export table to CSV/Excel
5. Custom color themes
6. Column filtering/search

## Related Files

- Implementation: `gcm_agent/utils/table_formatter.py`
- Integration: `gcm_agent/ui/chat_ui.py`
- Tests: `tests/test_table_formatter.py`
- Documentation: `docs/TABLE_FORMATTING.md` (this file)