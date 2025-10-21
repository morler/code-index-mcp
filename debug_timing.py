#!/usr/bin/env python3

"""Debug timing issues in edit operations."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_timing():
    """Debug where time is spent in edit operations."""
    try:
        print("1. Importing edit operations...")
        import_start = time.perf_counter()
        from core.edit_operations import get_memory_edit_operations

        import_time = time.perf_counter() - import_start
        print(f"   Import took {import_time:.3f}s")

        print("2. Creating test file...")
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        new_content = original_content + "\n# Modified"

        file_start = time.perf_counter()
        test_file.write_text(original_content, encoding="utf-8")
        file_time = time.perf_counter() - file_start
        print(f"   File creation took {file_time:.3f}s")

        print("3. Getting edit operations instance...")
        ops_start = time.perf_counter()
        edit_ops = get_memory_edit_operations()
        ops_time = time.perf_counter() - ops_start
        print(f"   Getting instance took {ops_time:.3f}s")

        print("4. Performing edit...")
        edit_start = time.perf_counter()
        success, error = edit_ops.edit_file_atomic(
            str(test_file), original_content, new_content
        )
        edit_time = time.perf_counter() - edit_start
        print(f"   Edit operation took {edit_time:.3f}s")

        if success:
            print("✓ Edit successful")
        else:
            print(f"✗ Edit failed: {error}")

        # Cleanup
        if test_file.exists():
            test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_timing()
