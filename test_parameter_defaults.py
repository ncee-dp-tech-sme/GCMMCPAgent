#!/usr/bin/env python3
"""
Test script to verify parameter defaults functionality.

Tests that the _add_parameter_defaults method correctly adds
pagination parameters (page_number, page_size) to tool calls.
"""

import sys
import asyncio
from gcm_agent.mcp.client import GCMMCPClient


def test_parameter_defaults():
    """Test parameter defaults for various tool call scenarios."""
    
    # Create a mock client (we only need the method, not a real connection)
    client = GCMMCPClient.__new__(GCMMCPClient)
    client.logger = type('obj', (object,), {
        'info': lambda self, msg: print(f"[INFO] {msg}"),
        'debug': lambda self, msg: print(f"[DEBUG] {msg}"),
        'error': lambda self, msg: print(f"[ERROR] {msg}"),
        'warning': lambda self, msg: print(f"[WARNING] {msg}")
    })()
    
    print("=" * 80)
    print("TEST 1: List tool with no pagination parameters")
    print("=" * 80)
    args1 = {"filters": {"asset_type": "key"}}
    result1 = client._add_parameter_defaults("fetch_detailed_asset_list_by_it_assets", args1)
    print(f"Input:  {args1}")
    print(f"Output: {result1}")
    assert result1.get("page_number") == 1, "Should add page_number=1"
    assert result1.get("page_size") == 50, "Should add page_size=50"
    print("✓ PASSED: Added pagination parameters at top level\n")
    
    print("=" * 80)
    print("TEST 2: List tool with nested body structure")
    print("=" * 80)
    args2 = {"body": {"filters": {"asset_type": "key"}}}
    result2 = client._add_parameter_defaults("fetch_asset_list", args2)
    print(f"Input:  {args2}")
    print(f"Output: {result2}")
    assert result2["body"].get("page_number") == 1, "Should add page_number=1 to body"
    assert result2["body"].get("page_size") == 50, "Should add page_size=50 to body"
    print("✓ PASSED: Added pagination parameters to nested body\n")
    
    print("=" * 80)
    print("TEST 3: List tool with existing pagination parameters")
    print("=" * 80)
    args3 = {"page_number": 2, "page_size": 100, "filters": {}}
    result3 = client._add_parameter_defaults("list_keys", args3)
    print(f"Input:  {args3}")
    print(f"Output: {result3}")
    assert result3.get("page_number") == 2, "Should preserve existing page_number"
    assert result3.get("page_size") == 100, "Should preserve existing page_size"
    print("✓ PASSED: Preserved existing pagination parameters\n")
    
    print("=" * 80)
    print("TEST 4: Non-list tool (should not add pagination)")
    print("=" * 80)
    args4 = {"key_id": "12345"}
    result4 = client._add_parameter_defaults("get_key_details", args4)
    print(f"Input:  {args4}")
    print(f"Output: {result4}")
    assert "page_number" not in result4, "Should not add pagination to non-list tools"
    assert "page_size" not in result4, "Should not add pagination to non-list tools"
    print("✓ PASSED: Did not add pagination to non-list tool\n")
    
    print("=" * 80)
    print("TEST 5: Fetch tool with params structure")
    print("=" * 80)
    args5 = {"params": {"filters": {"contains_classified_data": True}}}
    result5 = client._add_parameter_defaults("fetch_dashboard", args5)
    print(f"Input:  {args5}")
    print(f"Output: {result5}")
    assert result5["params"].get("page_number") == 1, "Should add page_number=1 to params"
    assert result5["params"].get("page_size") == 50, "Should add page_size=50 to params"
    print("✓ PASSED: Added pagination parameters to nested params\n")
    
    print("=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    print("\nThe parameter defaults functionality is working correctly.")
    print("The client will now automatically add pagination parameters when:")
    print("  - Tool name contains: list, fetch, get_all, search, query, dashboard")
    print("  - Parameters are missing: page_number, page_size")
    print("  - Defaults: page_number=1, page_size=50")
    
    return True


if __name__ == "__main__":
    try:
        success = test_parameter_defaults()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
