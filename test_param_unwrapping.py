#!/usr/bin/env python3
"""Test script to verify parameter unwrapping logic."""

import sys
from typing import Dict, Any


def unwrap_params(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unwrap nested params structure from LangChain MCP adapter.
    
    The LangChain MCP adapter wraps tool parameters in a nested 'params'
    structure: {"params": {"arg1": val1, "arg2": val2}}
    But the GCM MCP server expects flat parameters: {"arg1": val1, "arg2": val2}
    
    This method detects and unwraps the nested structure while preserving
    flat structures that don't need unwrapping.
    
    Args:
        arguments: Tool arguments (may be wrapped or flat)
    
    Returns:
        Unwrapped arguments dictionary
    """
    # Check if arguments contain a nested 'params' dict
    if isinstance(arguments, dict) and "params" in arguments and len(arguments) == 1:
        # Extract the contents of 'params'
        unwrapped = arguments["params"]
        if isinstance(unwrapped, dict):
            print(f"✓ Unwrapped nested params structure: {list(unwrapped.keys())}")
            return unwrapped
    
    # Return original structure if no unwrapping needed
    print(f"✓ No unwrapping needed, returning original structure")
    return arguments


def test_unwrap_params():
    """Test the parameter unwrapping logic."""
    print("Testing parameter unwrapping logic...\n")
    
    # Test 1: Nested params structure (should unwrap)
    print("Test 1: Nested params structure")
    nested = {"params": {"asset_category": "key", "page_number": 1, "page_size": 20}}
    result = unwrap_params(nested)
    expected = {"asset_category": "key", "page_number": 1, "page_size": 20}
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"Input:  {nested}")
    print(f"Output: {result}")
    print("✓ PASSED\n")
    
    # Test 2: Flat structure (should not unwrap)
    print("Test 2: Flat structure")
    flat = {"asset_category": "key", "page_number": 1, "page_size": 20}
    result = unwrap_params(flat)
    expected = {"asset_category": "key", "page_number": 1, "page_size": 20}
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"Input:  {flat}")
    print(f"Output: {result}")
    print("✓ PASSED\n")
    
    # Test 3: Params with additional keys (should not unwrap)
    print("Test 3: Params with additional keys")
    mixed = {"params": {"arg1": "val1"}, "other_key": "val2"}
    result = unwrap_params(mixed)
    expected = {"params": {"arg1": "val1"}, "other_key": "val2"}
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"Input:  {mixed}")
    print(f"Output: {result}")
    print("✓ PASSED\n")
    
    # Test 4: Empty params (should unwrap to empty dict)
    print("Test 4: Empty params")
    empty = {"params": {}}
    result = unwrap_params(empty)
    expected = {}
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"Input:  {empty}")
    print(f"Output: {result}")
    print("✓ PASSED\n")
    
    # Test 5: Non-dict params value (should not unwrap)
    print("Test 5: Non-dict params value")
    non_dict = {"params": "string_value"}
    result = unwrap_params(non_dict)
    expected = {"params": "string_value"}
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"Input:  {non_dict}")
    print(f"Output: {result}")
    print("✓ PASSED\n")
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_unwrap_params()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)

# Made with Bob
