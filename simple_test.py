#!/usr/bin/env python3

"""Simple test of apply_edit functionality."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def test_simple_edit():
    """Test simple edit operation."""
    try:
        from core.edit_operations import get_memory_edit_operations

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        new_content = original_content + "\n# Modified"

        try:
            # Write original content
            test_file.write_text(original_content, encoding="utf-8")

            # Measure edit operation
            start_time = time.perf_counter()

            edit_ops = get_memory_edit_operations()
            success, error = edit_ops.edit_file_atomic(
                str(test_file), original_content, new_content
            )

            duration = time.perf_counter() - start_time

            if success:
                actual_content = test_file.read_text(encoding="utf-8")
                if actual_content == new_content:
                    print(f"✓ Edit successful in {duration:.3f}s")
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
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_edit()
    print(f"Result: {'PASS' if success else 'FAIL'}")
