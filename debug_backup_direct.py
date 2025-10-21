#!/usr/bin/env python3

"""Debug backup_file method directly."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_backup_direct():
    """Debug backup_file method directly."""
    try:
        from core.backup import get_backup_system

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        test_file.write_text(original_content, encoding="utf-8")

        try:
            system = get_backup_system()

            # Patch the backup_file method to add timing
            original_backup_file = system.backup_file

            def timed_backup_file(file_path):
                print("backup_file called...")
                start = time.perf_counter()
                result = original_backup_file(file_path)
                end = time.perf_counter()
                print(f"backup_file completed in {end - start:.3f}s")
                return result

            system.backup_file = timed_backup_file

            print("Calling backup_file...")
            start = time.perf_counter()
            operation_id = system.backup_file(str(test_file))
            end = time.perf_counter()
            print(f"Total call took {end - start:.3f}s")
            print(f"Operation ID: {operation_id}")

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
    debug_backup_direct()
