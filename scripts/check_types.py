#!/usr/bin/env python3
"""
Type checking script using MyPy.

Runs MyPy type checking and tracks error count to prevent regressions.
Current baseline: 56 errors (as of 2025-09-18)
Target: 0 errors

Usage:
  python scripts/check_types.py          # Normal check
  python scripts/check_types.py --fast   # Fast check (error count only)
  python scripts/check_types.py --fix-baseline  # Update baseline to current count
"""

import subprocess
import sys
import re
import argparse
from pathlib import Path


def run_mypy() -> tuple[int, str]:
    """Run MyPy and return error count and output."""
    try:
        result = subprocess.run(
            ["uv", "run", "mypy", "src/"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=Path(__file__).parent.parent
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        output = stdout + stderr

        # Parse error count from MyPy output
        error_match = re.search(r"Found (\d+) errors? in", output)
        error_count = int(error_match.group(1)) if error_match else 0

        return error_count, output
    except Exception as e:
        print(f"Error running MyPy: {e}")
        return -1, str(e)


def update_baseline_in_script(new_baseline: int):
    """Update the baseline value in this script file."""
    script_path = Path(__file__)
    content = script_path.read_text(encoding='utf-8')

    # Update the baseline value
    pattern = r'BASELINE_ERRORS = \d+  # Current baseline \(updated [^)]+\)'
    replacement = f'BASELINE_ERRORS = {new_baseline}  # Current baseline (updated 2025-09-18)'

    updated_content = re.sub(pattern, replacement, content)
    script_path.write_text(updated_content, encoding='utf-8')


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MyPy type checking with regression detection')
    parser.add_argument('--fast', action='store_true', help='Fast mode: only show error count')
    parser.add_argument('--fix-baseline', action='store_true', help='Update baseline to current error count')
    args = parser.parse_args()

    BASELINE_ERRORS = 56  # Current baseline (updated 2025-09-18)
    TARGET_ERRORS = 0     # Ultimate goal

    print("🔍 Running MyPy type checking...")
    error_count, output = run_mypy()

    if error_count == -1:
        print("❌ Failed to run MyPy")
        sys.exit(1)

    if args.fix_baseline:
        update_baseline_in_script(error_count)
        print(f"✅ Baseline updated from {BASELINE_ERRORS} to {error_count}")
        print("📝 Please commit this change to preserve the new baseline")
        sys.exit(0)

    print(f"\n📊 Type checking results:")
    print(f"   Current errors: {error_count}")
    print(f"   Baseline:       {BASELINE_ERRORS}")
    print(f"   Target:         {TARGET_ERRORS}")

    if error_count == 0:
        print("🎉 Perfect! No type errors found!")
        sys.exit(0)
    elif error_count <= BASELINE_ERRORS:
        improvement = BASELINE_ERRORS - error_count
        if improvement > 0:
            print(f"✅ Good! Reduced errors by {improvement}")
        else:
            print("✅ No regression detected")

        if not args.fast:
            print("\n📝 Current errors:")
            print(output)
        sys.exit(0)
    else:
        regression = error_count - BASELINE_ERRORS
        print(f"❌ Regression detected! {regression} new type errors")
        if not args.fast:
            print("\n📝 All errors:")
            print(output)
        sys.exit(1)


if __name__ == "__main__":
    main()