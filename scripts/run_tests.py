#!/usr/bin/env python3
"""Test runner script for the Code Index MCP project.

Following Linus's principle: "Good programmers worry about data structures."
Provides simple, focused test execution and reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description, cwd=None):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Success!")
        if result.stdout:
            print(f"Output:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with exit code {e.returncode}")
        if e.stdout:
            print(f"Stdout:\n{e.stdout}")
        if e.stderr:
            print(f"Stderr:\n{e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run tests for Code Index MCP")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--file", type=str, help="Run specific test file")

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print(f"📁 Working directory: {project_root}")
    print(f"🐍 Python: {sys.executable}")

    # Base pytest command
    cmd = ["uv", "run", "python", "-m", "pytest"]

    # Add test markers
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])

    # Add specific file if requested
    if args.file:
        cmd.append(f"tests/{args.file}")
    else:
        cmd.append("tests/")

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Skip slow tests if requested
    if args.fast:
        cmd.extend(["-m", "not slow"])

    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=src/code_index_mcp", "--cov-report=html", "--cov-report=term"])

    # Add other useful options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "--strict-markers",  # Fail on unknown markers
        "--strict-config",   # Fail on unknown config options
    ])

    # Run the tests
    success = run_command(cmd, "Running pytest", cwd=project_root)

    if args.coverage and success:
        print(f"\n📊 Coverage report generated: {project_root}/htmlcov/index.html")

    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests completed successfully!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())