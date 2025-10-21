#!/usr/bin/env python3

"""Debug apply_edit function to identify the issue."""

import sys
import tempfile
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def test_apply_edit():
    """Test apply_edit function directly."""
    try:
        from code_index_mcp.server_unified import apply_edit

        print("✓ Successfully imported apply_edit from server_unified")

        # Test if MCP is available
        result = apply_edit("/tmp/test", "test", "test")
        if result.get("error") == "MCP not available":
            print("⚠ MCP not available, using direct edit operations test")
            return test_direct_edit_operations()

    except ImportError as e:
        print(f"✗ Failed to import apply_edit: {e}")
        return False

    # Create test file
    test_file = Path(tempfile.mktemp(suffix=".txt"))
    original_content = "Hello World"
    new_content = "Hello World\nModified"

    try:
        # Write original content
        test_file.write_text(original_content, encoding="utf-8")
        print(f"✓ Created test file: {test_file}")

        # Test apply_edit
        print(f"Testing apply_edit with:")
        print(f"  file_path: {test_file}")
        print(f"  old_content: {repr(original_content)}")
        print(f"  new_content: {repr(new_content)}")

        result = apply_edit(str(test_file), original_content, new_content)
        print(f"Result: {result}")

        # Check if file was modified
        if test_file.exists():
            actual_content = test_file.read_text(encoding="utf-8")
            print(f"Actual file content: {repr(actual_content)}")

            if actual_content == new_content:
                print("✓ File was successfully modified")
                return True
            else:
                print("✗ File content doesn't match expected")
                return False
        else:
            print("✗ Test file no longer exists")
            return False

    except Exception as e:
        print(f"✗ Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
            print(f"✓ Cleaned up test file")


def test_direct_edit_operations():
    """Test direct edit operations without MCP."""
    try:
        # Import the core edit operations directly
        from core.edit_operations import get_memory_edit_operations

        print("✓ Successfully imported get_memory_edit_operations")

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "Hello World"
        new_content = "Hello World\nModified"

        try:
            # Write original content
            test_file.write_text(original_content, encoding="utf-8")
            print(f"✓ Created test file: {test_file}")

            # Test edit operations
            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), original_content, new_content
            )

            print(f"Edit result: success={success}, error={error}")

            # Check if file was modified
            if test_file.exists():
                actual_content = test_file.read_text(encoding="utf-8")
                print(f"Actual file content: {repr(actual_content)}")

                if actual_content == new_content:
                    print("✓ File was successfully modified")
                    return True
                else:
                    print("✗ File content doesn't match expected")
                    return False
            else:
                print("✗ Test file no longer exists")
                return False

        except Exception as e:
            print(f"✗ Exception during edit test: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
                print(f"✓ Cleaned up test file")

    except ImportError as e:
        print(f"✗ Failed to import edit operations: {e}")
        import traceback

        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Exception in direct edit test: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_apply_edit()
    print(f"\nTest result: {'PASS' if success else 'FAIL'}")
