"""
Integration Test: Verify Memory Backup Usage

Tests that the main edit functions are using memory backup system.
Following Linus's principle: "Show me the code that proves it works."
"""

import os
import sys
import tempfile
import time
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from code_index_mcp.core.backup import get_backup_system
from code_index_mcp.core.edit_operations import edit_file_atomic


class TestMemoryBackupUsage:
    """Test that main edit functions use memory backup"""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path
    
    def test_edit_file_atomic_uses_memory_backup(self, temp_project):
        """Test that edit_file_atomic uses memory backup system"""
        # Clear backup system
        backup_system = get_backup_system()
        backup_system.clear_all_backups()
        
        # Create test file
        file_path = temp_project / "test_memory_usage.txt"
        original_content = "Original content for memory backup test"
        file_path.write_text(original_content)
        
        # Edit file using main interface
        new_content = "Modified content for memory backup test"
        success, error = edit_file_atomic(
            str(file_path),
            original_content,
            new_content
        )
        
        # Verify edit succeeded
        assert success, f"Edit should succeed: {error}"
        assert file_path.read_text() == new_content, "File should be modified"
        
        # Verify memory backup was created
        backup_info = backup_system.get_backup_info(file_path)
        assert backup_info is not None, "Memory backup should exist"
        assert backup_info['status'] == 'completed', "Backup should be completed"
        assert backup_info['file_path'] == str(file_path.absolute()), "Backup should be for correct file"
        
        # Verify rollback works
        restored = backup_system.restore_file(file_path)
        assert restored, "Rollback should succeed"
        assert file_path.read_text() == original_content, "File should be restored"
        
        print(f"✅ edit_file_atomic uses memory backup system")
        print(f"   Memory backup ID: {backup_info['operation_id']}")
        print(f"   File path: {backup_info['file_path']}")
        print(f"   Status: {backup_info['status']}")
    
    def test_no_disk_backups_created(self, temp_project):
        """Test that no disk backup files are created during editing"""
        # Clear backup system
        backup_system = get_backup_system()
        backup_system.clear_all_backups()
        
        # Create test file
        file_path = temp_project / "no_disk_backup.txt"
        original_content = "Original content"
        file_path.write_text(original_content)
        
        # Find any existing backup files before edit
        backup_patterns = [
            "**/*.bak",
            "**/*.backup", 
            "**/.edit_backup/**",
            "**/*~",
            "**/*.tmp"
        ]
        
        existing_backups = []
        for pattern in backup_patterns:
            existing_backups.extend(temp_project.glob(pattern))
        
        # Edit file
        new_content = "Modified content"
        success, error = edit_file_atomic(
            str(file_path),
            original_content,
            new_content
        )
        
        # Find backup files after edit
        new_backups = []
        for pattern in backup_patterns:
            new_backups.extend(temp_project.glob(pattern))
        
        # Verify edit succeeded and no disk backups created
        assert success, f"Edit should succeed: {error}"
        assert len(new_backups) == len(existing_backups), "No new disk backup files should be created"
        
        # Verify memory backup exists instead
        backup_info = backup_system.get_backup_info(file_path)
        assert backup_info is not None, "Memory backup should exist instead of disk backup"
        
        print(f"✅ No disk backup files created during editing")
        print(f"   Memory backup ID: {backup_info['operation_id']}")
        print(f"   Disk backup files before: {len(existing_backups)}")
        print(f"   Disk backup files after: {len(new_backups)}")
    
    def test_memory_backup_system_status(self, temp_project):
        """Test memory backup system status tracking"""
        # Clear backup system
        backup_system = get_backup_system()
        backup_system.clear_all_backups()
        
        # Get initial status
        initial_status = backup_system.get_system_status()
        initial_backup_count = initial_status['backups']['backup_count']
        
        # Create and edit multiple files
        files = []
        for i in range(3):
            file_path = temp_project / f"status_test_{i}.txt"
            content = f"Content for file {i}"
            file_path.write_text(content)
            files.append(file_path)
            
            # Edit file
            new_content = content + f"\n# Modified {i}"
            success, error = edit_file_atomic(
                str(file_path),
                content,
                new_content
            )
            
            assert success, f"Edit {i} should succeed: {error}"
        
        # Get final status
        final_status = backup_system.get_system_status()
        final_backup_count = final_status['backups']['backup_count']
        
        # Verify status tracking
        assert final_backup_count == initial_backup_count + 3, "Should have 3 new backups"
        assert final_status['backups']['current_mb'] > 0, "Should use memory for backups"
        
        print(f"✅ Memory backup system tracks status correctly")
        print(f"   Initial backup count: {initial_backup_count}")
        print(f"   Final backup count: {final_backup_count}")
        print(f"   Memory usage: {final_status['backups']['current_mb']:.3f}MB")


def run_memory_backup_usage_tests():
    """Run all memory backup usage tests manually"""
    print("=== Memory Backup Usage Tests ===")
    
    test_instance = TestMemoryBackupUsage()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        try:
            test_instance.test_edit_file_atomic_uses_memory_backup(project_path)
            test_instance.test_no_disk_backups_created(project_path)
            test_instance.test_memory_backup_system_status(project_path)
            
            print("\n=== All Memory Backup Usage Tests Passed ===")
            print("✅ Main edit functions are using memory backup system")
            return True
            
        except Exception as e:
            print(f"\n❌ Memory backup usage test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = run_memory_backup_usage_tests()
    if not success:
        sys.exit(1)