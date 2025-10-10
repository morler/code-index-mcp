"""Concurrent edit failure and rollback tests"""

import pytest
import tempfile
import os
import threading
import time
import random
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.code_index_mcp.core.edit_models import EditOperation, MemoryBackupManager, get_backup_manager
from src.code_index_mcp.core.backup import apply_edit_with_backup, get_backup_system, backup_file, restore_file


class TestConcurrentRollback:
    """Tests for concurrent edit operations with rollback"""
    
    @pytest.fixture
    def temp_files(self):
        """Create multiple temporary files for concurrent testing"""
        files = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'_test_{i}.py') as f:
                f.write(f"""# Test file {i}
def function_{i}():
    print("Function {i}")
    return {i}
""")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            if os.path.exists(file_path):
                os.unlink(file_path)
    
    @pytest.fixture
    def backup_manager(self):
        """Create a fresh backup manager for each test"""
        import src.code_index_mcp.core.edit_models as edit_models
        edit_models._global_backup_manager = None
        manager = get_backup_manager()
        manager.max_memory_mb = 20  # Larger limit for concurrent tests
        return manager
    
    def test_concurrent_edits_with_rollback(self, temp_files, backup_manager):
        """
        Test: Multiple threads editing different files with some failures and rollbacks
        """
        results = []
        errors = []
        file_states = {}
        
        # Record original file states
        for file_path in temp_files:
            file_states[file_path] = Path(file_path).read_text()
        
        def edit_file_worker(file_path, thread_id):
            try:
                # Create backup for this file
                backup_system = get_backup_system()
                operation_id = backup_system.backup_file(file_path)
                if operation_id is None:
                    raise Exception(f"Backup failed for {file_path}")
                
                # Simulate edit that may fail
                new_content = f"""# Modified by thread {thread_id}
def modified_function():
    print("Modified by thread {thread_id}")
    return {thread_id * 10}
"""
                
                # 30% chance of failure
                if random.random() < 0.3:
                    with patch('pathlib.Path.write_text', side_effect=IOError(f"Thread {thread_id} simulated error")):
                        success, error = apply_edit_with_backup(
                            file_path=file_path,
                            new_content=new_content
                        )
                        if not success:
                            errors.append((thread_id, file_path, error))
                        else:
                            results.append((thread_id, file_path, "success"))
                else:
                    # Successful edit
                    success, error = apply_edit_with_backup(
                        file_path=file_path,
                        new_content=new_content
                    )
                    if success:
                        results.append((thread_id, file_path, "success"))
                    else:
                        errors.append((thread_id, file_path, error))
                
            except Exception as e:
                errors.append((thread_id, file_path, str(e)))
        
        # Create threads for concurrent execution
        threads = []
        for i, file_path in enumerate(temp_files):
            # Multiple threads per file to increase contention
            for j in range(2):
                thread = threading.Thread(
                    target=edit_file_worker,
                    args=(file_path, f"{i}-{j}")
                )
                threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # Verify results
        total_operations = len(threads)
        successful_ops = len(results)
        failed_ops = len(errors)
        
        assert successful_ops + failed_ops == total_operations, "All operations should be accounted for"
        assert failed_ops > 0, "Some operations should have failed"
        assert successful_ops > 0, "Some operations should have succeeded"
        
        # Verify file integrity - no corruption
        for file_path in temp_files:
            current_content = Path(file_path).read_text()
            assert isinstance(current_content, str), f"File {file_path} should contain valid string"
            assert len(current_content) > 0, f"File {file_path} should not be empty"
            
            # Should contain either original or modified content, not garbage
            assert "def " in current_content, f"File {file_path} should contain function definition"
        
        # Performance check - should complete within reasonable time
        duration = end_time - start_time
        assert duration < 10.0, f"Concurrent operations should complete quickly, took {duration:.2f}s"
    
    def test_concurrent_same_file_rollback(self, temp_files, backup_manager):
        """
        Test: Multiple threads editing the same file with rollbacks
        """
        file_path = temp_files[0]
        original_content = Path(file_path).read_text()
        
        results = []
        errors = []
        
        def edit_same_file_worker(thread_id):
            try:
                new_content = f"""# Thread {thread_id} modification
def thread_function():
    print("From thread {thread_id}")
    return {thread_id}
"""
                
                # 50% chance of failure
                if random.random() < 0.5:
                    with patch('pathlib.Path.write_text', side_effect=IOError(f"Thread {thread_id} error")):
                        success, error = apply_edit_with_backup(
                            file_path=file_path,
                            new_content=new_content
                        )
                        if not success:
                            errors.append((thread_id, error))
                        else:
                            results.append(thread_id)
                else:
                    success, error = apply_edit_with_backup(
                        file_path=file_path,
                        new_content=new_content
                    )
                    if success:
                        results.append(thread_id)
                    else:
                        errors.append((thread_id, error))
                
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads for the same file
        threads = []
        for i in range(8):
            thread = threading.Thread(target=edit_same_file_worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify file integrity
        final_content = Path(file_path).read_text()
        assert isinstance(final_content, str), "File should contain valid string"
        assert "def " in final_content, "File should contain function definition"
        
        # Should not be corrupted
        assert len(final_content) > 10, "File should have substantial content"
        
        # Verify some operations failed and were rolled back
        assert len(errors) > 0, "Some operations should have failed"
        assert len(results) > 0, "Some operations should have succeeded"
    
    def test_concurrent_memory_pressure_rollback(self, backup_manager):
        """
        Test: Concurrent operations under memory pressure with rollbacks
        """
        # Reduce memory limits to increase pressure
        backup_manager.max_memory_mb = 5
        backup_manager.max_backups = 10
        
        temp_files = []
        try:
            # Create multiple files
            for i in range(8):
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'_pressure_{i}.txt') as f:
                    # Create files with significant content
                    content = f"Pressure test file {i}\n" + "Line content\n" * 100
                    f.write(content)
                    temp_files.append(f.name)
            
            results = []
            errors = []
            
            def memory_pressure_worker(file_path, thread_id):
                try:
                    # Create backup (may fail due to memory pressure)
                    backup_system = get_backup_system()
                    operation_id = backup_system.backup_file(file_path)
                    backup_success = operation_id is not None
                    
                    new_content = f"Modified by thread {thread_id} under memory pressure\n" + "New line\n" * 50
                    
                    # Simulate failure 40% of time
                    if random.random() < 0.4:
                        with patch('pathlib.Path.write_text', side_effect=MemoryError(f"Memory pressure in thread {thread_id}")):
                            success, error = apply_edit_with_backup(
                                file_path=file_path,
                                new_content=new_content
                            )
                            if not success:
                                errors.append((thread_id, error))
                            else:
                                results.append((thread_id, backup_success))
                    else:
                        success, error = apply_edit_with_backup(
                            file_path=file_path,
                            new_content=new_content
                        )
                        if success:
                            results.append((thread_id, backup_success))
                        else:
                            errors.append((thread_id, error))
                    
                except Exception as e:
                    errors.append((thread_id, str(e)))
            
            # Execute with thread pool
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for i, file_path in enumerate(temp_files):
                    future = executor.submit(memory_pressure_worker, file_path, i)
                    futures.append(future)
                
                # Wait for all to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass  # Errors captured in worker
            
            # Verify results
            assert len(results) + len(errors) == len(temp_files), "All operations should be accounted for"
            
            # Check memory usage
            memory_status = backup_manager.get_memory_usage()
            assert memory_status['current_memory_mb'] <= backup_manager.max_memory_mb * 1.1, "Memory usage should be within limits"
            
            # Verify file integrity
            for file_path in temp_files:
                if os.path.exists(file_path):
                    content = Path(file_path).read_text()
                    assert isinstance(content, str), f"File {file_path} should contain valid content"
                    assert len(content) > 0, f"File {file_path} should not be empty"
        
        finally:
            # Cleanup
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
    
    def test_concurrent_rollback_race_condition(self, temp_files, backup_manager):
        """
        Test: Race conditions during concurrent rollback operations
        """
        results = []
        errors = []
        
        def race_condition_worker(file_path, thread_id):
            try:
                # Create backup
                backup_system = get_backup_system()
                operation_id = backup_system.backup_file(file_path)
                backup_success = operation_id is not None
                
                # Simulate complex edit operation
                new_content = f"""# Race condition test - thread {thread_id}
import threading
import time

def race_function():
    print("Thread {thread_id} executing")
    time.sleep(0.001)  # Simulate work
    return {thread_id}
"""
                
                # Introduce timing variations
                time.sleep(random.uniform(0.001, 0.005))
                
                # 60% chance of failure to increase rollback scenarios
                if random.random() < 0.6:
                    error_msg = f"Race condition error in thread {thread_id}"
                    with patch('pathlib.Path.write_text', side_effect=RuntimeError(error_msg)):
                        success, error = apply_edit_with_backup(
                            file_path=file_path,
                            new_content=new_content
                        )
                        if not success:
                            errors.append((thread_id, file_path, error))
                        else:
                            results.append((thread_id, file_path, backup_success))
                else:
                    success, error = apply_edit_with_backup(
                        file_path=file_path,
                        new_content=new_content
                    )
                    if success:
                        results.append((thread_id, file_path, backup_success))
                    else:
                        errors.append((thread_id, file_path, error))
                
            except Exception as e:
                errors.append((thread_id, file_path, str(e)))
        
        # Create many threads to increase race condition likelihood
        threads = []
        for i in range(15):
            file_path = temp_files[i % len(temp_files)]
            thread = threading.Thread(target=race_condition_worker, args=(file_path, i))
            threads.append(thread)
        
        # Start threads rapidly to increase contention
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no deadlocks occurred
        assert len(results) + len(errors) == len(threads), "All threads should complete"
        
        # Verify file integrity - no corruption from race conditions
        for file_path in temp_files:
            content = Path(file_path).read_text()
            assert isinstance(content, str), f"File {file_path} should be valid string"
            assert "def " in content or "import" in content, f"File {file_path} should contain valid code"
            
            # Should not contain partial writes or corruption
            assert not content.startswith("def race_function"), "File should not contain partially written content"
    
    def test_concurrent_rollback_stress_test(self, backup_manager):
        """
        Test: Stress test with high concurrency and frequent rollbacks
        """
        # Create many temporary files
        temp_files = []
        try:
            for i in range(10):
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'_stress_{i}.py') as f:
                    f.write(f"""# Stress test file {i}
def stress_function_{i}():
    return {i}
""")
                    temp_files.append(f.name)
            
            results = []
            errors = []
            start_time = time.time()
            
            def stress_worker(thread_id):
                try:
                    file_path = temp_files[thread_id % len(temp_files)]
                    
                    # Create backup
                    backup_system = get_backup_system()
                    operation_id = backup_system.backup_file(file_path)
                    
                    # High failure rate (80%) to stress rollback mechanism
                    new_content = f"# Stress thread {thread_id}\ndef stress_{thread_id}():\n    return {thread_id}\n"
                    
                    if random.random() < 0.8:
                        with patch('pathlib.Path.write_text', side_effect=Exception(f"Stress failure {thread_id}")):
                            success, error = apply_edit_with_backup(
                                file_path=file_path,
                                new_content=new_content
                            )
                            if not success:
                                errors.append(thread_id)
                            else:
                                results.append(thread_id)
                    else:
                        success, error = apply_edit_with_backup(
                            file_path=file_path,
                            new_content=new_content
                        )
                        if success:
                            results.append(thread_id)
                        else:
                            errors.append(thread_id)
                    
                except Exception:
                    errors.append(thread_id)
            
            # High concurrency stress test
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for i in range(50):  # 50 concurrent operations
                    future = executor.submit(stress_worker, i)
                    futures.append(future)
                
                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify stress test results
            assert len(results) + len(errors) == 50, "All operations should complete"
            assert duration < 15.0, f"Stress test should complete in reasonable time, took {duration:.2f}s"
            
            # Verify system stability
            memory_status = backup_manager.get_memory_usage()
            assert memory_status['current_memory_mb'] < backup_manager.max_memory_mb * 2, "Memory usage should not blow up"
            
            # Verify no file corruption
            for file_path in temp_files:
                if os.path.exists(file_path):
                    content = Path(file_path).read_text()
                    assert isinstance(content, str), "All files should remain valid"
                    assert len(content) > 0, "No files should be empty"
        
        finally:
            for file_path in temp_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)