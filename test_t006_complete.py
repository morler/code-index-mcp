#!/usr/bin/env python3
"""
T006 Complete Integration Test - Memory Edit Workflow
验证完整的内存编辑工作流集成
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def test_codeindex_integration():
    """Test CodeIndex integration with memory backup"""
    print("🔧 Testing CodeIndex integration...")
    
    try:
        from src.core.index import CodeIndex, AtomicEdit, BatchEdit
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Original content for testing\nLine 2\nLine 3")
            test_file = f.name
        
        try:
            # Create CodeIndex instance
            index = CodeIndex(base_path=Path(test_file).parent, files={}, symbols={})
            
            # Test single file edit through CodeIndex
            old_content = "Original content for testing\n"
            new_content = "Modified content for testing\n"
            
            success, error = index.edit_file_atomic(test_file, old_content, new_content)
            
            if success:
                print("✅ CodeIndex single edit: SUCCESS")
                
                # Verify content was changed
                with open(test_file, 'r') as f:
                    content = f.read()
                    if new_content in content:
                        print("✅ Content verification: PASSED")
                    else:
                        print("❌ Content verification: FAILED")
                        return False
            else:
                print(f"❌ CodeIndex single edit: FAILED - {error}")
                return False
            
            # Test batch edit through CodeIndex
            batch = BatchEdit(
                operations=[
                    AtomicEdit(
                        file_path=test_file,
                        old_content="Modified content for testing",
                        new_content="Batch modified content"
                    )
                ]
            )
            
            batch_success, batch_error = index.edit_files_transaction(batch)
            
            if batch_success:
                print("✅ CodeIndex batch edit: SUCCESS")
            else:
                print(f"❌ CodeIndex batch edit: FAILED - {batch_error}")
                return False
            
            return True
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
                
    except ImportError as e:
        print(f"⚠️  CodeIndex import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ CodeIndex integration test failed: {e}")
        return False

def test_no_disk_backups_created():
    """Verify no disk backup files are created during operations"""
    print("🔍 Checking for disk backup files...")
    
    # Common backup file patterns
    backup_patterns = [
        '*.bak', '*.backup', '*.tmp', '*.temp',
        '*_backup_*', '*_bak_*', '.backup_*'
    ]
    
    found_backups = []
    for pattern in backup_patterns:
        import glob
        matches = glob.glob(pattern, recursive=True)
        found_backups.extend(matches)
    
    if found_backups:
        print(f"❌ Found backup files: {found_backups}")
        return False
    else:
        print("✅ No disk backup files found: PASSED")
        return True

def main():
    """Run complete T006 integration test"""
    print("🚀 T006 Complete Integration Test - Memory Edit Workflow")
    print("=" * 60)
    
    tests = [
        ("CodeIndex Integration", test_codeindex_integration),
        ("No Disk Backups", test_no_disk_backups_created),
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
        print("🎉 T006 Complete Integration Test: PASSED")
        print("✅ Memory edit workflow fully integrated with CodeIndex")
        return True
    else:
        print("❌ T006 Complete Integration Test: FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)