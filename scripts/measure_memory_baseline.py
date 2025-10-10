#!/usr/bin/env python3
"""
Memory Usage Baseline Measurement

Measures current memory usage patterns for apply_edit operations.
This establishes baseline metrics for comparison with memory-based backup system.

Following Linus's principle: "Measure everything, assume nothing."
"""

import os
import sys
import time
import tempfile
import tracemalloc
from pathlib import Path
from typing import Dict, List, Any
import json

# Try to import psutil, use fallback if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not available, using basic memory tracking only")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.edit import EditOperation, apply_edit, rollback_edit


class MemoryBaseline:
    """Measure memory usage for current disk-based backup system."""
    
    def __init__(self):
        if HAS_PSUTIL:
            self.process = psutil.Process()
        else:
            self.process = None
        self.baseline_memory = None
        self.measurements = []
    
    def start_measurement(self):
        """Start memory tracking."""
        # Start tracemalloc for detailed memory tracking
        tracemalloc.start()
        
        # Get baseline memory
        if HAS_PSUTIL:
            self.baseline_memory = self.process.memory_info()
            print(f"Baseline memory: {self.baseline_memory.rss / 1024 / 1024:.2f} MB RSS")
            print(f"Baseline memory: {self.baseline_memory.vms / 1024 / 1024:.2f} MB VMS")
        else:
            self.baseline_memory = None
            print("Baseline memory: psutil not available, using tracemalloc only")
    
    def measure_operation(self, name: str, operation_func) -> Dict[str, Any]:
        """Measure memory usage for a specific operation."""
        # Memory before operation
        if HAS_PSUTIL:
            memory_before = self.process.memory_info()
        else:
            memory_before = None
        tracemalloc_before = tracemalloc.get_traced_memory()
        
        # Execute operation
        start_time = time.perf_counter()
        result = operation_func()
        end_time = time.perf_counter()
        
        # Memory after operation
        if HAS_PSUTIL:
            memory_after = self.process.memory_info()
        else:
            memory_after = None
        tracemalloc_after = tracemalloc.get_traced_memory()
        
        # Calculate differences
        if HAS_PSUTIL:
            rss_diff = memory_after.rss - memory_before.rss
            vms_diff = memory_after.vms - memory_before.vms
        else:
            rss_diff = 0
            vms_diff = 0
        current, peak = tracemalloc_after
        current_before, peak_before = tracemalloc_before
        tracemalloc_current_diff = current - current_before
        tracemalloc_peak_diff = peak - peak_before
        
        if HAS_PSUTIL:
            measurement = {
                'name': name,
                'duration_ms': (end_time - start_time) * 1000,
                'rss_before_mb': memory_before.rss / 1024 / 1024,
                'rss_after_mb': memory_after.rss / 1024 / 1024,
                'rss_diff_mb': rss_diff / 1024 / 1024,
                'vms_before_mb': memory_before.vms / 1024 / 1024,
                'vms_after_mb': memory_after.vms / 1024 / 1024,
                'vms_diff_mb': vms_diff / 1024 / 1024,
                'tracemalloc_current_mb': current / 1024 / 1024,
                'tracemalloc_peak_mb': peak / 1024 / 1024,
                'tracemalloc_current_diff_mb': tracemalloc_current_diff / 1024 / 1024,
                'tracemalloc_peak_diff_mb': tracemalloc_peak_diff / 1024 / 1024,
                'result': result
            }
        else:
            measurement = {
                'name': name,
                'duration_ms': (end_time - start_time) * 1000,
                'rss_before_mb': 0,
                'rss_after_mb': 0,
                'rss_diff_mb': 0,
                'vms_before_mb': 0,
                'vms_after_mb': 0,
                'vms_diff_mb': 0,
                'tracemalloc_current_mb': current / 1024 / 1024,
                'tracemalloc_peak_mb': peak / 1024 / 1024,
                'tracemalloc_current_diff_mb': tracemalloc_current_diff / 1024 / 1024,
                'tracemalloc_peak_diff_mb': tracemalloc_peak_diff / 1024 / 1024,
                'result': result
            }
        
        self.measurements.append(measurement)
        
        print(f"\n{name}:")
        print(f"  Duration: {measurement['duration_ms']:.2f}ms")
        print(f"  RSS change: {measurement['rss_diff_mb']:.2f} MB")
        print(f"  VMS change: {measurement['vms_diff_mb']:.2f} MB")
        print(f"  Tracemalloc current: {measurement['tracemalloc_current_diff_mb']:.2f} MB")
        print(f"  Tracemalloc peak: {measurement['tracemalloc_peak_diff_mb']:.2f} MB")
        
        return measurement
    
    def create_test_files(self, temp_dir: Path) -> Dict[str, Path]:
        """Create test files of various sizes."""
        files = {}
        
        # Small file (~1KB)
        small_content = "def small_function():\n    return 'small'\n" * 20
        files['small'] = temp_dir / "small.py"
        files['small'].write_text(small_content)
        
        # Medium file (~10KB)
        medium_content = "class MediumClass:\n    def method(self):\n        pass\n" * 200
        files['medium'] = temp_dir / "medium.py"
        files['medium'].write_text(medium_content)
        
        # Large file (~100KB)
        large_content = "# Large file content\n" + "x = 1\n" * 2000
        files['large'] = temp_dir / "large.py"
        files['large'].write_text(large_content)
        
        # Very large file (~1MB)
        very_large_content = "def very_large_function():\n    return 'very large'\n" * 20000
        files['very_large'] = temp_dir / "very_large.py"
        files['very_large'].write_text(very_large_content)
        
        return files
    
    def measure_file_edit(self, file_path: Path) -> Dict[str, Any]:
        """Measure memory usage for editing a specific file."""
        def edit_operation():
            old_content = file_path.read_text(encoding='utf-8')
            new_content = old_content + f"\n# Edited at {time.time()}\n"
            
            operation = EditOperation(
                file_path=str(file_path),
                old_content=old_content,
                new_content=new_content
            )
            
            success, error = apply_edit(operation)
            
            # Cleanup backup
            if operation.backup_path and Path(operation.backup_path).exists():
                Path(operation.backup_path).unlink()
            
            return {'success': success, 'error': error}
        
        return self.measure_operation(f"edit_{file_path.name}", edit_operation)
    
    def measure_rollback(self, file_path: Path) -> Dict[str, Any]:
        """Measure memory usage for rollback operation."""
        def rollback_operation():
            old_content = file_path.read_text(encoding='utf-8')
            new_content = "# Completely different content\n"
            
            operation = EditOperation(
                file_path=str(file_path),
                old_content=old_content,
                new_content=new_content
            )
            
            # Apply edit first
            success, error = apply_edit(operation)
            if not success:
                return {'success': False, 'error': error}
            
            # Then rollback
            rollback_success = rollback_edit(operation)
            
            # Cleanup backup
            if operation.backup_path and Path(operation.backup_path).exists():
                Path(operation.backup_path).unlink()
            
            return {'success': rollback_success}
        
        return self.measure_operation(f"rollback_{file_path.name}", rollback_operation)
    
    def measure_concurrent_edits(self, files: Dict[str, Path]) -> Dict[str, Any]:
        """Measure memory usage for concurrent file edits."""
        def concurrent_operation():
            results = []
            for name, file_path in files.items():
                old_content = file_path.read_text(encoding='utf-8')
                new_content = old_content + f"\n# Concurrent edit to {name}\n"
                
                operation = EditOperation(
                    file_path=str(file_path),
                    old_content=old_content,
                    new_content=new_content
                )
                
                success, error = apply_edit(operation)
                results.append({'name': name, 'success': success, 'error': error})
                
                # Cleanup backup
                if operation.backup_path and Path(operation.backup_path).exists():
                    Path(operation.backup_path).unlink()
            
            return results
        
        return self.measure_operation("concurrent_edits", concurrent_operation)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory usage report."""
        if not self.measurements:
            return {'error': 'No measurements available'}
        
        # Calculate statistics
        rss_changes = [m['rss_diff_mb'] for m in self.measurements]
        vms_changes = [m['vms_diff_mb'] for m in self.measurements]
        tracemalloc_changes = [m['tracemalloc_current_diff_mb'] for m in self.measurements]
        durations = [m['duration_ms'] for m in self.measurements]
        
        if HAS_PSUTIL:
            baseline_data = {
                'rss_mb': self.baseline_memory.rss / 1024 / 1024,
                'vms_mb': self.baseline_memory.vms / 1024 / 1024
            }
        else:
            baseline_data = {'rss_mb': 0, 'vms_mb': 0}
        
        report = {
            'baseline': baseline_data,
            'statistics': {
                'total_operations': len(self.measurements),
                'avg_rss_change_mb': sum(rss_changes) / len(rss_changes),
                'max_rss_change_mb': max(rss_changes),
                'min_rss_change_mb': min(rss_changes),
                'avg_vms_change_mb': sum(vms_changes) / len(vms_changes),
                'max_vms_change_mb': max(vms_changes),
                'min_vms_change_mb': min(vms_changes),
                'avg_tracemalloc_change_mb': sum(tracemalloc_changes) / len(tracemalloc_changes),
                'max_tracemalloc_change_mb': max(tracemalloc_changes),
                'min_tracemalloc_change_mb': min(tracemalloc_changes),
                'avg_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations)
            },
            'measurements': self.measurements
        }
        
        return report
    
    def save_report(self, filename: str):
        """Save memory usage report to file."""
        report = self.generate_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nMemory baseline report saved to: {filename}")
        
        # Print summary
        stats = report['statistics']
        print(f"\n=== Memory Baseline Summary ===")
        print(f"Total operations: {stats['total_operations']}")
        print(f"Average RSS change: {stats['avg_rss_change_mb']:.2f} MB")
        print(f"Average VMS change: {stats['avg_vms_change_mb']:.2f} MB")
        print(f"Average tracemalloc change: {stats['avg_tracemalloc_change_mb']:.2f} MB")
        print(f"Average duration: {stats['avg_duration_ms']:.2f} ms")


def main():
    """Run memory baseline measurements."""
    print("=== Memory Usage Baseline Measurement ===")
    
    baseline = MemoryBaseline()
    baseline.start_measurement()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        print("\nCreating test files...")
        files = baseline.create_test_files(temp_path)
        
        # Measure individual file edits
        print("\nMeasuring individual file edits...")
        for name, file_path in files.items():
            baseline.measure_file_edit(file_path)
        
        # Measure rollback operations
        print("\nMeasuring rollback operations...")
        for name, file_path in files.items():
            baseline.measure_rollback(file_path)
        
        # Measure concurrent edits
        print("\nMeasuring concurrent edits...")
        baseline.measure_concurrent_edits(files)
    
    # Generate and save report
    report_path = "memory_baseline_report.json"
    baseline.save_report(report_path)
    
    # Stop tracemalloc
    tracemalloc.stop()
    
    print("\n=== Memory Baseline Complete ===")


if __name__ == "__main__":
    main()