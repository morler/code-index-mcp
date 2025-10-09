#!/usr/bin/env python3
"""
Performance Baseline Tests for Apply Edit Backup Removal

Establishes current performance metrics for apply_edit with disk backup.
This baseline will be used to measure improvements after implementing
memory-based backup system.

Key Metrics:
- Average response time for edit operations
- Disk usage for backup files  
- Memory usage during operations
- Throughput (edits per second)
"""

import os
import sys
import time
import tempfile
import shutil
import statistics
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@dataclass
class PerformanceMetrics:
    """Performance measurement results"""
    operation: str
    response_times: List[float]
    memory_usage_mb: float
    disk_usage_mb: float
    throughput_ops_per_sec: float
    success_rate: float

class BaselinePerformanceTest:
    """Baseline performance measurement for current disk-based backup system"""
    
    def __init__(self, test_dir: str = None):
        self.test_dir = Path(test_dir or tempfile.mkdtemp(prefix="edit_baseline_"))
        self.test_files = []
        self.backup_dir = self.test_dir / ".edit_backup"
        
    def setup_test_files(self, count: int = 100) -> None:
        """Create test files for performance measurement"""
        print(f"Creating {count} test files...")
        
        for i in range(count):
            file_path = self.test_dir / f"test_file_{i}.py"
            
            # Generate realistic Python content
            content = f'''#!/usr/bin/env python3
"""
Test file {i} for performance baseline testing
"""

import os
import sys
from typing import List, Dict, Optional

class TestClass{i}:
    """Test class {i}"""
    
    def __init__(self, name: str):
        self.name = name
        self.data = []
    
    def method_{i}(self, param: int) -> str:
        """Test method {i}"""
        return f"{{self.name}}_{{param}}"
    
    def calculate_{i}(self, values: List[int]) -> int:
        """Calculation method {i}"""
        return sum(values) * len(values)

def function_{i}(x: int, y: int) -> int:
    """Test function {i}"""
    return x * y + i

def main_{i}():
    """Main function {i}"""
    obj = TestClass{i}("test")
    result = obj.method_{i}(42)
    print(f"Result: {{result}}")
    return result

if __name__ == "__main__":
    main_{i}()
'''
            
            file_path.write_text(content, encoding='utf-8')
            self.test_files.append(file_path)
        
        print(f"✅ Created {len(self.test_files)} test files")
    
    def measure_current_edit_performance(self) -> PerformanceMetrics:
        """Measure current disk-based backup edit performance"""
        print("\n=== Measuring Current Edit Performance ===")
        
        try:
            from core.index import CodeIndex
            index = CodeIndex(
                base_path=str(self.test_dir),
                files={},
                symbols={}
            )
        except ImportError:
            print("❌ Cannot import CodeIndex, using mock edit operations")
            return self._measure_mock_edit_performance()
        
        response_times = []
        successful_edits = 0
        total_edits = len(self.test_files)
        
        # Measure baseline memory
        baseline_memory = self._get_memory_usage()
        
        start_time = time.time()
        
        for i, file_path in enumerate(self.test_files):
            # Read current content
            old_content = file_path.read_text(encoding='utf-8')
            
            # Create new content (modify a line)
            lines = old_content.split('\n')
            for j, line in enumerate(lines):
                if f'def method_{i}(' in line:
                    lines[j] = line.replace('return f"', 'return f"MODIFIED_')
                    break
            new_content = '\n'.join(lines)
            
            # Measure edit operation time
            edit_start = time.time()
            success, error = index.edit_file_atomic(str(file_path), old_content, new_content)
            edit_time = time.time() - edit_start
            
            response_times.append(edit_time)
            
            if success:
                successful_edits += 1
            else:
                print(f"❌ Edit failed for {file_path.name}: {error}")
            
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{total_edits} edits")
        
        total_time = time.time() - start_time
        
        # Measure disk usage (backup files)
        disk_usage = self._calculate_disk_usage()
        
        # Measure memory usage
        final_memory = self._get_memory_usage()
        memory_usage = final_memory - baseline_memory
        
        # Calculate metrics
        throughput = total_edits / total_time if total_time > 0 else 0
        success_rate = (successful_edits / total_edits) * 100 if total_edits > 0 else 0
        
        metrics = PerformanceMetrics(
            operation="disk_backup_edit",
            response_times=response_times,
            memory_usage_mb=memory_usage,
            disk_usage_mb=disk_usage,
            throughput_ops_per_sec=throughput,
            success_rate=success_rate
        )
        
        self._print_metrics(metrics)
        return metrics
    
    def _measure_mock_edit_performance(self) -> PerformanceMetrics:
        """Mock performance measurement when CodeIndex unavailable"""
        print("Using mock edit operations...")
        
        response_times = []
        successful_edits = 0
        total_edits = len(self.test_files)
        
        # Simulate edit operations with timing
        for i, file_path in enumerate(self.test_files):
            old_content = file_path.read_text(encoding='utf-8')
            
            # Simulate backup creation (disk I/O)
            backup_path = str(file_path) + ".backup"
            edit_start = time.time()
            
            try:
                # Mock backup creation
                shutil.copy2(file_path, backup_path)
                
                # Mock edit operation
                new_content = old_content.replace(f'def method_{i}(', f'def MODIFIED_method_{i}(')
                file_path.write_text(new_content, encoding='utf-8')
                
                # Mock backup cleanup
                os.remove(backup_path)
                
                edit_time = time.time() - edit_start
                response_times.append(edit_time)
                successful_edits += 1
                
            except Exception as e:
                print(f"❌ Mock edit failed: {e}")
                response_times.append(1.0)  # Default penalty time
        
        # Calculate mock metrics
        avg_time = statistics.mean(response_times) if response_times else 0
        throughput = total_edits / sum(response_times) if response_times else 0
        success_rate = (successful_edits / total_edits) * 100 if total_edits > 0 else 0
        
        metrics = PerformanceMetrics(
            operation="mock_disk_backup_edit",
            response_times=response_times,
            memory_usage_mb=5.0,  # Mock memory usage
            disk_usage_mb=2.0,    # Mock disk usage (backup files)
            throughput_ops_per_sec=throughput,
            success_rate=success_rate
        )
        
        self._print_metrics(metrics)
        return metrics
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # psutil not available
    
    def _calculate_disk_usage(self) -> float:
        """Calculate disk usage of test files and backups in MB"""
        total_size = 0
        
        # Calculate test file sizes
        for file_path in self.test_files:
            if file_path.exists():
                total_size += file_path.stat().st_size
        
        # Calculate backup directory size
        if self.backup_dir.exists():
            for backup_file in self.backup_dir.rglob('*'):
                if backup_file.is_file():
                    total_size += backup_file.stat().st_size
        
        return total_size / 1024 / 1024  # Convert to MB
    
    def _print_metrics(self, metrics: PerformanceMetrics) -> None:
        """Print detailed performance metrics"""
        print(f"\n📊 Performance Metrics for {metrics.operation}:")
        print(f"  📈 Response Time:")
        if metrics.response_times:
            print(f"    Average: {statistics.mean(metrics.response_times)*1000:.2f}ms")
            print(f"    Median:  {statistics.median(metrics.response_times)*1000:.2f}ms")
            print(f"    Min:     {min(metrics.response_times)*1000:.2f}ms")
            print(f"    Max:     {max(metrics.response_times)*1000:.2f}ms")
        
        print(f"  💾 Memory Usage: {metrics.memory_usage_mb:.2f} MB")
        print(f"  💿 Disk Usage: {metrics.disk_usage_mb:.2f} MB")
        print(f"  ⚡ Throughput: {metrics.throughput_ops_per_sec:.2f} ops/sec")
        print(f"  ✅ Success Rate: {metrics.success_rate:.1f}%")
    
    def cleanup(self) -> None:
        """Clean up test files and directories"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"🧹 Cleaned up test directory: {self.test_dir}")

def run_baseline_test(num_files: int = 100) -> PerformanceMetrics:
    """Run complete baseline performance test"""
    print(f"🚀 Starting Baseline Performance Test with {num_files} files")
    print("=" * 60)
    
    test = BaselinePerformanceTest()
    
    try:
        # Setup test environment
        test.setup_test_files(num_files)
        
        # Measure current performance
        metrics = test.measure_current_edit_performance()
        
        print("\n" + "=" * 60)
        print("🎯 Baseline Performance Test Complete!")
        
        return metrics
        
    finally:
        # Cleanup
        test.cleanup()

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply Edit Performance Baseline Test")
    parser.add_argument("--files", type=int, default=100, help="Number of test files (default: 100)")
    parser.add_argument("--output", type=str, help="Output file for metrics (JSON)")
    
    args = parser.parse_args()
    
    # Run baseline test
    metrics = run_baseline_test(args.files)
    
    # Save results if requested
    if args.output:
        import json
        results = {
            "operation": metrics.operation,
            "avg_response_time_ms": statistics.mean(metrics.response_times) * 1000 if metrics.response_times else 0,
            "memory_usage_mb": metrics.memory_usage_mb,
            "disk_usage_mb": metrics.disk_usage_mb,
            "throughput_ops_per_sec": metrics.throughput_ops_per_sec,
            "success_rate": metrics.success_rate,
            "response_times_ms": [t * 1000 for t in metrics.response_times]
        }
        
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"💾 Results saved to: {args.output}")
    
    # Print summary for comparison
    print(f"\n📋 Baseline Summary (Target: 20% improvement)")
    print(f"  Response Time: {statistics.mean(metrics.response_times)*1000:.1f}ms → Target: ≤{statistics.mean(metrics.response_times)*1000*0.8:.1f}ms")
    print(f"  Disk Usage: {metrics.disk_usage_mb:.1f}MB → Target: ≤{metrics.disk_usage_mb*0.5:.1f}MB")

if __name__ == "__main__":
    main()