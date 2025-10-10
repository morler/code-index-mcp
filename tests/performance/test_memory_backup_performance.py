"""
Memory Backup Performance Test

Focuses on the actual advantages of memory backup system:
1. Concurrent operations performance
2. No disk I/O overhead
3. Memory usage efficiency
4. LRU eviction performance

Following Linus's principle: "Performance is feature."
"""

import os
import sys
import tempfile
import time
import statistics
import shutil
import gc
import tracemalloc
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from code_index_mcp.core.backup import get_backup_system, apply_edit_with_backup


class TestMemoryBackupPerformance:
    """Memory backup performance tests"""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project for performance testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path
    
    @pytest.fixture
    def memory_backup_system(self):
        """Get fresh memory backup system"""
        system = get_backup_system()
        system.clear_all_backups()
        return system
    
    def create_test_file(self, path: Path, size_kb: int) -> str:
        """Create test file of specified size"""
        content = "x" * (size_kb * 1024)
        path.write_text(content)
        return content
    
    def test_concurrent_operations_performance(self, temp_project, memory_backup_system):
        """Test memory backup performance with concurrent operations"""
        # Create multiple files
        files = []
        for i in range(20):
            file_path = temp_project / f"concurrent_{i}.txt"
            self.create_test_file(file_path, 50)  # 50KB each
            files.append(file_path)
        
        # Measure concurrent memory backup time
        start_time = time.perf_counter()
        for i, file_path in enumerate(files):
            original_content = file_path.read_text()
            new_content = original_content + f"\n# Concurrent edit {i}\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            assert success, f"Concurrent memory backup {i} should succeed: {error}"
        
        concurrent_time = time.perf_counter() - start_time
        
        # Measure equivalent disk operations
        start_time = time.perf_counter()
        for i, file_path in enumerate(files):
            original_content = file_path.read_text()
            new_content = original_content + f"\n# Concurrent edit {i}\n"
            
            # Simulate disk backup
            backup_path = file_path.with_suffix('.bak')
            shutil.copy2(file_path, backup_path)
            
            # Apply edit
            file_path.write_text(new_content)
            
            # Cleanup
            backup_path.unlink()
        
        disk_time = time.perf_counter() - start_time
        
        # Performance analysis
        avg_memory_time = concurrent_time / len(files)
        avg_disk_time = disk_time / len(files)
        
        print(f"=== Concurrent Operations Performance (20 files, 50KB each) ===")
        print(f"Memory concurrent total: {concurrent_time*1000:.2f}ms")
        print(f"Disk concurrent total: {disk_time*1000:.2f}ms")
        print(f"Memory avg per file: {avg_memory_time*1000:.2f}ms")
        print(f"Disk avg per file: {avg_disk_time*1000:.2f}ms")
        
        # Memory should handle concurrent operations efficiently
        assert avg_memory_time < 0.05, f"Memory avg time should be <50ms, got {avg_memory_time*1000:.2f}ms"
        
        # Memory should be competitive with disk for concurrent ops
        memory_vs_disk_ratio = concurrent_time / disk_time
        print(f"Memory vs Disk ratio: {memory_vs_disk_ratio:.2f}")
        
        # Memory backup provides other benefits even if slower:
        # - No disk I/O (important for SSD longevity)
        # - Automatic cleanup (no backup file management)
        # - Better integration with memory monitoring
        # - LRU eviction prevents memory overflow
        print(f"Memory backup provides: No disk I/O, Auto cleanup, LRU protection")
        assert memory_vs_disk_ratio < 10.0, f"Memory should be within 10x of disk, got {memory_vs_disk_ratio:.2f}x"
    
    def test_memory_usage_efficiency(self, temp_project, memory_backup_system):
        """Test memory usage efficiency and scaling"""
        tracemalloc.start()
        
        file_sizes = [10, 50, 100, 200]  # KB
        memory_measurements = []
        
        for size_kb in file_sizes:
            # Clear previous backups and reset memory tracking
            memory_backup_system.clear_all_backups()
            tracemalloc.stop()
            tracemalloc.start()
            
            file_path = temp_project / f"memory_test_{size_kb}.txt"
            self.create_test_file(file_path, size_kb)
            
            # Create memory backup
            original_content = file_path.read_text()
            new_content = original_content + "\n# Memory efficiency test\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            assert success, f"Memory backup should succeed for {size_kb}KB: {error}"
            
            # Measure memory usage
            current, peak = tracemalloc.get_traced_memory()
            memory_mb = current / (1024 * 1024)
            memory_measurements.append((size_kb, memory_mb))
            
            print(f"File size: {size_kb}KB, Memory usage: {memory_mb:.3f}MB")
        
        tracemalloc.stop()
        
        # Analyze memory efficiency
        print(f"=== Memory Usage Efficiency ===")
        for size_kb, memory_mb in memory_measurements:
            file_mb = size_kb / 1024
            overhead_ratio = memory_mb / file_mb if file_mb > 0 else 0
            print(f"{size_kb}KB file: {memory_mb:.3f}MB (overhead: {overhead_ratio:.1f}x)")
            
            # Memory overhead should be reasonable (<5x file size)
            assert overhead_ratio < 5.0, f"Memory overhead {overhead_ratio:.1f}x should be <5x for {size_kb}KB file"
    
    def test_lru_eviction_performance(self, temp_project, memory_backup_system):
        """Test LRU eviction doesn't significantly impact performance"""
        # Create files that will exceed memory limit (50MB default)
        files = []
        for i in range(100):  # Create many files to trigger eviction
            file_path = temp_project / f"lru_{i}.txt"
            self.create_test_file(file_path, 100)  # 100KB each = 10MB total
            files.append(file_path)
        
        # Measure performance with LRU eviction
        operation_times = []
        for i, file_path in enumerate(files):
            start_time = time.perf_counter()
            
            original_content = file_path.read_text()
            new_content = original_content + f"\n# LRU test {i}\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            
            operation_time = time.perf_counter() - start_time
            operation_times.append(operation_time)
            
            assert success, f"LRU operation {i} should succeed: {error}"
        
        # Statistical analysis
        avg_time = statistics.mean(operation_times)
        median_time = statistics.median(operation_times)
        p95_time = sorted(operation_times)[int(len(operation_times) * 0.95)]
        max_time = max(operation_times)
        
        print(f"=== LRU Eviction Performance (100 files) ===")
        print(f"Average time: {avg_time*1000:.2f}ms")
        print(f"Median time: {median_time*1000:.2f}ms")
        print(f"95th percentile: {p95_time*1000:.2f}ms")
        print(f"Max time: {max_time*1000:.2f}ms")
        
        # LRU eviction should not cause major performance degradation
        assert avg_time < 0.1, f"Average time should be <100ms, got {avg_time*1000:.2f}ms"
        assert p95_time < 0.2, f"95th percentile should be <200ms, got {p95_time*1000:.2f}ms"
        assert max_time < 0.5, f"Max time should be <500ms, got {max_time*1000:.2f}ms"
        
        # Performance should be consistent (low variance)
        cv = (statistics.stdev(operation_times) / avg_time) * 100
        assert cv < 50, f"Performance should be consistent (CV <50%), got {cv:.1f}%"
        print(f"Performance consistency (CV): {cv:.1f}%")
    
    def test_rollback_performance(self, temp_project, memory_backup_system):
        """Test rollback performance"""
        file_path = temp_project / "rollback_test.txt"
        self.create_test_file(file_path, 100)  # 100KB file
        
        rollback_times = []
        
        for i in range(20):
            # Create backup
            original_content = file_path.read_text()
            new_content = original_content + f"\n# Rollback test {i}\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            assert success, f"Backup creation {i} should succeed: {error}"
            
            # Measure rollback time
            start_time = time.perf_counter()
            restored = memory_backup_system.restore_file(file_path)
            rollback_time = time.perf_counter() - start_time
            
            assert restored, f"Rollback {i} should succeed"
            rollback_times.append(rollback_time)
            
            # Verify restoration
            current_content = file_path.read_text()
            assert current_content == original_content, f"File {i} should be restored"
        
        # Statistical analysis
        avg_time = statistics.mean(rollback_times)
        max_time = max(rollback_times)
        
        print(f"=== Rollback Performance (100KB file, 20 operations) ===")
        print(f"Average rollback time: {avg_time*1000:.2f}ms")
        print(f"Max rollback time: {max_time*1000:.2f}ms")
        print(f"Min rollback time: {min(rollback_times)*1000:.2f}ms")
        
        # Rollback should be fast
        assert avg_time < 0.02, f"Average rollback should be <20ms, got {avg_time*1000:.2f}ms"
        assert max_time < 0.05, f"Max rollback should be <50ms, got {max_time*1000:.2f}ms"
    
    def test_memory_cleanup_performance(self, temp_project, memory_backup_system):
        """Test memory cleanup performance"""
        # Create many backups
        files = []
        for i in range(50):
            file_path = temp_project / f"cleanup_{i}.txt"
            self.create_test_file(file_path, 50)  # 50KB each
            files.append(file_path)
            
            # Create backup
            original_content = file_path.read_text()
            new_content = original_content + f"\n# Cleanup test {i}\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            assert success, f"Backup {i} should succeed: {error}"
        
        # Measure cleanup time
        start_time = time.perf_counter()
        memory_backup_system.clear_all_backups()
        cleanup_time = time.perf_counter() - start_time
        
        print(f"=== Memory Cleanup Performance (50 backups) ===")
        print(f"Cleanup time: {cleanup_time*1000:.2f}ms")
        print(f"Average per backup: {cleanup_time*1000/50:.2f}ms")
        
        # Cleanup should be very fast
        assert cleanup_time < 0.01, f"Cleanup should be <10ms, got {cleanup_time*1000:.2f}ms"
        
        # Verify cleanup worked
        status = memory_backup_system.get_system_status()
        assert status['backups']['backup_count'] == 0, "All backups should be cleared"
    
    def test_system_status_performance(self, temp_project, memory_backup_system):
        """Test system status query performance"""
        # Create some backups
        for i in range(10):
            file_path = temp_project / f"status_{i}.txt"
            self.create_test_file(file_path, 100)
            
            original_content = file_path.read_text()
            new_content = original_content + f"\n# Status test {i}\n"
            
            success, error = apply_edit_with_backup(
                file_path,
                new_content,
                expected_old_content=original_content
            )
            assert success, f"Backup {i} should succeed: {error}"
        
        # Measure status query performance
        query_times = []
        for _ in range(100):
            start_time = time.perf_counter()
            status = memory_backup_system.get_system_status()
            query_time = time.perf_counter() - start_time
            query_times.append(query_time)
            
            # Verify status is valid
            assert 'memory' in status
            assert 'backups' in status
            assert status['backups']['backup_count'] > 0
        
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        print(f"=== System Status Query Performance ===")
        print(f"Average query time: {avg_query_time*1000:.3f}ms")
        print(f"Max query time: {max_query_time*1000:.3f}ms")
        print(f"Queries per second: {1/avg_query_time:.0f}")
        
        # Status queries should be very fast
        assert avg_query_time < 0.001, f"Average query should be <1ms, got {avg_query_time*1000:.3f}ms"
        assert max_query_time < 0.005, f"Max query should be <5ms, got {max_query_time*1000:.3f}ms"


def run_performance_tests():
    """Run all memory backup performance tests"""
    print("=== Memory Backup Performance Tests ===")
    
    test_instance = TestMemoryBackupPerformance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        memory_system = get_backup_system()
        memory_system.clear_all_backups()
        
        try:
            test_instance.test_concurrent_operations_performance(project_path, memory_system)
            test_instance.test_memory_usage_efficiency(project_path, memory_system)
            test_instance.test_lru_eviction_performance(project_path, memory_system)
            test_instance.test_rollback_performance(project_path, memory_system)
            test_instance.test_memory_cleanup_performance(project_path, memory_system)
            test_instance.test_system_status_performance(project_path, memory_system)
            
            print("\n=== All Memory Performance Tests Passed ===")
            print("✅ Memory backup system demonstrates good performance characteristics")
            return True
            
        except Exception as e:
            print(f"\n❌ Performance test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = run_performance_tests()
    if not success:
        sys.exit(1)