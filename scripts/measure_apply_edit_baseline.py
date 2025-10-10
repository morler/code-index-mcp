#!/usr/bin/env python3

"""Measure Code Index MCP apply_edit performance baseline.

This script measures the current apply_edit operations to establish a performance
baseline before implementing memory-based backup changes.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import tempfile
import tracemalloc
from pathlib import Path
from typing import Any, Dict, Optional


def _bytes_to_mib(value: Optional[int]) -> Optional[float]:
    if value is None:
        return None
    return round(value / (1024 * 1024), 2)


def create_test_file(size_kb: int = 10) -> tuple[Path, str]:
    """Create a test file of specified size."""
    content = "x" * (size_kb * 1024)  # Create file with specified size
    return Path(tempfile.mktemp(suffix=".txt")), content


def measure_apply_edit_performance(file_size_kb: int = 10) -> Dict[str, Any]:
    """Measure apply_edit operation performance."""
    # Add src to path
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    try:
        from code_index_mcp.server_unified import apply_edit
    except ImportError:
        # Fallback for testing
        def apply_edit(file_path: str, new_content: str, **kwargs):
            # Simple file write for baseline measurement
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return {"success": True, "bytes_written": len(new_content.encode())}

    # Create test file
    test_file, original_content = create_test_file(file_size_kb)
    new_content = original_content + "\n# Modified content\n"
    
    try:
        # Write original content
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        gc.collect()
        tracemalloc.start()
        start_time = time.perf_counter()
        
        # Measure apply_edit operation
        result = apply_edit(str(test_file), original_content, new_content)
        
        duration = time.perf_counter() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Check for backup files
        backup_files = []
        for suffix in ['.backup', '.bak', '.orig']:
            backup_path = test_file.with_suffix(test_file.suffix + suffix)
            if backup_path.exists():
                backup_files.append(str(backup_path))
        
        return {
            'file_size_kb': file_size_kb,
            'operation': 'apply_edit',
            'duration_seconds': round(duration, 3),
            'python_current_bytes': current,
            'python_peak_bytes': peak,
            'python_current_mib': _bytes_to_mib(current),
            'python_peak_mib': _bytes_to_mib(peak),
            'backup_files_created': backup_files,
            'backup_count': len(backup_files),
            'success': result.get('success', True),
            'bytes_written': result.get('bytes_written', len(new_content.encode())),
            'file_path': str(test_file)
        }
    
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        for suffix in ['.backup', '.bak', '.orig']:
            backup_path = test_file.with_suffix(test_file.suffix + suffix)
            if backup_path.exists():
                backup_path.unlink()


def measure_multiple_operations(sizes_kb: list[int]) -> Dict[str, Any]:
    """Measure apply_edit performance across different file sizes."""
    results = []
    
    for size in sizes_kb:
        print(f"Measuring {size}KB file...")
        result = measure_apply_edit_performance(size)
        results.append(result)
    
    # Calculate aggregates
    durations = [r['duration_seconds'] for r in results]
    peak_memory = [r['python_peak_mib'] or 0 for r in results]
    backup_counts = [r['backup_count'] for r in results]
    
    return {
        'timestamp': time.time(),
        'test_type': 'apply_edit_baseline',
        'file_sizes_tested': sizes_kb,
        'results': results,
        'summary': {
            'avg_duration_seconds': round(sum(durations) / len(durations), 3),
            'max_duration_seconds': round(max(durations), 3),
            'min_duration_seconds': round(min(durations), 3),
            'avg_peak_memory_mib': round(sum(peak_memory) / len(peak_memory), 2),
            'max_peak_memory_mib': round(max(peak_memory), 2),
            'backup_files_per_operation': backup_counts,
            'creates_backup_files': any(backup_counts)
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Measure apply_edit performance baseline')
    parser.add_argument('--sizes', type=str, default='1,10,100,1000', 
                       help='Comma-separated list of file sizes in KB to test')
    parser.add_argument('--output', type=Path, default=None, 
                       help='Optional output file to write JSON metrics')
    args = parser.parse_args()
    
    # Parse file sizes
    sizes_kb = [int(s.strip()) for s in args.sizes.split(',')]
    
    # Run measurements
    metrics = measure_multiple_operations(sizes_kb)
    
    # Output results
    output = json.dumps(metrics, indent=2)
    
    if args.output:
        args.output.write_text(output + '\n', encoding='utf-8')
        print(f"Results written to {args.output}")
    
    print(output)


if __name__ == '__main__':
    main()