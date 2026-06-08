"""
Test script for UI implementation

Quick verification that all UI components can be imported and initialized.
"""

# Made with Bob
# 2026-06-05 22:17 UTC - Test script for UI verification

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all UI modules can be imported."""
    print("Testing imports...")
    
    try:
        from gcm_agent.ui import create_config_ui, create_chat_ui
        print("✅ UI module imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_ui_creation():
    """Test that UI components can be created."""
    print("\nTesting UI creation...")
    
    try:
        from gcm_agent.ui import create_config_ui, create_chat_ui
        
        # Test config UI creation
        print("  Creating config UI...")
        config_ui = create_config_ui()
        print("  ✅ Config UI created")
        
        # Test chat UI creation
        print("  Creating chat UI...")
        chat_ui = create_chat_ui()
        print("  ✅ Chat UI created")
        
        return True
    except Exception as e:
        print(f"  ❌ UI creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """Test that main app can be created."""
    print("\nTesting app creation...")
    
    try:
        from app import create_app
        
        print("  Creating main app...")
        app = create_app()
        print("  ✅ Main app created")
        
        return True
    except Exception as e:
        print(f"  ❌ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("GCM Agent UI Implementation Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("UI Creation", test_ui_creation()))
    results.append(("App Creation", test_app_creation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
        print("\nTo run the application:")
        print("  python app.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())