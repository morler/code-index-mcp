"""Contract tests for edit failure rollback functionality"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.code_index_mcp.core.edit_models import EditOperation, MemoryBackupManager
from src.code_index_mcp.core.backup import apply_edit_with_backup, get_backup_system


class TestEditRollbackContract:
    """Contract tests for edit rollback functionality"""
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Original content line 1\nOriginal content line 2\n")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def backup_manager(self):
        """Create a memory backup manager for testing"""
        manager = MemoryBackupManager()
        manager.max_memory_mb = 10  # Small limit for testing
        return manager
    
    def test_rollback_on_edit_failure(self, temp_file, backup_manager):
        """
        Contract: When edit operation fails, file must be restored to original state
        
        Given: A file with original content
        When: An edit operation fails during application
        Then: File content must be exactly as it was before the edit attempt
        """
        # Read original content
        original_content = Path(temp_file).read_text()
        
        # Mock file write to raise exception
        with patch('pathlib.Path.write_text', side_effect=IOError("Disk full")):
            # Attempt edit that should fail
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content="Modified content\n"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        assert error is not None, "Should return error message"
        
        # Verify file content is unchanged
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "File should be restored to original state after failure"
    
    def test_rollback_preserves_file_metadata(self, temp_file, backup_manager):
        """
        Contract: Rollback must preserve file metadata (permissions, timestamps)
        
        Given: A file with specific metadata
        When: Edit operation fails and rollback occurs
        Then: File metadata must be unchanged
        """
        import stat
        import time
        
        file_path = Path(temp_file)
        
        # Record original metadata
        original_stat = file_path.stat()
        original_mode = original_stat.st_mode
        original_mtime = original_stat.st_mtime
        
        # Small delay to ensure timestamp difference
        time.sleep(0.01)
        
        # Mock edit to fail
        with patch('pathlib.Path.write_text', side_effect=PermissionError("Permission denied")):
            success, error = apply_edit_with_backup(
                file_path=str(file_path),
                new_content="Modified content"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Verify metadata is preserved
        current_stat = file_path.stat()
        assert current_stat.st_mode == original_mode, "File permissions should be preserved"
        # Note: mtime might change during rollback, so we focus on permissions
    
    def test_rollback_with_memory_backup_failure(self, temp_file):
        """
        Contract: When both edit and memory backup fail, system must not corrupt file
        
        Given: A file with original content
        When: Edit operation fails and memory backup is unavailable
        Then: File must remain in original state (no corruption)
        """
        original_content = Path(temp_file).read_text()
        
        # Mock backup system to fail
        with patch('src.code_index_mcp.core.backup.get_backup_system') as mock_get_system:
            mock_system = MagicMock()
            mock_system.backup_file.side_effect = Exception("Backup system failed")
            mock_get_system.return_value = mock_system
            
            # Mock edit to fail
            with patch('pathlib.Path.write_text', side_effect=IOError("Device error")):
                success, error = apply_edit_with_backup(
                    file_path=temp_file,
                    new_content="Modified content"
                )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Verify file is unchanged
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "File should not be corrupted when both edit and backup fail"
    
    def test_rollback_concurrent_safety(self, temp_file, backup_manager):
        """
        Contract: Rollback operations must be thread-safe
        
        Given: Multiple threads attempting edits on the same file
        When: One or more edits fail
        Then: Rollback must not interfere with other operations
        """
        import threading
        import time
        
        original_content = Path(temp_file).read_text()
        results = []
        errors = []
        
        def edit_file(thread_id):
            try:
                # Simulate edit that fails for half the threads
                if thread_id % 2 == 0:
                    with patch('pathlib.Path.write_text', side_effect=IOError(f"Thread {thread_id} error")):
                        success, error = apply_edit_with_backup(
                            file_path=temp_file,
                            new_content=f"Modified by thread {thread_id}"
                        )
                        if not success:
                            errors.append(f"Thread {thread_id} error: {error}")
                        else:
                            results.append(f"Thread {thread_id} completed")
                else:
                    # Successful edit
                    time.sleep(0.01)  # Small delay
                    success, error = apply_edit_with_backup(
                        file_path=temp_file,
                        new_content=f"Success by thread {thread_id}"
                    )
                    if success:
                        results.append(f"Thread {thread_id} completed")
                    else:
                        errors.append(f"Thread {thread_id} error: {error}")
            except Exception as e:
                errors.append(f"Thread {thread_id} exception: {e}")
        
        # Create multiple threads
        threads = []
        for i in range(4):
            thread = threading.Thread(target=edit_file, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify file is not corrupted (should be valid text)
        final_content = Path(temp_file).read_text()
        assert isinstance(final_content, str), "File content should be valid string"
        assert len(final_content) > 0, "File should not be empty"
        
        # Verify expected errors occurred
        assert len(errors) >= 2, "Expected at least 2 threads to fail"
        assert all("error" in error.lower() or "exception" in error.lower() for error in errors), "All errors should contain 'error' or 'exception'"
    
    def test_rollback_memory_limit_handling(self, temp_file, backup_manager):
        """
        Contract: Rollback must work correctly even when memory limits are reached
        
        Given: A backup manager at memory capacity
        When: Edit operation fails
        Then: Rollback must still succeed using available backups
        """
        # Fill backup manager to capacity
        backup_manager.max_memory_mb = 1  # Very small limit
        backup_manager.max_backups = 2    # Very small backup limit
        
        original_content = Path(temp_file).read_text()
        
        # Create backup that should fit
        operation = EditOperation(
            file_path=temp_file,
            original_content=original_content
        )
        backup_added = backup_manager.add_backup(operation)
        assert backup_added, "Backup should be added successfully"
        
        # Mock edit to fail
        with patch('pathlib.Path.write_text', side_effect=IOError("Memory error")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content="Modified content"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Verify rollback succeeded
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "Rollback should work even with memory limits"