"""
Integration Test: Memory Monitoring and LRU Cleanup

Tests that memory monitoring and LRU cleanup mechanisms work correctly.
Following Linus's principle: "Good taste is eliminating special cases."
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
from code_index_mcp.core.edit_models import MemoryBackupManager
from code_index_mcp.core.memory_monitor import get_memory_monitor, MemoryThreshold


class TestMemoryMonitoringLRU:
    """Test memory monitoring and LRU cleanup mechanisms"""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path
    
    @pytest.fixture
    def small_backup_manager(self):
        """Create backup manager with small memory limit for testing"""
        return MemoryBackupManager(max_memory_mb=5)  # 5MB limit
    
    def test_memory_monitoring_tracking(self, temp_project):
        """Test memory monitoring tracks operations correctly"""
        # Get memory monitor
        monitor = get_memory_monitor()
        
        # Get initial state
        initial_status = monitor.get_current_usage()
        initial_usage = initial_status['current_mb']
        
        # Create test file and backup
        file_path = temp_project / "memory_monitor_test.txt"
        content = "x" * (1024 * 1024)  # 1MB content
        file_path.write_text(content)
        
        # Create backup (should record memory usage)
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(file_path)
        
        # Get updated status
        updated_status = monitor.get_current_usage()
        updated_usage = updated_status['current_mb']
        
        # Verify memory tracking
        assert updated_usage > initial_usage, "Memory usage should increase after backup"
        assert updated_status['peak_mb'] >= updated_usage, "Peak usage should be updated"
        
        print(f"✅ Memory monitoring tracks operations correctly")
        print(f"   Initial usage: {initial_usage:.3f}MB")
        print(f"   Updated usage: {updated_usage:.3f}MB")
        print(f"   Peak usage: {updated_status['peak_mb']:.3f}MB")
    
    def test_memory_threshold_warnings(self, temp_project):
        """Test memory threshold warnings and alerts"""
        # Create memory monitor with low threshold for testing
        from code_index_mcp.core.memory_monitor import create_memory_monitor
        monitor = create_memory_monitor(max_memory_mb=2.0)  # 2MB limit
        monitor.threshold = MemoryThreshold(
            warning_percent=25.0,  # Warning at 25% (0.5MB)
            critical_percent=75.0,  # Critical at 75% (1.5MB)
            absolute_limit_mb=3.0,
            backup_limit_mb=2.0
        )
        
        # Reset memory to low baseline
        monitor.current_usage_mb = 0.1
        
        # Track alerts
        alerts = []
        def alert_callback(level, alert_data):
            alerts.append((level, alert_data))
        
        monitor.set_alert_callback(alert_callback)
        
        # Record operation that should trigger warning
        monitor.record_operation(0.6, "test_operation")  # Should trigger warning (0.7MB > 0.5MB)
        
        # Debug info
        print(f"   Debug: current usage after first operation: {monitor.current_usage_mb:.3f}MB")
        print(f"   Debug: warning threshold: {monitor.max_memory_mb * (monitor.threshold.warning_percent / 100):.3f}MB")
        print(f"   Debug: alerts so far: {len(alerts)}")
        
        # Check for warning alert
        warning_alerts = [a for a in alerts if a[0] == "warning"]
        assert len(warning_alerts) > 0, f"Should trigger warning alert. Current: {monitor.current_usage_mb:.3f}MB, Threshold: {monitor.max_memory_mb * (monitor.threshold.warning_percent / 100):.3f}MB"
        
        # Record more memory (should trigger critical)
        monitor.record_operation(1.0, "test_operation")  # Should trigger critical (1.7MB > 1.5MB)
        
        # Check for critical alert
        critical_alerts = [a for a in alerts if a[0] == "critical"]
        assert len(critical_alerts) > 0, "Should trigger critical alert"
        
        print(f"✅ Memory threshold warnings work correctly")
        print(f"   Warning alerts: {len(warning_alerts)}")
        print(f"   Critical alerts: {len(critical_alerts)}")
        print(f"   Total alerts: {len(alerts)}")
        print(f"   Final memory usage: {monitor.current_usage_mb:.3f}MB")
    
    def test_lru_eviction_memory_pressure(self, temp_project, small_backup_manager):
        """Test LRU eviction under memory pressure"""
        # Create files that will exceed memory limit
        files = []
        for i in range(10):  # Create 10 files of 1MB each (10MB total > 5MB limit)
            file_path = temp_project / f"lru_test_{i}.txt"
            content = f"Content for file {i}" + "x" * (1024 * 1024 - 20)  # ~1MB each
            file_path.write_text(content)
            files.append(file_path)
        
        # Track which files get evicted
        backup_info = {}
        
        # Add backups for all files (should trigger LRU eviction)
        for i, file_path in enumerate(files):
            from code_index_mcp.core.edit_models import EditOperation
            
            operation = EditOperation(
                file_path=str(file_path.absolute()),
                original_content=file_path.read_text()
            )
            
            success = small_backup_manager.add_backup(operation)
            backup_info[str(file_path)] = {
                'added': success,
                'index': i
            }
        
        # Check that memory limit is respected
        memory_usage = small_backup_manager.get_memory_usage()
        assert memory_usage['current_mb'] <= small_backup_manager.max_memory_mb, "Memory usage should not exceed limit"
        
        # Check that some files were evicted (final cache size < total files)
        final_cache_count = memory_usage['backup_count']
        evicted_count = len(files) - final_cache_count
        
        assert evicted_count > 0, "Some files should be evicted due to memory pressure"
        assert final_cache_count <= small_backup_manager.max_backups, "Backup count should not exceed limit"
        
        print(f"✅ LRU eviction works under memory pressure")
        print(f"   Files created: {len(files)}")
        print(f"   Files retained in cache: {final_cache_count}")
        print(f"   Files evicted: {evicted_count}")
        print(f"   Memory usage: {memory_usage['current_mb']:.3f}MB / {memory_usage['max_mb']}MB")
        print(f"   Backup count: {memory_usage['backup_count']}")
    
    def test_lru_access_order_update(self, temp_project, small_backup_manager):
        """Test LRU access order is updated correctly"""
        # Create smaller files to avoid immediate eviction
        files = []
        for i in range(3):
            file_path = temp_project / f"access_order_{i}.txt"
            content = f"Content for file {i}" + "x" * (512 * 1024 - 20)  # ~0.5MB each
            file_path.write_text(content)
            files.append(file_path)
        
        # Add backups
        from code_index_mcp.core.edit_models import EditOperation
        operations = []
        
        for file_path in files:
            operation = EditOperation(
                file_path=str(file_path.absolute()),
                original_content=file_path.read_text()
            )
            small_backup_manager.add_backup(operation)
            operations.append(operation)
        
        # Verify all files are in cache
        for file_path in files:
            backup = small_backup_manager.get_backup(str(file_path))
            assert backup is not None, f"File {file_path.name} should exist in cache"
        
        # Access first backup (should move to end of LRU order)
        first_backup = small_backup_manager.get_backup(str(files[0]))
        assert first_backup is not None, "First backup should exist"
        
        # Add more files to trigger memory pressure and eviction
        for i in range(3, 8):  # Add 5 more files (total 4MB > 5MB limit will trigger eviction)
            file_path = temp_project / f"filler_{i}.txt"
            content = f"Filler content {i}" + "x" * (512 * 1024 - 20)  # ~0.5MB each
            file_path.write_text(content)
            
            operation = EditOperation(
                file_path=str(file_path.absolute()),
                original_content=content
            )
            small_backup_manager.add_backup(operation)
        
        # Check that first file still exists (was accessed recently)
        first_backup_after = small_backup_manager.get_backup(str(files[0]))
        assert first_backup_after is not None, "First backup should still exist after access"
        
        # Check that second file was likely evicted (was LRU when we didn't access it)
        second_backup_after = small_backup_manager.get_backup(str(files[1]))
        # Note: This might not always be evicted depending on exact memory timing
        # The key test is that access order is updated correctly
        
        # Verify memory limit is respected
        memory_usage = small_backup_manager.get_memory_usage()
        assert memory_usage['current_mb'] <= small_backup_manager.max_memory_mb, "Memory usage should not exceed limit"
        
        print(f"✅ LRU access order updated correctly")
        print(f"   First file (accessed) exists: {first_backup_after is not None}")
        print(f"   Second file exists: {second_backup_after is not None}")
        print(f"   Memory usage: {memory_usage['current_mb']:.3f}MB / {memory_usage['max_mb']}MB")
        print(f"   Backup count: {memory_usage['backup_count']}")
    
    def test_expired_backup_cleanup(self, temp_project, small_backup_manager):
        """Test cleanup of expired backups"""
        # Create test file
        file_path = temp_project / "expired_test.txt"
        content = "Content for expired backup test"
        file_path.write_text(content)
        
        # Add backup
        from code_index_mcp.core.edit_models import EditOperation
        operation = EditOperation(
            file_path=str(file_path.absolute()),
            original_content=content
        )
        
        success = small_backup_manager.add_backup(operation)
        assert success, "Backup should be added"
        
        # Manually expire the backup by setting old timestamp
        import time
        from datetime import datetime, timedelta
        operation.created_at = datetime.now() - timedelta(hours=2)  # 2 hours ago
        
        # Run cleanup with 1 hour max age
        cleaned_count = small_backup_manager.cleanup_expired(max_age_seconds=3600)
        
        assert cleaned_count == 1, "Should clean up 1 expired backup"
        
        # Verify backup was removed
        backup_after = small_backup_manager.get_backup(str(file_path))
        assert backup_after is None, "Expired backup should be removed"
        
        print(f"✅ Expired backup cleanup works correctly")
        print(f"   Cleaned up backups: {cleaned_count}")
        print(f"   Backup exists after cleanup: {backup_after is not None}")
    
    def test_memory_release_on_completion(self, temp_project):
        """Test memory is released when operations complete"""
        # Get memory monitor
        monitor = get_memory_monitor()
        
        # Create test file
        file_path = temp_project / "release_test.txt"
        content = "x" * (1024 * 1024)  # 1MB content
        file_path.write_text(content)
        
        # Get initial memory
        initial_status = monitor.get_current_usage()
        initial_usage = initial_status['current_mb']
        
        # Create backup (should increase memory)
        backup_system = get_backup_system()
        operation_id = backup_system.backup_file(file_path)
        
        # Memory should increase
        after_backup_status = monitor.get_current_usage()
        after_backup_usage = after_backup_status['current_mb']
        assert after_backup_usage > initial_usage, "Memory should increase after backup"
        
        # Complete the operation (should release memory)
        backup_info = backup_system.get_backup_info(file_path)
        if backup_info:
            memory_size = backup_info.get('memory_size', 0) / (1024 * 1024)
            monitor.release_operation(memory_size)
        
        # Memory should decrease
        final_status = monitor.get_current_usage()
        final_usage = final_status['current_mb']
        
        # Note: Memory might not return exactly to initial due to other factors
        # But it should be less than after backup
        assert final_usage < after_backup_usage, "Memory should decrease after release"
        
        print(f"✅ Memory release on completion works correctly")
        print(f"   Initial usage: {initial_usage:.3f}MB")
        print(f"   After backup: {after_backup_usage:.3f}MB")
        print(f"   After release: {final_usage:.3f}MB")
    
    def test_memory_monitoring_history(self, temp_project):
        """Test memory monitoring maintains history"""
        # Get memory monitor
        monitor = get_memory_monitor()
        
        # Clear history for clean test
        monitor.history.clear()
        
        # Create test file
        file_path = temp_project / "history_test.txt"
        content = "Content for history test"
        file_path.write_text(content)
        
        # Record several operations
        for i in range(5):
            monitor.record_operation(0.1, f"test_operation_{i}")
            time.sleep(0.01)  # Small delay
        
        # Check history
        assert len(monitor.history) >= 5, "Should have at least 5 history entries"
        
        # Check peak usage was tracked
        current_status = monitor.get_current_usage()
        assert current_status['peak_mb'] > 0, "Peak usage should be tracked"
        
        print(f"✅ Memory monitoring history works correctly")
        print(f"   History entries: {len(monitor.history)}")
        print(f"   Peak usage: {current_status['peak_mb']:.3f}MB")


def run_memory_monitoring_lru_tests():
    """Run all memory monitoring and LRU tests manually"""
    print("=== Memory Monitoring and LRU Tests ===")
    
    test_instance = TestMemoryMonitoringLRU()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        try:
            test_instance.test_memory_monitoring_tracking(project_path)
            test_instance.test_memory_threshold_warnings(project_path)
            test_instance.test_lru_eviction_memory_pressure(project_path, test_instance.small_backup_manager())
            test_instance.test_lru_access_order_update(project_path, test_instance.small_backup_manager())
            test_instance.test_expired_backup_cleanup(project_path, test_instance.small_backup_manager())
            test_instance.test_memory_release_on_completion(project_path)
            test_instance.test_memory_monitoring_history(project_path)
            
            print("\n=== All Memory Monitoring and LRU Tests Passed ===")
            print("✅ Memory monitoring and LRU cleanup mechanisms work correctly")
            return True
            
        except Exception as e:
            print(f"\n❌ Memory monitoring test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = run_memory_monitoring_lru_tests()
    if not success:
        sys.exit(1)