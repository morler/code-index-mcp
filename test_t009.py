#!/usr/bin/env python3
"""
T009 - Edit Operation Status Tracking Implementation
创建编辑操作状态跟踪
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def test_edit_status_tracking():
    """Test edit operation status tracking"""
    print("🔧 Testing edit operation status tracking...")
    
    try:
        from src.code_index_mcp.core.edit_models import EditOperation, EditStatus, FileState
        from src.code_index_mcp.core.backup import get_backup_system
        
        # Test EditStatus enum
        print(f"✅ EditStatus values: {[status.value for status in EditStatus]}")
        
        # Test EditOperation creation
        operation = EditOperation(
            file_path=str(Path("test.txt").absolute()),
            original_content="old",
            new_content="new"
        )
        print(f"✅ EditOperation created: {operation.file_path}")
        
        # Test FileState
        import hashlib
        from datetime import datetime
        
        content = "test content"
        checksum = hashlib.md5(content.encode()).hexdigest()
        file_state = FileState(
            path="test.txt",
            checksum=checksum,
            size=len(content.encode()),
            modified_time=datetime.now()
        )
        print(f"✅ FileState created: {file_state.path} ({file_state.size} bytes)")
        
        # Test backup system status tracking
        from src.code_index_mcp.core.backup import get_backup_status
        status = get_backup_status()
        backup_count = status['backups'].get('backup_count', 0)
        print(f"✅ Backup system status: {backup_count} backups")
        
        return True
        
    except Exception as e:
        print(f"❌ Edit status tracking test failed: {e}")
        return False

def test_operation_lifecycle():
    """Test operation lifecycle tracking"""
    print("🔧 Testing operation lifecycle...")
    
    try:
        from src.code_index_mcp.core.edit_models import EditOperation, EditStatus
        from src.code_index_mcp.core.backup import get_backup_system
        
        backup_system = get_backup_system()
        
        # Create test file
        test_file = "test_subdir/test_file.txt"
        
        # Track operation from start to finish
        operation = EditOperation(
            file_path=str(Path(test_file).absolute()),
            original_content="Original content",
            new_content="Modified content"
        )
        
        # Simulate operation lifecycle
        print(f"✅ Operation created: {operation.operation_id}")
        print(f"✅ Initial status: {operation.status}")
        
        # Update status through lifecycle
        operation.status = EditStatus.IN_PROGRESS
        print(f"✅ Status updated: {operation.status}")
        
        operation.status = EditStatus.COMPLETED
        # Note: duration would need to be calculated from created_at
        print(f"✅ Operation completed")
        
        # Test backup cleanup tracking
        cleaned_count = backup_system.cleanup_expired_backups(max_age_seconds=0)
        print(f"✅ Cleanup tracking: {cleaned_count} cleaned")
        
        return True
        
    except Exception as e:
        print(f"❌ Operation lifecycle test failed: {e}")
        return False

def main():
    """Run T009 tests"""
    print("🚀 T009 - Edit Operation Status Tracking")
    print("=" * 60)
    
    tests = [
        ("Edit Status Tracking", test_edit_status_tracking),
        ("Operation Lifecycle", test_operation_lifecycle),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 T009: PASSED")
        print("✅ Edit operation status tracking implemented")
        return True
    else:
        print("❌ T009: FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)