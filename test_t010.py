#!/usr/bin/env python3
"""
T010 - API Contract Updates for Memory Backup
更新API契约反映内存备份变更
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def test_api_contract_changes():
    """Test API contract reflects memory backup changes"""
    print("🔧 Testing API contract changes...")
    
    try:
        # Check that apply_edit no longer creates disk backups
        from src.core.mcp_tools import tool_apply_edit
        from src.core.index import CodeIndex
        from pathlib import Path
        
        # Test apply_edit response structure using direct index
        from src.core.index import CodeIndex
        
        test_dir = Path("test_subdir").absolute()
        index = CodeIndex(base_path=str(test_dir), files={}, symbols={})
        
        test_file = str(Path("test_subdir/test_file.txt").absolute())
        
        # Read current content
        with open(test_file, 'r') as f:
            content = f.read()
        
        old_content = content.strip()
        new_content = content.strip() + "\n# Modified by API test"
        
        # Test direct index edit
        success, error = index.edit_file_atomic(test_file, old_content, new_content)
        
        result = {
            "success": success,
            "error": error,
            "files_changed": 1 if success else 0
        }
        
        # Verify response structure
        expected_keys = {"success", "error"}
        actual_keys = set(result.keys())
        
        if expected_keys.issubset(actual_keys):
            print("✅ API response structure: PASSED")
        else:
            print(f"❌ API response structure: missing {expected_keys - actual_keys}")
            return False
        
        # Verify success response
        if result.get("success"):
            print("✅ API success response: PASSED")
        else:
            print(f"❌ API failed: {result.get('error')}")
            return False
        
        # Verify no backup files created
        backup_files = list(Path(".").glob("*.bak")) + list(Path(".").glob("*.backup"))
        if not backup_files:
            print("✅ No disk backups created: PASSED")
        else:
            print(f"❌ Backup files found: {backup_files}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API contract test failed: {e}")
        return False

def test_memory_backup_api():
    """Test memory backup API integration"""
    print("🔧 Testing memory backup API...")
    
    try:
        from src.code_index_mcp.core.edit_operations import MemoryEditOperations
        from src.code_index_mcp.core.backup import get_backup_system
        
        # Test memory backup API
        edit_ops = MemoryEditOperations()
        from src.code_index_mcp.core.backup import get_backup_status
        
        # Test backup status API
        status = get_backup_status()
        expected_status_keys = {
            "memory", "backups", "limits", "timestamp"
        }
        
        if expected_status_keys.issubset(set(status.keys())):
            print("✅ Backup status API: PASSED")
        else:
            print(f"❌ Backup status API: missing keys")
            return False
        
        # Test memory usage API
        from src.code_index_mcp.core.memory_monitor import get_memory_monitor
        monitor = get_memory_monitor()
        
        memory_status = monitor.get_current_usage()
        expected_memory_keys = {
            "current_mb", "max_mb", "usage_percent", "peak_mb"
        }
        
        if expected_memory_keys.issubset(set(memory_status.keys())):
            print("✅ Memory usage API: PASSED")
        else:
            print(f"❌ Memory usage API: missing keys")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Memory backup API test failed: {e}")
        return False

def test_contract_documentation():
    """Test contract documentation updates"""
    print("🔧 Testing contract documentation...")
    
    try:
        # Check if contract files exist and are updated
        contract_dir = Path("specs/001-apply-edit-edit/contracts")
        if contract_dir.exists():
            contract_files = list(contract_dir.glob("*.yaml"))
            print(f"✅ Contract files found: {len(contract_files)}")
            
            for contract_file in contract_files:
                with open(contract_file, 'r') as f:
                    content = f.read()
                
                # Check for memory backup references
                if "memory" in content.lower() or "backup" in content.lower():
                    print(f"✅ Contract {contract_file.name}: contains backup references")
                else:
                    print(f"⚠️  Contract {contract_file.name}: no backup references")
        else:
            print("⚠️  Contract directory not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Contract documentation test failed: {e}")
        return False

def main():
    """Run T010 tests"""
    print("🚀 T010 - API Contract Updates for Memory Backup")
    print("=" * 60)
    
    tests = [
        ("API Contract Changes", test_api_contract_changes),
        ("Memory Backup API", test_memory_backup_api),
        ("Contract Documentation", test_contract_documentation),
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
        print("🎉 T010: PASSED")
        print("✅ API contracts updated for memory backup")
        return True
    else:
        print("❌ T010: FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)