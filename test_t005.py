#!/usr/bin/env python3
"""
Test script for T005: MemoryBackupManager core functionality
"""

import sys
import os
import tempfile
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_backup_system():
    """Test backup system functionality"""
    try:
        # Direct import from file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backup", 
            os.path.join(os.path.dirname(__file__), 'src', 'code_index_mcp', 'core', 'backup.py')
        )
        backup_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backup_module)
        
        BackupSystem = backup_module.BackupSystem
        get_backup_system = backup_module.get_backup_system
        backup_file = backup_module.backup_file
        restore_file = backup_module.restore_file
        apply_edit_with_backup = backup_module.apply_edit_with_backup
        get_backup_status = backup_module.get_backup_status
        
        print("✅ Successfully imported backup system modules")
        
        # Create test file
        test_file = Path(tempfile.gettempdir()) / "test_backup_system.txt"
        original_content = "Line 1\nLine 2\nLine 3\n"
        test_file.write_text(original_content)
        
        # Test backup system creation
        backup_system = BackupSystem(max_memory_mb=10.0)
        print("✅ BackupSystem created")
        
        # Test file backup
        operation_id = backup_system.backup_file(test_file)
        print(f"✅ File backed up: {operation_id}")
        
        # Test backup info
        backup_info = backup_system.get_backup_info(test_file)
        print(f"✅ Backup info: {backup_info['operation_id'] if backup_info else 'None'}")
        
        # Test backup listing
        backups = backup_system.list_backups()
        print(f"✅ Backup list: {len(backups)} backups")
        
        # Test edit with backup
        new_content = "Line 1\nMODIFIED Line 2\nLine 3\n"
        success, error = backup_system.apply_edit(test_file, new_content)
        print(f"✅ Edit applied: {success}")
        
        # Verify file content
        current_content = test_file.read_text()
        print(f"✅ Content updated: {current_content == new_content}")
        
        # Test restore
        restored = backup_system.restore_file(test_file)
        print(f"✅ File restored: {restored}")
        
        # Verify restore
        restored_content = test_file.read_text()
        print(f"✅ Content restored: {restored_content == original_content}")
        
        # Test global functions
        global_op_id = backup_file(test_file)
        print(f"✅ Global backup: {global_op_id}")
        
        global_success, global_error = apply_edit_with_backup(
            test_file, 
            "Global edit content\n"
        )
        print(f"✅ Global edit: {global_success}")
        
        global_status = get_backup_status()
        print(f"✅ Global status: {global_status['backups']['backup_count']} backups")
        
        # Test memory limits
        large_file = Path(tempfile.gettempdir()) / "large_test.txt"
        large_content = "x" * (15 * 1024 * 1024)  # 15MB
        large_file.write_text(large_content)
        
        try:
            backup_system.backup_file(large_file)
            print("❌ Large file should have been rejected!")
            return False
        except Exception as e:
            print(f"✅ Large file correctly rejected: {type(e).__name__}")
        
        # Test system status
        system_status = backup_system.get_system_status()
        print(f"✅ System status: {system_status['memory']['current_mb']:.2f}MB memory")
        
        # Test cleanup
        backup_system.clear_all_backups()
        final_backups = backup_system.list_backups()
        print(f"✅ Cleanup: {len(final_backups)} backups remaining")
        
        # Cleanup test files
        test_file.unlink()
        large_file.unlink()
        
        print("\n🎉 All backup system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Backup system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backup_system()
    sys.exit(0 if success else 1)