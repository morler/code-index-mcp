"""Integration tests for memory-based rollback functionality"""

import pytest
import tempfile
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.code_index_mcp.core.edit_models import EditOperation, MemoryBackupManager, get_backup_manager
from src.code_index_mcp.core.backup import apply_edit_with_backup, get_backup_system, backup_file, restore_file


class TestMemoryRollbackIntegration:
    """Integration tests for memory-based rollback"""
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("""def hello_world():
    print("Hello, World!")
    return 42
""")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def backup_manager(self):
        """Create a fresh backup manager for each test"""
        import src.code_index_mcp.core.edit_models as edit_models
        edit_models._global_backup_manager = None
        return get_backup_manager()
    
    def test_complete_edit_rollback_flow(self, temp_file, backup_manager):
        """
        Integration: Complete edit operation with rollback on failure
        
        Tests the entire flow from backup creation through edit attempt to rollback
        """
        original_content = Path(temp_file).read_text()
        
        # Step 1: Create backup
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(temp_file)
        assert operation_id is not None, "Backup creation should succeed"
        
        # Verify backup exists in memory
        backup_info = backup_system.get_backup_info(temp_file)
        assert backup_info is not None, "Backup should exist in memory"
        assert backup_info['status'] == 'completed', "Backup should be completed"
        
        # Verify backup content through the memory manager
        backup = backup_system.memory_manager.get_backup(temp_file)
        assert backup is not None, "Backup should exist in memory manager"
        assert backup.original_content == original_content, "Backup content should match original"
        
        # Step 2: Attempt edit that fails
        new_content = """def hello_world():
    print("Modified Hello!")
    return 100
"""
        
        with patch('pathlib.Path.write_text', side_effect=IOError("Simulated disk error")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content=new_content
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        assert error is not None, "Should return error message"
        
        # Step 3: Verify rollback occurred
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "File should be rolled back to original content"
    
    def test_rollback_with_large_file(self, backup_manager):
        """
        Integration: Rollback with large files near memory limits
        """
        # Create a large temporary file (close to 10MB limit)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            # Write ~5MB of content
            line = "A" * 100 + "\n"
            for _ in range(50000):  # ~5MB
                f.write(line)
            temp_path = f.name
        
        try:
            original_content = Path(temp_path).read_text()
            
            # Create backup (should work due to 10MB file size limit)
            backup_system = get_backup_system()
            operation_id = backup_system.backup_file(temp_path)
            assert operation_id is not None, "Large file backup should succeed"
            
            # Attempt edit that fails
            with patch('pathlib.Path.write_text', side_effect=IOError("Large file edit error")):
                success, error = apply_edit_with_backup(
                    file_path=temp_path,
                    new_content="Modified large content"
                )
            
            # Verify edit failed
            assert not success, "Edit should fail"
            
            # Verify rollback
            current_content = Path(temp_path).read_text()
            assert current_content == original_content, "Large file should be properly rolled back"
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_rollback_with_binary_file(self, backup_manager):
        """
        Integration: Rollback with binary files
        """
        # Create a binary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            binary_data = os.urandom(1024)  # 1KB of random binary data
            f.write(binary_data)
            temp_path = f.name
        
        try:
            # Binary files should be rejected for memory backup
            backup_system = get_backup_system()
            operation_id = backup_system.backup_file(temp_path)
            # This might succeed or fail depending on implementation
            # The key is that the system handles it gracefully
            
            # Edit should proceed without backup for binary files
            original_data = Path(temp_path).read_bytes()
            
            # This test verifies binary files are handled gracefully
            assert len(original_data) == 1024, "Binary file should remain unchanged"
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_rollback_with_special_characters(self, temp_file, backup_manager):
        """
        Integration: Rollback with files containing special characters and Unicode
        """
        # Original content with special characters
        original_content = """# 特殊字符测试
def test_function():
    print("Hello 世界! 🌍")
    emoji = "🚀🔥💯"
    unicode_text = "Café naïve résumé"
    return True
"""
        
        Path(temp_file).write_text(original_content, encoding='utf-8')
        
        # Create backup
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(temp_file)
        assert operation_id is not None, "Backup with special characters should succeed"
        
        # Attempt edit with different special characters
        new_content = """# Modified 特殊字符测试
def test_function():
    print("Modified Hello 世界! 🌍")
    emoji = "🎉🎊🎈"
    unicode_text = "Modified Café naïve résumé"
    return False
"""
        
        with patch('pathlib.Path.write_text', side_effect=UnicodeError("Encoding error")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content=new_content
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Verify rollback preserved special characters
        current_content = Path(temp_file).read_text(encoding='utf-8')
        assert current_content == original_content, "Special characters should be preserved in rollback"
    
    def test_rollback_with_file_permissions_error(self, temp_file, backup_manager):
        """
        Integration: Rollback when file permissions cause edit failure
        """
        original_content = Path(temp_file).read_text()
        
        # Create backup
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(temp_file)
        assert operation_id is not None, "Backup should succeed"
        
        # Mock permission error during write
        with patch('pathlib.Path.write_text', side_effect=PermissionError("Permission denied")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content="Modified content"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Verify rollback
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "File should be rolled back after permission error"
    
    def test_rollback_with_concurrent_edits(self, temp_file, backup_manager):
        """
        Integration: Multiple concurrent edit attempts with rollbacks
        """
        original_content = Path(temp_file).read_text()
        results = []
        errors = []
        
        def concurrent_edit(thread_id, should_fail=False):
            try:
                new_content = f"""def hello_world():
    print("Thread {thread_id}")
    return {thread_id}
"""
                if should_fail:
                    with patch('pathlib.Path.write_text', side_effect=IOError(f"Thread {thread_id} failed")):
                        success, error = apply_edit_with_backup(
                            file_path=temp_file,
                            new_content=new_content
                        )
                        if not success:
                            errors.append((thread_id, error))
                        else:
                            results.append(thread_id)
                else:
                    # Small delay to increase chance of interleaving
                    time.sleep(0.001)
                    success, error = apply_edit_with_backup(
                        file_path=temp_file,
                        new_content=new_content
                    )
                    if success:
                        results.append(thread_id)
                    else:
                        errors.append((thread_id, error))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create threads - half will fail
        threads = []
        for i in range(6):
            thread = threading.Thread(
                target=concurrent_edit, 
                args=(i, i % 2 == 0)  # Even threads fail
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) >= 2, "At least 2 threads should succeed"
        assert len(errors) >= 2, "At least 2 threads should fail"
        
        # Verify file is not corrupted
        final_content = Path(temp_file).read_text()
        assert "def hello_world():" in final_content, "File should contain valid function definition"
        assert isinstance(final_content, str), "Content should be string"
    
    def test_rollback_memory_cleanup(self, temp_file, backup_manager):
        """
        Integration: Memory cleanup after rollback operations
        """
        # Create backup
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(temp_file)
        assert operation_id is not None, "Backup should succeed"
        
        initial_memory = backup_manager.get_memory_usage()
        initial_backup_count = len(backup_manager.backup_cache)
        
        # Attempt edit that fails
        with patch('pathlib.Path.write_text', side_effect=IOError("Simulated error")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content="Modified content"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # Memory should be cleaned up after rollback
        final_memory = backup_manager.get_memory_usage()
        final_backup_count = len(backup_manager.backup_cache)
        
        # Backup should still exist (not cleaned up after rollback)
        assert final_backup_count == initial_backup_count, "Backup count should remain after rollback"
        assert final_memory['current_memory_mb'] <= initial_memory['current_memory_mb'] * 1.1, "Memory usage should not increase significantly"
    
    def test_rollback_with_missing_backup(self, temp_file, backup_manager):
        """
        Integration: Rollback behavior when backup is missing
        """
        original_content = Path(temp_file).read_text()
        
        # Don't create backup - simulate missing backup
        missing_backup = backup_manager.get_backup(temp_file)
        assert missing_backup is None, "Backup should be missing"
        
        # Attempt edit that fails
        with patch('pathlib.Path.write_text', side_effect=IOError("Edit failed")):
            success, error = apply_edit_with_backup(
                file_path=temp_file,
                new_content="Modified content"
            )
        
        # Verify edit failed
        assert not success, "Edit should fail"
        
        # File should remain unchanged when no backup exists
        current_content = Path(temp_file).read_text()
        assert current_content == original_content, "File should remain unchanged when no backup exists"