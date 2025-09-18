#!/usr/bin/env python3
"""
Type checking script using MyPy.

Runs MyPy type checking and tracks error count to prevent regressions.
Current baseline: 52 errors (as of 2025-09-18)
Target: 0 errors
"""

import subprocess
import sys
import re
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


def main():
    """Main entry point."""
    BASELINE_ERRORS = 52  # Current baseline
    TARGET_ERRORS = 0     # Ultimate goal

    print("🔍 Running MyPy type checking...")
    error_count, output = run_mypy()

    if error_count == -1:
        print("❌ Failed to run MyPy")
        sys.exit(1)

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
        print("\n📝 Current errors:")
        print(output)
        sys.exit(0)
    else:
        regression = error_count - BASELINE_ERRORS
        print(f"❌ Regression detected! {regression} new type errors")
        print("\n📝 All errors:")
        print(output)
        sys.exit(1)


if __name__ == "__main__":
    main()