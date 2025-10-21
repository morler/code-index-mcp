#!/usr/bin/env python3

"""Debug each step of edit_file_atomic to find the bottleneck."""

import sys
import tempfile
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def debug_edit_steps():
    """Debug each step of the edit process."""
    try:
        from core.edit_operations import get_memory_edit_operations
        from core.memory_monitor import check_memory_limits

        # Create test file
        test_file = Path(tempfile.mktemp(suffix=".txt"))
        original_content = "x" * 1024  # 1KB
        new_content = original_content + "\n# Modified"

        try:
            test_file.write_text(original_content, encoding="utf-8")
            print(f"Created test file: {test_file}")

            # Step 1: Check memory limits
            print("Step 1: Checking memory limits...")
            start = time.perf_counter()
            memory_ok, memory_error = check_memory_limits("edit_operation")
            step1_time = time.perf_counter() - start
            print(
                f"   Memory check took {step1_time:.3f}s: {memory_ok}, {memory_error}"
            )

            # Step 2: Get edit operations instance
            print("Step 2: Getting edit operations instance...")
            start = time.perf_counter()
            edit_ops = get_memory_edit_operations()
            step2_time = time.perf_counter() - start
            print(f"   Instance creation took {step2_time:.3f}s")

            # Step 3: Validate file path
            print("Step 3: Validating file path...")
            start = time.perf_counter()
            file_path_obj = Path(test_file)
            exists = file_path_obj.exists()
            step3_time = time.perf_counter() - start
            print(f"   Path validation took {step3_time:.3f}s: exists={exists}")

            # Step 4: Read current content
            print("Step 4: Reading current content...")
            start = time.perf_counter()
            current_content = file_path_obj.read_text(encoding="utf-8")
            step4_time = time.perf_counter() - start
            print(f"   File read took {step4_time:.3f}s: {len(current_content)} chars")

            # Step 5: Content validation
            print("Step 5: Content validation...")
            start = time.perf_counter()
            old_stripped = original_content.strip()
            current_stripped = current_content.strip()
            if old_stripped == current_stripped:
                validated_new_content = new_content
            step5_time = time.perf_counter() - start
            print(f"   Content validation took {step5_time:.3f}s")

            # Step 6: Apply edit with backup
            print("Step 6: Applying edit with backup...")
            start = time.perf_counter()
            from core.backup import apply_edit_with_backup

            success, error = apply_edit_with_backup(
                str(test_file),
                validated_new_content,
                original_content
                if original_content and original_content.strip()
                else None,
            )
            step6_time = time.perf_counter() - start
            print(
                f"   Edit with backup took {step6_time:.3f}s: success={success}, error={error}"
            )

            total_time = (
                step1_time
                + step2_time
                + step3_time
                + step4_time
                + step5_time
                + step6_time
            )
            print(f"\nTotal time: {total_time:.3f}s")
            print(
                f"Bottleneck: Step 6 took {step6_time / total_time * 100:.1f}% of total time"
            )

        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_edit_steps()
