#!/usr/bin/env python3
"""Final performance validation for memory backup system"""

import tempfile
import os
import sys
import time
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add src to path for imports
sys.path.insert(0, 'src')

from code_index_mcp.core.edit_models import MemoryBackupManager, EditOperation
from code_index_mcp.core.backup import get_backup_system
from code_index_mcp.config import reset_config
import pytest


class TestFinalPerformanceValidation:
    """Final performance validation tests"""
    
    def test_memory_backup_scalability(self):
        """Test memory backup scalability with different file sizes"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "50",  # 50MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "10"  # 10MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Test different file sizes
            file_sizes = [1, 10, 100, 500, 1000]  # KB
            backup_times = []
            
            for size_kb in file_sizes:
                file_path = project_path / f"test_{size_kb}kb.txt"
                content = "x" * (size_kb * 1024)
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                # Measure backup time
                start_time = time.perf_counter()
                success = manager.add_backup(operation)
                backup_time = time.perf_counter() - start_time
                
                backup_times.append(backup_time)
                
                print(f"   {size_kb}KB file: {backup_time*1000:.2f}ms")
                assert success, f"Backup should succeed for {size_kb}KB file"
            
            # Analyze scalability
            # Time should scale roughly linearly with file size
            small_file_time = backup_times[0]  # 1KB
            large_file_time = backup_times[-1]  # 1000KB
            
            size_ratio = file_sizes[-1] / file_sizes[0]  # 1000x
            time_ratio = large_file_time / small_file_time
            
            print(f"   Size ratio: {size_ratio}x")
            print(f"   Time ratio: {time_ratio:.1f}x")
            print(f"   Scalability efficiency: {size_ratio/time_ratio:.1f}")
            
            # Performance should be reasonable (not too slow)
            assert large_file_time < 0.1, "Large file backup should be under 100ms"
            assert time_ratio < size_ratio * 2, "Time scaling should be reasonable"
            
            print("✅ Memory backup scalability is acceptable")
    
    def test_lru_eviction_performance(self):
        """Test LRU eviction performance under memory pressure"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "5",  # 5MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Fill memory beyond limit to trigger evictions
            num_files = 20
            file_size_kb = 300  # 300KB each
            eviction_times = []
            
            for i in range(num_files):
                file_path = project_path / f"evict_test_{i}.txt"
                content = "x" * (file_size_kb * 1024)
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                # Measure time including potential eviction
                start_time = time.perf_counter()
                success = manager.add_backup(operation)
                add_time = time.perf_counter() - start_time
                
                eviction_times.append(add_time)
                
                if i % 5 == 0:
                    print(f"   File {i}: {add_time*1000:.2f}ms, Cache: {len(manager.backup_cache)}")
            
            # Analyze eviction performance
            avg_time = statistics.mean(eviction_times)
            max_time = max(eviction_times)
            
            print(f"   Average add time: {avg_time*1000:.2f}ms")
            print(f"   Max add time: {max_time*1000:.2f}ms")
            print(f"   Final cache size: {len(manager.backup_cache)}")
            print(f"   Memory usage: {manager.current_memory_mb:.2f}MB")
            
            # Eviction should not cause excessive delays
            assert max_time < 0.05, "Eviction should not cause excessive delays"
            assert avg_time < 0.02, "Average time should be reasonable"
            assert manager.current_memory_mb <= manager.max_memory_mb, "Memory should be within limits"
            
            print("✅ LRU eviction performance is acceptable")
    
    def test_concurrent_access_performance(self):
        """Test performance under concurrent access"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "20",  # 20MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "5"  # 5MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Pre-populate with some backups
            files = []
            for i in range(10):
                file_path = project_path / f"concurrent_file_{i}.txt"
                content = "x" * (100 * 1024)  # 100KB each
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                manager.add_backup(operation)
                files.append(file_path)
            
            def concurrent_access_worker(worker_id):
                """Worker that performs mixed operations"""
                start_time = time.perf_counter()
                operations = 0
                
                for i in range(50):
                    file_idx = i % len(files)
                    
                    if i % 3 == 0:
                        # Add backup
                        content = files[file_idx].read_text()
                        operation = EditOperation(
                            file_path=str(files[file_idx]),
                            original_content=content
                        )
                        manager.add_backup(operation)
                    elif i % 3 == 1:
                        # Get backup
                        manager.get_backup(str(files[file_idx]))
                    else:
                        # Remove backup
                        manager.remove_backup(str(files[file_idx]))
                    
                    operations += 1
                
                end_time = time.perf_counter()
                return operations, end_time - start_time
            
            # Run concurrent workers
            num_workers = 5
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(concurrent_access_worker, i) for i in range(num_workers)]
                
                total_operations = 0
                total_time = 0
                
                for future in futures:
                    operations, worker_time = future.result()
                    total_operations += operations
                    total_time = max(total_time, worker_time)  # Use max for parallel time
            
            # Calculate performance metrics
            ops_per_second = total_operations / total_time
            avg_time_per_op = total_time / total_operations * 1000
            
            print(f"   Total operations: {total_operations}")
            print(f"   Parallel time: {total_time:.3f}s")
            print(f"   Operations per second: {ops_per_second:.0f}")
            print(f"   Average time per operation: {avg_time_per_op:.2f}ms")
            
            # Performance should be reasonable under concurrency
            assert ops_per_second > 100, "Should handle at least 100 ops/sec under concurrency"
            assert avg_time_per_op < 10, "Average operation time should be under 10ms"
            
            print("✅ Concurrent access performance is acceptable")
    
    def test_memory_efficiency(self):
        """Test memory efficiency of the backup system"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "10",  # 10MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Add files and measure memory usage
            file_sizes_kb = [50, 100, 200, 400, 800]  # Different sizes
            total_original_size = 0
            
            for size_kb in file_sizes_kb:
                file_path = project_path / f"memory_test_{size_kb}.txt"
                content = "x" * (size_kb * 1024)
                file_path.write_text(content)
                
                total_original_size += len(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                manager.add_backup(operation)
            
            # Calculate memory efficiency
            memory_usage_mb = manager.current_memory_mb
            memory_usage_bytes = memory_usage_mb * 1024 * 1024
            overhead_ratio = memory_usage_bytes / total_original_size
            
            print(f"   Total original content: {total_original_size / 1024:.1f}KB")
            print(f"   Memory usage: {memory_usage_mb:.2f}MB")
            print(f"   Overhead ratio: {overhead_ratio:.2f}x")
            print(f"   Cache size: {len(manager.backup_cache)} files")
            
            # Memory overhead should be reasonable
            assert overhead_ratio < 2.0, "Memory overhead should be less than 2x"
            assert memory_usage_mb <= manager.max_memory_mb, "Memory should be within limits"
            
            print("✅ Memory efficiency is acceptable")
    
    def test_performance_regression_detection(self):
        """Test to detect performance regressions"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "20",  # 20MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "5"  # 5MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Performance benchmarks (these should be adjusted based on baseline)
            benchmarks = {
                'small_file_backup_ms': 5.0,    # 5KB file
                'medium_file_backup_ms': 10.0,  # 100KB file
                'large_file_backup_ms': 50.0,   # 1MB file
                'lru_eviction_ms': 20.0,        # Time for eviction operation
                'concurrent_ops_per_sec': 200   # Concurrent operations
            }
            
            # Test small file backup
            small_file = project_path / "small.txt"
            small_content = "x" * (5 * 1024)  # 5KB
            small_file.write_text(small_content)
            
            operation = EditOperation(
                file_path=str(small_file),
                original_content=small_content
            )
            
            start_time = time.perf_counter()
            manager.add_backup(operation)
            small_file_time = (time.perf_counter() - start_time) * 1000
            
            print(f"   Small file backup: {small_file_time:.2f}ms (benchmark: {benchmarks['small_file_backup_ms']}ms)")
            assert small_file_time < benchmarks['small_file_backup_ms'], "Small file backup performance regression"
            
            # Test medium file backup
            medium_file = project_path / "medium.txt"
            medium_content = "x" * (100 * 1024)  # 100KB
            medium_file.write_text(medium_content)
            
            operation = EditOperation(
                file_path=str(medium_file),
                original_content=medium_content
            )
            
            start_time = time.perf_counter()
            manager.add_backup(operation)
            medium_file_time = (time.perf_counter() - start_time) * 1000
            
            print(f"   Medium file backup: {medium_file_time:.2f}ms (benchmark: {benchmarks['medium_file_backup_ms']}ms)")
            assert medium_file_time < benchmarks['medium_file_backup_ms'], "Medium file backup performance regression"
            
            # Test large file backup
            large_file = project_path / "large.txt"
            large_content = "x" * (1024 * 1024)  # 1MB
            large_file.write_text(large_content)
            
            operation = EditOperation(
                file_path=str(large_file),
                original_content=large_content
            )
            
            start_time = time.perf_counter()
            manager.add_backup(operation)
            large_file_time = (time.perf_counter() - start_time) * 1000
            
            print(f"   Large file backup: {large_file_time:.2f}ms (benchmark: {benchmarks['large_file_backup_ms']}ms)")
            assert large_file_time < benchmarks['large_file_backup_ms'], "Large file backup performance regression"
            
            print("✅ No performance regressions detected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])