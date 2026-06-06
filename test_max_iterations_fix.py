#!/usr/bin/env python3
"""
Test script to verify the max_iterations fix for broad queries.

This script validates that the configuration defaults have been updated
to handle broad queries like "all keys" or "all assets" without hitting
the recursion limit.

Run: python test_max_iterations_fix.py
"""

# Made with Bob
# 2026-06-06 04:27 UTC - Added test script to validate max_iterations and discovery_mode defaults and provide manual test guidance

from gcm_agent.config.config_manager import AgentConfig


# Validate the default AgentConfig values for the broad query fix.
def validate_configuration_defaults() -> None:
    """Validate the updated AgentConfig defaults."""
    config = AgentConfig()

    assert config.max_iterations == 20, (
        f"Expected max_iterations=20, got {config.max_iterations}"
    )
    print("[PASS] max_iterations default is 20")

    assert config.discovery_mode is False, (
        f"Expected discovery_mode=False, got {config.discovery_mode}"
    )
    print("[PASS] discovery_mode default is False")


# Print manual test guidance for validating broad query behavior with the agent.
def print_manual_test_guidance() -> None:
    """Print manual test guidance."""
    print("\nManual testing guidance:")
    print("- Actual GCM connection is required for full end-to-end validation.")
    print("- Success means the agent returns actual data, not a 'need more steps' response.")
    print("- Suggested broad queries to test:")
    print('  1. "show me all keys"')
    print('  2. "list all assets"')
    print('  3. "get all key groups"')

    print("\nTest mode 1: discovery_mode=False (default)")
    print("- Use the default AgentConfig settings.")
    print("- Confirm discovery_mode is False and max_iterations is 20.")
    print("- Run the agent with one of the suggested broad queries.")
    print("- Expected result: actual keys/assets/key groups are returned without recursion limit issues.")

    print("\nTest mode 2: discovery_mode=True")
    print("- Override AgentConfig with discovery_mode=True while keeping max_iterations=20.")
    print("- Run the same broad queries again.")
    print("- Expected result: discovery mode should still complete successfully within 20 iterations.")

    print("\nExample validation scenarios:")
    print("- Default mode: AgentConfig()")
    print("- Discovery mode: AgentConfig(discovery_mode=True, max_iterations=20)")


# Run the configuration validation and print manual test instructions.
def main() -> None:
    """Run the test script."""
    print("Verifying max_iterations fix configuration defaults...\n")
    validate_configuration_defaults()
    print_manual_test_guidance()
    print("\nConfiguration validation completed successfully.")


if __name__ == "__main__":
    main()