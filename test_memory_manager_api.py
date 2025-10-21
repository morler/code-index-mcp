#!/usr/bin/env python3

"""Test MemoryBackupManager API consistency."""

import sys
import tempfile
from pathlib import Path

# Add src to path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def test_memory_manager_api():
    """Test MemoryBackupManager API consistency."""
    try:
        from core.edit_models import MemoryBackupManager, EditOperation

        print("Testing MemoryBackupManager API...")

        # Create manager
        manager = MemoryBackupManager()

        # Test basic methods exist
        assert hasattr(manager, "add_backup"), "Missing add_backup method"
        assert hasattr(manager, "get_backup"), "Missing get_backup method"
        assert hasattr(manager, "remove_backup"), "Missing remove_backup method"
        assert hasattr(manager, "get_memory_usage"), "Missing get_memory_usage method"
        assert hasattr(manager, "cleanup_expired"), "Missing cleanup_expired method"
        assert hasattr(manager, "clear_all"), "Missing clear_all method"
        assert hasattr(manager, "get_backup_info"), "Missing get_backup_info method"
        assert hasattr(manager, "list_backups"), "Missing list_backups method"

        print("✅ All required methods exist")

        # Test method signatures
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            # Create edit operation
            op = EditOperation(file_path=str(test_file))
            op.set_original_content("test content")

            # Test add_backup
            result = manager.add_backup(op)
            assert isinstance(result, bool), "add_backup should return bool"
            print("✅ add_backup signature correct")

            # Test get_backup
            retrieved = manager.get_backup(str(test_file))
            assert retrieved is not None, "get_backup should return operation"
            assert isinstance(retrieved, EditOperation), (
                "get_backup should return EditOperation"
            )
            print("✅ get_backup signature correct")

            # Test get_memory_usage
            usage = manager.get_memory_usage()
            assert isinstance(usage, dict), "get_memory_usage should return dict"
            assert "current_mb" in usage, "get_memory_usage should contain current_mb"
            print("✅ get_memory_usage signature correct")

            # Test get_backup_info
            info = manager.get_backup_info(str(test_file))
            assert info is not None, "get_backup_info should return info"
            assert isinstance(info, dict), "get_backup_info should return dict"
            print("✅ get_backup_info signature correct")

            # Test list_backups
            backups = manager.list_backups()
            assert isinstance(backups, list), "list_backups should return list"
            assert len(backups) > 0, "list_backups should contain items"
            print("✅ list_backups signature correct")

            # Test remove_backup
            result = manager.remove_backup(str(test_file))
            assert isinstance(result, bool), "remove_backup should return bool"
            print("✅ remove_backup signature correct")

            # Test cleanup_expired
            count = manager.cleanup_expired()
            assert isinstance(count, int), "cleanup_expired should return int"
            print("✅ cleanup_expired signature correct")

            # Test clear_all
            manager.clear_all()  # Should not return anything
            print("✅ clear_all signature correct")

        print("✅ MemoryBackupManager API is consistent")
        return True

    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_memory_manager_api()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
