#!/usr/bin/env python3

"""Comprehensive test of apply_edit functionality."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def test_apply_edit_basic():
    """Test basic apply_edit functionality."""
    print("Testing basic apply_edit...")

    try:
        from core.edit_operations import get_memory_edit_operations

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "Hello World"
        new_content = "Hello World\nModified"

        try:
            test_file.write_text(original_content, encoding="utf-8")

            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), original_content, new_content
            )

            if success:
                actual_content = test_file.read_text(encoding="utf-8")
                if actual_content == new_content:
                    print("✓ Basic edit successful")
                    return True
                else:
                    print("✗ Content mismatch")
                    return False
            else:
                print(f"✗ Edit failed: {error}")
                return False

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_apply_edit_with_backup():
    """Test apply_edit with backup functionality."""
    print("Testing apply_edit with backup...")

    try:
        from core.backup import apply_edit_with_backup

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nLine 2 Modified\nLine 3"

        try:
            test_file.write_text(original_content, encoding="utf-8")

            success, error = apply_edit_with_backup(
                str(test_file), new_content, original_content
            )

            if success:
                actual_content = test_file.read_text(encoding="utf-8")
                if actual_content == new_content:
                    print("✓ Edit with backup successful")
                    return True
                else:
                    print("✗ Content mismatch")
                    return False
            else:
                print(f"✗ Edit with backup failed: {error}")
                return False

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_apply_edit_mismatch():
    """Test apply_edit with content mismatch."""
    print("Testing apply_edit with content mismatch...")

    try:
        from core.edit_operations import get_memory_edit_operations

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        actual_content = "Actual Content"
        wrong_old_content = "Wrong Content"
        new_content = "New Content"

        try:
            test_file.write_text(actual_content, encoding="utf-8")

            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), wrong_old_content, new_content
            )

            if not success and error and "mismatch" in error.lower():
                print("✓ Content mismatch correctly detected")
                return True
            else:
                print(f"✗ Should have failed with mismatch error: {error}")
                return False

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_apply_edit_large_file():
    """Test apply_edit with large file."""
    print("Testing apply_edit with large file...")

    try:
        from core.edit_operations import get_memory_edit_operations

        # Create test file with larger content
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "Line " + "x" * 1000 + "\n" * 100  # ~100KB
        new_content = original_content + "\n# Added at end"

        try:
            test_file.write_text(original_content, encoding="utf-8")

            start = time.perf_counter()
            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), original_content, new_content
            )
            duration = time.perf_counter() - start

            if success:
                actual_content = test_file.read_text(encoding="utf-8")
                if actual_content == new_content:
                    print(f"✓ Large file edit successful in {duration:.3f}s")
                    return True
                else:
                    print("✗ Content mismatch")
                    return False
            else:
                print(f"✗ Large file edit failed: {error}")
                return False

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def test_apply_edit_unicode():
    """Test apply_edit with Unicode content."""
    print("Testing apply_edit with Unicode content...")

    try:
        from core.edit_operations import get_memory_edit_operations

        # Create test file with Unicode content
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "Hello 世界 🌍\n中文测试\nEmoji: 🚀🎉"
        new_content = original_content + "\nModified: 修改后 ✨"

        try:
            test_file.write_text(original_content, encoding="utf-8")

            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), original_content, new_content
            )

            if success:
                actual_content = test_file.read_text(encoding="utf-8")
                if actual_content == new_content:
                    print("✓ Unicode edit successful")
                    return True
                else:
                    print("✗ Unicode content mismatch")
                    return False
            else:
                print(f"✗ Unicode edit failed: {error}")
                return False

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        return False


def main():
    """Run all tests."""
    print("=== Comprehensive Apply Edit Test ===\n")

    tests = [
        test_apply_edit_basic,
        test_apply_edit_with_backup,
        test_apply_edit_mismatch,
        test_apply_edit_large_file,
        test_apply_edit_unicode,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"=== Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("✓ All apply_edit tests PASSED")
        return True
    else:
        print("✗ Some apply_edit tests FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
