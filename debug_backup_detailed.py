#!/usr/bin/env python3

"""Debug backup_file method with detailed timing."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_backup_detailed():
    """Debug backup_file method with detailed timing."""
    try:
        from core.backup import get_backup_system

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        test_file.write_text(original_content, encoding="utf-8")

        try:
            system = get_backup_system()
            print(f"Lock timeout: {system.lock_timeout_seconds}s")

            # Manually implement backup_file steps with timing
            file_path = Path(test_file)

            print("Step 1: Validate file exists...")
            start = time.perf_counter()
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            step1 = time.perf_counter() - start
            print(f"   Took {step1:.3f}s")

            print("Step 2: Check file size...")
            start = time.perf_counter()
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > system.max_file_size_mb:
                raise Exception(f"File too large: {file_size_mb:.1f}MB")
            step2 = time.perf_counter() - start
            print(f"   Took {step2:.3f}s")

            print("Step 3: Acquire file lock...")
            start = time.perf_counter()
            from core.file_lock import acquire_file_lock, release_file_lock

            file_lock = acquire_file_lock(
                file_path, lock_type="exclusive", timeout=system.lock_timeout_seconds
            )
            step3 = time.perf_counter() - start
            print(f"   Took {step3:.3f}s")

            try:
                print("Step 4: Create file state...")
                start = time.perf_counter()
                from core.edit_models import FileState, EditOperation, EditStatus

                file_state = FileState.from_file(file_path)
                step4 = time.perf_counter() - start
                print(f"   Took {step4:.3f}s")

                print("Step 5: Read file content...")
                start = time.perf_counter()
                original_content = file_path.read_text(encoding="utf-8")
                step5 = time.perf_counter() - start
                print(f"   Took {step5:.3f}s")

                print("Step 6: Create edit operation...")
                start = time.perf_counter()
                operation = EditOperation(file_path=str(file_path.absolute()))
                operation.set_original_content(original_content)
                operation.file_state = file_state
                operation.set_status(EditStatus.IN_PROGRESS)
                step6 = time.perf_counter() - start
                print(f"   Took {step6:.3f}s")

                print("Step 7: Add to memory manager...")
                start = time.perf_counter()
                if not system.memory_manager.add_backup(operation):
                    raise Exception("Memory limit exceeded")
                step7 = time.perf_counter() - start
                print(f"   Took {step7:.3f}s")

                print("Step 8: Record memory operation...")
                start = time.perf_counter()
                system.memory_monitor.record_operation(
                    operation.memory_size / (1024 * 1024), "backup_creation"
                )
                step8 = time.perf_counter() - start
                print(f"   Took {step8:.3f}s")

                operation.set_status(EditStatus.COMPLETED)
                print(f"Operation ID: {operation.operation_id}")

            finally:
                print("Step 9: Release file lock...")
                start = time.perf_counter()
                release_file_lock(file_path)
                step9 = time.perf_counter() - start
                print(f"   Took {step9:.3f}s")

            total_time = (
                step1 + step2 + step3 + step4 + step5 + step6 + step7 + step8 + step9
            )
            print(f"\nTotal time: {total_time:.3f}s")

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
    debug_backup_detailed()
