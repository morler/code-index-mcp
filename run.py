#!/usr/bin/env python
"""
Development convenience script to run the Code Index MCP server.
"""
import os
import sys
import traceback

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

def _explain_missing_dependency(error: ModuleNotFoundError) -> None:
    missing = getattr(error, "name", None) or str(error)
    sys.stderr.write(
        "Missing required dependency: {name}\n"
        "Install project requirements first (use `uv sync` or activate the provided virtual environment).\n"
        "Refer to README.md for setup instructions.\n".format(name=missing)
    )

def main() -> None:
    try:
        from code_index_mcp.server import main as server_main
    except ModuleNotFoundError as exc:
        _explain_missing_dependency(exc)
        raise SystemExit(1) from exc
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
    else:
        server_main()


if __name__ == "__main__":
    main()
