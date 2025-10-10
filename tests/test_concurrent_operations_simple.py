#!/usr/bin/env python3
"""Test concurrent file operations with memory backup - simplified version"""

import tempfile
import os
import sys
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path for imports
sys.path.insert(0, 'src')

from code_index_mcp.core.edit_models import MemoryBackupManager, EditOperation
from code_index_mcp.config import reset_config
import pytest


class TestConcurrentOperationsSimple:
    """Test concurrent file operations - simplified"""
    
    def test_concurrent_backup_additions(self):
        """Test concurrent backup additions to MemoryBackupManager"""
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
            
            def add_backup_worker(worker_id):
                """Worker function to add backups"""
                results = []
                for i in range(5):
                    file_path = project_path / f"worker_{worker_id}_file_{i}.txt"
                    content = f"x" * (100 * 1024)  # 100KB each
                    file_path.write_text(content)
                    
                    operation = EditOperation(
                        file_path=str(file_path),
                        original_content=content
                    )
                    
                    success = manager.add_backup(operation)
                    results.append((worker_id, i, success))
                    
                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)
                
                return results
            
            # Run multiple workers concurrently
            num_workers = 5
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(add_backup_worker, i) for i in range(num_workers)]
                
                all_results = []
                for future in as_completed(futures):
                    worker_results = future.result()
                    all_results.extend(worker_results)
            
            # Verify all operations succeeded
            successful_ops = [r for r in all_results if r[2]]
            failed_ops = [r for r in all_results if not r[2]]
            
            print(f"   Successful operations: {len(successful_ops)}")
            print(f"   Failed operations: {len(failed_ops)}")
            print(f"   Total backups in cache: {len(manager.backup_cache)}")
            print(f"   Memory usage: {manager.current_memory_mb:.2f}MB")
            
            # All operations should succeed (total 25 * 100KB = 2.5MB < 10MB)
            assert len(successful_ops) == 25, f"All 25 operations should succeed, got {len(successful_ops)}"
            assert len(failed_ops) == 0, "No operations should fail"
            assert len(manager.backup_cache) == 25, "Should have 25 backups in cache"
            
            print("✅ Concurrent backup additions work correctly")
    
    def test_concurrent_backup_access(self):
        """Test concurrent backup access and retrieval"""
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
            
            # Add some initial backups
            files = []
            for i in range(5):
                file_path = project_path / f"file_{i}.txt"
                content = f"x" * (200 * 1024)  # 200KB each
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                manager.add_backup(operation)
                files.append(file_path)
            
            def access_backup_worker(worker_id):
                """Worker function to access backups"""
                results = []
                for i in range(10):
                    file_idx = i % len(files)
                    backup = manager.get_backup(str(files[file_idx]))
                    
                    if backup:
                        results.append((worker_id, file_idx, True, len(backup.original_content)))
                    else:
                        results.append((worker_id, file_idx, False, 0))
                    
                    # Small delay
                    time.sleep(0.001)
                
                return results
            
            # Run multiple workers accessing backups
            num_workers = 3
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(access_backup_worker, i) for i in range(num_workers)]
                
                all_results = []
                for future in as_completed(futures):
                    worker_results = future.result()
                    all_results.extend(worker_results)
            
            # Analyze results
            successful_access = [r for r in all_results if r[2]]
            failed_access = [r for r in all_results if not r[2]]
            
            print(f"   Successful accesses: {len(successful_access)}")
            print(f"   Failed accesses: {len(failed_access)}")
            
            # Most accesses should succeed
            assert len(successful_access) > len(failed_access), "Most accesses should succeed"
            
            # Verify content sizes are correct
            for result in successful_access:
                _, _, _, content_size = result
                assert content_size == 200 * 1024, f"Content size should be 200KB, got {content_size}"
            
            print("✅ Concurrent backup access works correctly")
    
    def test_memory_pressure_under_concurrency(self):
        """Test memory management under concurrent pressure"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "3",  # 3MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            def add_backup_with_pressure(worker_id):
                """Worker function that adds backups under memory pressure"""
                results = []
                for i in range(8):  # Each worker tries to add 8 files
                    file_path = project_path / f"pressure_{worker_id}_{i}.txt"
                    content = "x" * (400 * 1024)  # 400KB each
                    
                    file_path.write_text(content)
                    
                    operation = EditOperation(
                        file_path=str(file_path),
                        original_content=content
                    )
                    
                    success = manager.add_backup(operation)
                    results.append((worker_id, i, success))
                    
                    # Small delay to increase concurrency
                    time.sleep(0.002)
                
                return results
            
            # Run multiple workers to create memory pressure
            num_workers = 4
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(add_backup_with_pressure, i) for i in range(num_workers)]
                
                all_results = []
                for future in as_completed(futures):
                    worker_results = future.result()
                    all_results.extend(worker_results)
            
            # Analyze results
            successful_ops = [r for r in all_results if r[2]]
            failed_ops = [r for r in all_results if not r[2]]
            
            print(f"   Successful operations: {len(successful_ops)}")
            print(f"   Failed operations: {len(failed_ops)}")
            print(f"   Final cache size: {len(manager.backup_cache)}")
            print(f"   Final memory usage: {manager.current_memory_mb:.2f}MB")
            print(f"   Memory limit: {manager.max_memory_mb}MB")
            
            # Memory usage should not exceed limit
            assert manager.current_memory_mb <= manager.max_memory_mb, "Memory usage should not exceed limit"
            
            # Cache size should be reasonable (at most memory limit / smallest file size)
            max_possible_files = manager.max_memory_mb / 0.4  # 400KB = 0.4MB
            assert len(manager.backup_cache) <= max_possible_files + 1, "Cache size should be reasonable"
            
            # Some operations should succeed, some might fail due to memory pressure
            assert len(successful_ops) > 0, "Some operations should succeed"
            
            print("✅ Memory pressure under concurrency handled correctly")
    
    def test_thread_safety_of_memory_manager(self):
        """Test thread safety of MemoryBackupManager operations"""
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
            
            # Shared set of files for all workers
            shared_files = []
            for i in range(10):
                file_path = project_path / f"shared_file_{i}.txt"
                content = f"x" * (100 * 1024)  # 100KB each
                file_path.write_text(content)
                shared_files.append(file_path)
            
            def mixed_operations_worker(worker_id):
                """Worker that performs mixed operations"""
                results = []
                
                for i in range(20):
                    file_idx = i % len(shared_files)
                    file_path = shared_files[file_idx]
                    
                    if i % 3 == 0:
                        # Add backup
                        content = file_path.read_text()
                        operation = EditOperation(
                            file_path=str(file_path),
                            original_content=content
                        )
                        success = manager.add_backup(operation)
                        results.append((worker_id, i, "add", success))
                    
                    elif i % 3 == 1:
                        # Get backup
                        backup = manager.get_backup(str(file_path))
                        success = backup is not None
                        results.append((worker_id, i, "get", success))
                    
                    else:
                        # Remove backup
                        success = manager.remove_backup(str(file_path))
                        results.append((worker_id, i, "remove", success))
                    
                    time.sleep(0.001)
                
                return results
            
            # Run multiple workers with mixed operations
            num_workers = 3
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(mixed_operations_worker, i) for i in range(num_workers)]
                
                all_results = []
                for future in as_completed(futures):
                    worker_results = future.result()
                    all_results.extend(worker_results)
            
            # Analyze results by operation type
            add_ops = [r for r in all_results if r[2] == "add"]
            get_ops = [r for r in all_results if r[2] == "get"]
            remove_ops = [r for r in all_results if r[2] == "remove"]
            
            successful_adds = sum(1 for r in add_ops if r[3])
            successful_gets = sum(1 for r in get_ops if r[3])
            successful_removes = sum(1 for r in remove_ops if r[3])
            
            print(f"   Add operations: {successful_adds}/{len(add_ops)} successful")
            print(f"   Get operations: {successful_gets}/{len(get_ops)} successful")
            print(f"   Remove operations: {successful_removes}/{len(remove_ops)} successful")
            print(f"   Final cache size: {len(manager.backup_cache)}")
            print(f"   Final memory usage: {manager.current_memory_mb:.2f}MB")
            
            # System should remain stable
            assert manager.current_memory_mb <= manager.max_memory_mb, "Memory usage should not exceed limit"
            assert len(manager.backup_cache) >= 0, "Cache size should be non-negative"
            
            # Most operations should succeed (some adds might fail due to duplicates, etc.)
            total_ops = len(all_results)
            successful_ops = successful_adds + successful_gets + successful_removes
            success_rate = successful_ops / total_ops
            
            assert success_rate > 0.5, f"Success rate should be > 50%, got {success_rate:.2%}"
            
            print("✅ Thread safety test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])