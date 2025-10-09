#!/usr/bin/env python3
"""
T006 Simple Integration Test - Memory Edit Workflow
简化的内存编辑工作流集成测试
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def test_memory_edit_integration():
    """Test memory edit operations integration"""
    print("🔧 Testing memory edit integration...")
    
    try:
        from src.code_index_mcp.core.edit_operations import MemoryEditOperations
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello world\nThis is a test")
            test_file = f.name
        
        try:
            # Test memory edit operations
            edit_ops = MemoryEditOperations()
            
            # Test file edit (includes automatic backup)
            old_content = "Hello world\nThis is a test"
            new_content = "Hello modified world\nThis is a test"
            
            success, error = edit_ops.edit_file_atomic(test_file, old_content, new_content)
            if not success:
                print(f"❌ File edit failed: {error}")
                return False
            print("✅ File edit with memory backup: PASSED")
            
            # Verify content
            with open(test_file, 'r') as f:
                content = f.read()
                if new_content in content:
                    print("✅ Content verification: PASSED")
                else:
                    print("❌ Content verification: FAILED")
                    return False
            
            return True
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
                
    except Exception as e:
        print(f"❌ Memory edit integration test failed: {e}")
        return False

def test_no_disk_backups():
    """Verify no disk backup files are created"""
    print("🔍 Verifying no disk backups...")
    
    # Check for backup files in current directory
    backup_extensions = ['.bak', '.backup', '.tmp', '.temp']
    current_dir = Path('.')
    
    found_backups = []
    for file_path in current_dir.iterdir():
        if file_path.is_file():
            if any(file_path.suffix == ext for ext in backup_extensions):
                found_backups.append(str(file_path))
    
    if found_backups:
        print(f"❌ Found backup files: {found_backups}")
        return False
    else:
        print("✅ No disk backup files: PASSED")
        return True

def main():
    """Run simplified T006 integration test"""
    print("🚀 T006 Simple Integration Test - Memory Edit Workflow")
    print("=" * 60)
    
    tests = [
        ("Memory Edit Integration", test_memory_edit_integration),
        ("No Disk Backups", test_no_disk_backups),
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
        print("🎉 T006 Simple Integration Test: PASSED")
        print("✅ Memory edit workflow is working correctly")
        return True
    else:
        print("❌ T006 Simple Integration Test: FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)