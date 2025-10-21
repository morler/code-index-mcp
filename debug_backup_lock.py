#!/usr/bin/env python3

"""Debug backup file lock acquisition."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_backup_lock():
    """Debug backup file lock acquisition in context."""
    try:
        from core.file_lock import acquire_file_lock, release_file_lock
        from core.backup import BackupSystem

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        test_file.write_text(original_content, encoding="utf-8")

        try:
            print("Testing lock acquisition with same parameters as backup...")

            # Test with same timeout as backup system
            lock_timeout_seconds = 30  # This is what BackupSystem uses

            start = time.perf_counter()
            lock = acquire_file_lock(
                test_file, lock_type="exclusive", timeout=lock_timeout_seconds
            )
            lock_time = time.perf_counter() - start

            print(f"Lock acquired in {lock_time:.3f}s")

            # Simulate what backup does
            print("Simulating backup operations...")

            # Read file content (like backup does)
            start = time.perf_counter()
            content = test_file.read_text(encoding="utf-8")
            read_time = time.perf_counter() - start
            print(f"File read took {read_time:.3f}s")

            # Create FileState (like backup does)
            start = time.perf_counter()
            from core.edit_models import FileState

            file_state = FileState.from_file(test_file)
            state_time = time.perf_counter() - start
            print(f"FileState creation took {state_time:.3f}s")

            # Release lock
            release_file_lock(test_file)
            print("Lock released")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if test_file.exists():
                test_file.unlink()
            lock_file = test_file.with_suffix(test_file.suffix + ".lock")
            if lock_file.exists():
                lock_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_backup_lock()
