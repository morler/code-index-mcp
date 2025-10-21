#!/usr/bin/env python3

"""Debug file lock acquisition."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_file_lock():
    """Debug file lock acquisition."""
    try:
        from core.file_lock import acquire_file_lock, release_file_lock, WIN32_AVAILABLE

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        test_file.write_text("test content", encoding="utf-8")

        print(f"WIN32_AVAILABLE: {WIN32_AVAILABLE}")
        print(f"Platform: {sys.platform}")

        try:
            print("Attempting to acquire file lock...")
            start = time.perf_counter()

            lock = acquire_file_lock(test_file, lock_type="exclusive", timeout=5.0)

            lock_time = time.perf_counter() - start
            print(f"Lock acquired in {lock_time:.3f}s")

            # Release lock
            print("Releasing lock...")
            release_file_lock(test_file)
            print("Lock released")

        except Exception as e:
            print(f"Lock acquisition failed: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if test_file.exists():
                test_file.unlink()
            # Clean up lock file if it exists
            lock_file = test_file.with_suffix(test_file.suffix + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_file_lock()
