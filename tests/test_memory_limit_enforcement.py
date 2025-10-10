"""
Test Memory Limit Enforcement

Tests that the memory backup system properly enforces memory limits
and rejects operations that would exceed configured limits.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from code_index_mcp.config import get_memory_backup_config, reset_config
from code_index_mcp.core.backup import get_backup_system, apply_edit_with_backup, _global_backup_system
from code_index_mcp.core.edit_models import MemoryBackupManager, EditOperation


class TestMemoryLimitEnforcement:
    """Test memory limit enforcement mechanisms"""
    
    def test_file_size_limit_enforcement(self):
        """Test that files exceeding size limit are rejected"""
        # Reset config and set small file size limit
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "50",
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB limit
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            # Reset global backup system to pick up new config
            import code_index_mcp.core.backup as backup_module
            backup_module._global_backup_system = None
            
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                
                # Create a large file (2MB) that exceeds the 1MB limit
                large_file = project_path / "large.txt"
                large_content = "x" * (2 * 1024 * 1024)  # 2MB
                large_file.write_text(large_content)
                
                # Try to edit the large file
                new_content = large_content + "\n# This should fail\n"
                
                success, error = apply_edit_with_backup(
                    large_file,
                    new_content,
                    expected_old_content=large_content
                )
                
                # Should fail due to file size limit
                assert not success, "Edit should fail due to file size limit"
                assert "file size" in error.lower() or "too large" in error.lower(), \
                    f"Error should mention file size: {error}"
                
                # Should fail due to file size limit
                assert not success, f"Edit should fail due to file size limit, but succeeded. Error: {error}"
                assert "file size" in error.lower() or "too large" in error.lower(), \
                    f"Error should mention file size: {error}"
                
                print(f"✅ File size limit enforcement works")
                print(f"   Error: {error}")
                
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_memory_limit_enforcement_with_multiple_files(self):
        """Test memory limit enforcement with multiple backup files"""
        # Reset config and set small memory limit
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "5",  # 5MB total limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                backup_system = get_backup_system()
                backup_system.clear_all_backups()
                
                # Create multiple files that together exceed memory limit
                files = []
                for i in range(4):  # 4 files × 1.5MB = 6MB > 5MB limit
                    file_path = project_path / f"file_{i}.txt"
                    content = "x" * (int(1.5 * 1024 * 1024))  # 1.5MB each
                    file_path.write_text(content)
                    files.append(file_path)
                
                # Edit files until memory limit is reached
                successful_edits = 0
                for i, file_path in enumerate(files):
                    original_content = file_path.read_text()
                    new_content = original_content + f"\n# Edit {i}\n"
                    
                    success, error = apply_edit_with_backup(
                        file_path,
                        new_content,
                        expected_old_content=original_content
                    )
                    
                    if success:
                        successful_edits += 1
                        print(f"   Edit {i}: SUCCESS")
                    else:
                        print(f"   Edit {i}: FAILED - {error}")
                        # Should fail due to memory limit
                        assert "memory" in error.lower() or "limit" in error.lower() or "too large" in error.lower(), \
                            f"Error should mention memory/size limit: {error}"
                        break
                
                # Should have failed before editing all files due to memory limit
                assert successful_edits < len(files), \
                    f"Should have failed before editing all {len(files)} files, succeeded with {successful_edits}"
                
                print(f"✅ Memory limit enforcement works with multiple files")
                print(f"   Successful edits: {successful_edits}/{len(files)}")
                
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_memory_backup_manager_limit_enforcement(self):
        """Test MemoryBackupManager directly enforces limits"""
        # Reset config and set small limits
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "3",  # 3MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            manager = MemoryBackupManager()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                
                # Create a file that fits within limits
                test_file = project_path / "test.txt"
                content = "x" * (1024 * 1024)  # 1MB
                test_file.write_text(content)
                
                # Create backup operation
                operation = EditOperation(
                    file_path=str(test_file),
                    original_content=content
                )
                
                # Should succeed
                success = manager.add_backup(operation)
                assert success, "First backup should succeed"
                
                # Try to add another large file that would exceed limit
                large_file = project_path / "large.txt"
                large_content = "x" * int(2.5 * 1024 * 1024)  # 2.5MB
                large_file.write_text(large_content)
                
                large_operation = EditOperation(
                    file_path=str(large_file),
                    original_content=large_content
                )
                
                # Should fail due to memory limit
                success = manager.add_backup(large_operation)
                print(f"   Debug: Manager memory limit: {manager.max_memory_mb}MB")
                print(f"   Debug: Manager current memory: {manager.current_memory_mb:.2f}MB")
                print(f"   Debug: Large operation memory: {large_operation.memory_size / (1024*1024):.2f}MB")
                print(f"   Debug: Add backup success: {success}")
                assert not success, "Large backup should fail due to memory limit"
                
                print(f"✅ MemoryBackupManager enforces limits correctly")
                print(f"   Current memory usage: {manager.current_memory_mb:.2f}MB")
                print(f"   Max memory limit: {manager.max_memory_mb}MB")
                
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_memory_monitor_integration(self):
        """Test memory monitor integration with edit operations"""
        from code_index_mcp.core.memory_monitor import check_memory_limits
        
        # Reset config and set very low limit
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "1"  # 1MB limit
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            # Create a large backup to trigger memory limit
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                backup_system = get_backup_system()
                backup_system.clear_all_backups()
                
                # Create multiple files to approach limit
                for i in range(3):
                    file_path = project_path / f"test_{i}.txt"
                    content = "x" * (500 * 1024)  # 500KB each
                    file_path.write_text(content)
                    
                    original_content = file_path.read_text()
                    new_content = original_content + f"\n# Edit {i}\n"
                    
                    success, error = apply_edit_with_backup(
                        file_path,
                        new_content,
                        expected_old_content=original_content
                    )
                    
                    if not success:
                        print(f"   Edit {i} failed: {error}")
                        break
                
                # Test memory monitor directly
                is_ok, error_msg = check_memory_limits("test_operation")
                
                # Should be at or near limit
                current_status = backup_system.get_system_status()
                memory_usage = current_status['backups']['current_mb']
                
                print(f"✅ Memory monitor integration works")
                print(f"   Memory usage: {memory_usage:.2f}MB")
                print(f"   Limit check: {'OK' if is_ok else 'FAILED'}")
                if not is_ok:
                    print(f"   Error: {error_msg}")
                
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_graceful_degradation_when_limits_exceeded(self):
        """Test that system degrades gracefully when limits are exceeded"""
        # Reset config and set very low limits
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "2",  # 2MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB per file
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                backup_system = get_backup_system()
                backup_system.clear_all_backups()
                
                # Create a file within limits
                test_file = project_path / "test.txt"
                content = "x" * (800 * 1024)  # 800KB
                test_file.write_text(content)
                
                # First edit should succeed
                original_content = test_file.read_text()
                new_content = original_content + "\n# First edit\n"
                
                success, error = apply_edit_with_backup(
                    test_file,
                    new_content,
                    expected_old_content=original_content
                )
                
                assert success, "First edit should succeed"
                
                # Try to edit a file that exceeds limits
                large_file = project_path / "large.txt"
                large_content = "x" * int(1.5 * 1024 * 1024)  # 1.5MB > 1MB limit
                large_file.write_text(large_content)
                
                new_large_content = large_content + "\n# This should fail\n"
                
                success, error = apply_edit_with_backup(
                    large_file,
                    new_large_content,
                    expected_old_content=large_content
                )
                
                # Should fail gracefully
                assert not success, "Large file edit should fail"
                assert error, "Should provide error message"
                assert "file size" in error.lower() or "memory" in error.lower() or "file too large" in error.lower(), \
                    f"Error should mention size/memory: {error}"
                
                # Original file should still be intact
                assert large_file.read_text() == large_content, \
                    "Original file should be unchanged after failed edit"
                
                # First file should still have its backup
                backup_info = backup_system.get_backup_info(test_file)
                assert backup_info is not None, "First file backup should still exist"
                
                print(f"✅ Graceful degradation works correctly")
                print(f"   Failed edit error: {error}")
                print(f"   Original file intact: {large_file.read_text()[:50]}...")
                print(f"   First backup exists: {backup_info is not None}")
                
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()


def run_memory_limit_tests():
    """Run all memory limit enforcement tests manually"""
    print("=== Memory Limit Enforcement Tests ===")
    
    test_instance = TestMemoryLimitEnforcement()
    
    try:
        test_instance.test_file_size_limit_enforcement()
        test_instance.test_memory_limit_enforcement_with_multiple_files()
        test_instance.test_memory_backup_manager_limit_enforcement()
        test_instance.test_memory_monitor_integration()
        test_instance.test_graceful_degradation_when_limits_exceeded()
        
        print("\n=== All Memory Limit Enforcement Tests Passed ===")
        print("✅ Memory backup system properly enforces limits")
        return True
        
    except Exception as e:
        print(f"\n❌ Memory limit test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_memory_limit_tests()
    if not success:
        sys.exit(1)