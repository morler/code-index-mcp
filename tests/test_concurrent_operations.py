#!/usr/bin/env python3
"""Test concurrent file operations with memory backup"""

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
from code_index_mcp.core.backup import get_backup_system
from code_index_mcp.server_unified import apply_edit
from code_index_mcp.config import reset_config
import pytest


class TestConcurrentOperations:
    """Test concurrent file operations"""
    
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
    
    def test_concurrent_file_edits(self):
        """Test concurrent file edits through apply_edit"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "10",  # 10MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create initial files
            files = []
            for i in range(10):
                file_path = project_path / f"file_{i}.txt"
                content = f"Initial content {i}\n"
                file_path.write_text(content)
                files.append(file_path)
            
            def edit_file_worker(worker_id, file_index):
                """Worker function to edit files"""
                file_path = files[file_index]
                
                # Read current content
                current_content = file_path.read_text()
                
                # Add worker-specific edit
                new_content = current_content + f"Edit by worker {worker_id} at {time.time()}\n"
                
                try:
                    success, error = apply_edit(
                        file_path=str(file_path),
                        new_content=new_content,
                        expected_old_content=current_content
                    )
                    return (worker_id, file_index, success, error)
                except Exception as e:
                    return (worker_id, file_index, False, str(e))
            
            # Run concurrent edits on different files
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i in range(10):
                    future = executor.submit(edit_file_worker, i, i)
                    futures.append(future)
                
                results = []
                for future in as_completed(futures):
                    results.append(future.result())
            
            # Analyze results
            successful_edits = [r for r in results if r[2]]
            failed_edits = [r for r in results if not r[2]]
            
            print(f"   Successful edits: {len(successful_edits)}")
            print(f"   Failed edits: {len(failed_edits)}")
            # Print error details for debugging
            for result in failed_edits:
                worker_id, file_index, success, error = result
                print(f"   Worker {worker_id}, File {file_index}: {error}")
            
            # All edits should succeed since they're on different files
            assert len(successful_edits) == 10, f"All 10 edits should succeed, got {len(successful_edits)}"
            assert len(failed_edits) == 0, "No edits should fail"
            
            # Verify file contents
            for i, file_path in enumerate(files):
                content = file_path.read_text()
                assert f"Edit by worker {i}" in content, f"File {i} should contain edit by worker {i}"
            
            print("✅ Concurrent file edits work correctly")
    
    def test_concurrent_same_file_edits(self):
        """Test concurrent edits on the same file (should be serialized by file locking)"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "10",  # 10MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create a single file
            file_path = project_path / "shared_file.txt"
            initial_content = "Initial content\n"
            file_path.write_text(initial_content)
            
            def edit_shared_file_worker(worker_id):
                """Worker function to edit the same file"""
                max_attempts = 10
                for attempt in range(max_attempts):
                    try:
                        # Read current content
                        current_content = file_path.read_text()
                        
                        # Add worker-specific edit
                        new_content = current_content + f"Edit by worker {worker_id} (attempt {attempt})\n"
                        
                        success, error = apply_edit(
                            file_path=str(file_path),
                            new_content=new_content,
                            expected_old_content=current_content
                        )
                        
                        if success:
                            return (worker_id, attempt, True, None)
                        else:
                            # If failed due to race condition, wait and retry
                            time.sleep(0.01)
                            continue
                            
                    except Exception as e:
                        return (worker_id, attempt, False, str(e))
                
                return (worker_id, max_attempts, False, "Max attempts exceeded")
            
            # Run multiple workers trying to edit the same file
            num_workers = 5
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(edit_shared_file_worker, i) for i in range(num_workers)]
                
                results = []
                for future in as_completed(futures):
                    results.append(future.result())
            
            # Analyze results
            successful_edits = [r for r in results if r[2]]
            failed_edits = [r for r in results if not r[2]]
            
            print(f"   Successful edits: {len(successful_edits)}")
            print(f"   Failed edits: {len(failed_edits)}")
            # Print error details for debugging
            for result in failed_edits:
                worker_id, file_index, success, error = result
                print(f"   Worker {worker_id}, File {file_index}: {error}")
            
            # At least some edits should succeed
            assert len(successful_edits) > 0, "At least some edits should succeed"
            
            # Verify file integrity - content should be consistent
            final_content = file_path.read_text()
            lines = final_content.strip().split('\n')
            
            # Should have initial line plus at least one successful edit
            assert len(lines) >= 2, f"File should have at least 2 lines, got {len(lines)}"
            assert lines[0] == "Initial content", "First line should be unchanged"
            
            # Count successful edits in content
            edit_count = sum(1 for line in lines if "Edit by worker" in line)
            assert edit_count == len(successful_edits), f"Content should have {len(successful_edits)} edits, got {edit_count}"
            
            print(f"✅ Concurrent same-file edits handled correctly ({len(successful_edits)} successful)")
    
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])