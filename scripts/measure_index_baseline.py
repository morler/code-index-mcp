#!/usr/bin/env python3

"""Measure Code Index MCP indexing performance.

This script runs a full index rebuild against a project path and reports
execution timing and memory metrics as JSON so the results can be compared
over time.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, Optional


def _bytes_to_mib(value: Optional[int]) -> Optional[float]:
    if value is None:
        return None
    return round(value / (1024 * 1024), 2)


def measure_index(project_root: Path, include_rss: bool) -> Dict[str, Any]:
    src_path = project_root / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from code_index_mcp.indexing import get_index_manager

    index_manager = get_index_manager()
    if hasattr(index_manager, 'cleanup'):
        index_manager.cleanup()

    if not index_manager.set_project_path(str(project_root)):
        raise SystemExit('Failed to set project path for index manager')

    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    if not index_manager.refresh_index():
        raise SystemExit('Index refresh failed')
    duration = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stats = index_manager.get_index_stats() or {}

    rss = None
    if include_rss:
        try:
            import psutil  # type: ignore
        except ModuleNotFoundError:
            rss = None
        else:
            rss = psutil.Process().memory_info().rss

    result: Dict[str, Any] = {
        'project_path': str(project_root),
        'duration_seconds': round(duration, 3),
        'python_current_bytes': current,
        'python_peak_bytes': peak,
        'python_current_mib': _bytes_to_mib(current),
        'python_peak_mib': _bytes_to_mib(peak),
        'process_rss_bytes': rss,
        'process_rss_mib': _bytes_to_mib(rss),
    }

    for key in ('indexed_files', 'total_symbols', 'languages', 'index_version', 'timestamp', 'status'):
        if key in stats:
            result[f'index_{key}'] = stats[key]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Measure Code Index MCP indexing performance')
    parser.add_argument('--project-root', type=Path, default=None, help='Project root to index (defaults to repository root)')
    parser.add_argument('--no-rss', action='store_true', help='Skip process RSS measurement')
    parser.add_argument('--output', type=Path, default=None, help='Optional output file to write JSON metrics')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    default_root = script_dir.parent
    project_root = (args.project_root or default_root).resolve()

    if not project_root.exists():
        raise SystemExit(f'Project root does not exist: {project_root}')

    metrics = measure_index(project_root, include_rss=not args.no_rss)
    output = json.dumps(metrics, indent=2)

    if args.output:
        args.output.write_text(output + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
