"""
Performance Baseline Tests for Apply Edit Backup Functionality

Establishes baseline metrics for current disk-based backup system.
These measurements will be used to compare against memory-based implementation.

Following Linus's principle: "Good programmers measure, bad programmers guess."
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.edit import EditOperation, apply_edit, rollback_edit


class TestBackupBaseline:
    """Baseline measurements for current disk-based backup system."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with various file sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create test files of different sizes
            files = {
                "small.py": "def hello():\n    return 'Hello World'\n" * 10,  # ~250 bytes
                "medium.py": "class TestClass:\n    pass\n" * 100,  # ~2KB
                "large.py": "# Large file\n" + "x = 1\n" * 10000,  # ~100KB
            }
            
            for filename, content in files.items():
                (project_path / filename).write_text(content)
            
            yield project_path
    
    def measure_edit_operation(self, file_path: Path, new_content: str) -> Dict[str, float]:
        """Measure a single edit operation with timing."""
        # Read original content
        old_content = file_path.read_text(encoding='utf-8')
        
        # Measure backup creation time
        start_time = time.perf_counter()
        
        # Create edit operation
        operation = EditOperation(
            file_path=str(file_path),
            old_content=old_content,
            new_content=new_content
        )
        
        # Apply edit (includes backup creation)
        success, error = apply_edit(operation)
        
        end_time = time.perf_counter()
        
        # Measure backup file size
        backup_size = 0
        if operation.backup_path and Path(operation.backup_path).exists():
            backup_size = Path(operation.backup_path).stat().st_size
        
        return {
            'duration_ms': (end_time - start_time) * 1000,
            'backup_size_bytes': backup_size,
            'success': success,
            'error': error,
            'backup_path': operation.backup_path
        }
    
    def test_small_file_edit_baseline(self, temp_project):
        """Baseline measurement for small file editing."""
        file_path = temp_project / "small.py"
        new_content = file_path.read_text() + "\n# Added comment\n"
        
        metrics = self.measure_edit_operation(file_path, new_content)
        
        print(f"Small file edit: {metrics['duration_ms']:.2f}ms, "
              f"backup: {metrics['backup_size_bytes']} bytes")
        
        # Verify backup was created
        assert metrics['success']
        assert metrics['backup_size_bytes'] > 0
        assert metrics['backup_path'] and Path(metrics['backup_path']).exists()
        
        # Cleanup
        if metrics['backup_path']:
            Path(metrics['backup_path']).unlink(missing_ok=True)
    
    def test_medium_file_edit_baseline(self, temp_project):
        """Baseline measurement for medium file editing."""
        file_path = temp_project / "medium.py"
        new_content = file_path.read_text().replace("pass", "return True")
        
        metrics = self.measure_edit_operation(file_path, new_content)
        
        print(f"Medium file edit: {metrics['duration_ms']:.2f}ms, "
              f"backup: {metrics['backup_size_bytes']} bytes")
        
        assert metrics['success']
        assert metrics['backup_size_bytes'] > 0
        
        # Cleanup
        if metrics['backup_path']:
            Path(metrics['backup_path']).unlink(missing_ok=True)
    
    def test_large_file_edit_baseline(self, temp_project):
        """Baseline measurement for large file editing."""
        file_path = temp_project / "large.py"
        new_content = file_path.read_text() + "\n# Large file modification\n"
        
        metrics = self.measure_edit_operation(file_path, new_content)
        
        print(f"Large file edit: {metrics['duration_ms']:.2f}ms, "
              f"backup: {metrics['backup_size_bytes']} bytes")
        
        assert metrics['success']
        assert metrics['backup_size_bytes'] > 0
        
        # Cleanup
        if metrics['backup_path']:
            Path(metrics['backup_path']).unlink(missing_ok=True)
    
    def test_concurrent_edits_baseline(self, temp_project):
        """Baseline measurement for concurrent file edits."""
        files = ["small.py", "medium.py", "large.py"]
        results = []
        
        for filename in files:
            file_path = temp_project / filename
            new_content = file_path.read_text() + f"\n# Concurrent edit to {filename}\n"
            
            metrics = self.measure_edit_operation(file_path, new_content)
            results.append(metrics)
        
        total_duration = sum(r['duration_ms'] for r in results)
        total_backup_size = sum(r['backup_size_bytes'] for r in results)
        
        print(f"Concurrent edits: {total_duration:.2f}ms total, "
              f"{total_backup_size} bytes total backup")
        
        # All should succeed
        assert all(r['success'] for r in results)
        
        # Cleanup
        for result in results:
            if result['backup_path']:
                Path(result['backup_path']).unlink(missing_ok=True)
    
    def test_rollback_functionality_baseline(self, temp_project):
        """Baseline measurement for rollback functionality."""
        file_path = temp_project / "small.py"
        original_content = file_path.read_text()
        new_content = "# Completely different content\n"
        
        # Create edit operation
        operation = EditOperation(
            file_path=str(file_path),
            old_content=original_content,
            new_content=new_content
        )
        
        # Apply edit
        success, error = apply_edit(operation)
        assert success, f"Edit failed: {error}"
        
        # Verify file changed
        assert file_path.read_text() == new_content
        
        # Measure rollback time
        start_time = time.perf_counter()
        rollback_success = rollback_edit(operation)
        end_time = time.perf_counter()
        
        rollback_duration_ms = (end_time - start_time) * 1000
        
        print(f"Rollback operation: {rollback_duration_ms:.2f}ms")
        
        # Verify rollback worked
        assert rollback_success
        assert file_path.read_text() == original_content
        
        # Cleanup
        if operation.backup_path:
            Path(operation.backup_path).unlink(missing_ok=True)
    
    def test_backup_directory_structure(self, temp_project):
        """Analyze backup directory structure and naming."""
        file_path = temp_project / "small.py"
        new_content = file_path.read_text() + "\n# Test backup structure\n"
        
        operation = EditOperation(
            file_path=str(file_path),
            old_content=file_path.read_text(),
            new_content=new_content
        )
        
        success, error = apply_edit(operation)
        assert success
        
        backup_path = Path(operation.backup_path)
        
        # Analyze backup structure
        print(f"Backup directory: {backup_path.parent}")
        print(f"Backup filename: {backup_path.name}")
        print(f"Backup path pattern: {backup_path}")
        
        # Verify backup directory exists
        assert backup_path.parent.exists()
        assert backup_path.parent.name == ".edit_backup"
        
        # Verify backup file naming pattern
        assert "small.py" in backup_path.name
        assert backup_path.suffix == ".bak"
        
        # Cleanup
        backup_path.unlink(missing_ok=True)
        backup_path.parent.rmdir()
    
    def test_disk_space_usage_baseline(self, temp_project):
        """Measure disk space usage for backup operations."""
        original_sizes = {}
        backup_sizes = {}
        
        for filename in ["small.py", "medium.py", "large.py"]:
            file_path = temp_project / filename
            original_sizes[filename] = file_path.stat().st_size
            
            new_content = file_path.read_text() + f"\n# Disk space test for {filename}\n"
            
            operation = EditOperation(
                file_path=str(file_path),
                old_content=file_path.read_text(),
                new_content=new_content
            )
            
            success, error = apply_edit(operation)
            assert success
            
            if operation.backup_path:
                backup_sizes[filename] = Path(operation.backup_path).stat().st_size
        
        total_original = sum(original_sizes.values())
        total_backup = sum(backup_sizes.values())
        
        print(f"Original files: {total_original} bytes")
        print(f"Backup files: {total_backup} bytes")
        print(f"Backup overhead: {total_backup - total_original} bytes "
              f"({((total_backup/total_original - 1) * 100):.1f}%)")
        
        # Backup should be roughly same size as original
        for filename in original_sizes:
            assert abs(backup_sizes[filename] - original_sizes[filename]) < 100  # Allow small metadata diff
        
        # Cleanup
        for filename in backup_sizes:
            backup_file = temp_project / ".edit_backup" / f"{filename}.*.bak"
            for backup in backup_file.parent.glob(backup_file.name):
                backup.unlink()
        backup_file.parent.rmdir()


if __name__ == "__main__":
    # Run baseline tests manually
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    test_instance = TestBackupBaseline()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)
        
        # Create test files
        files = {
            "small.py": "def hello():\n    return 'Hello World'\n" * 10,
            "medium.py": "class TestClass:\n    pass\n" * 100,
            "large.py": "# Large file\n" + "x = 1\n" * 10000,
        }
        
        for filename, content in files.items():
            (project_path / filename).write_text(content)
        
        print("=== Apply Edit Backup Baseline Tests ===")
        
        # Run individual tests
        test_instance.test_small_file_edit_baseline(project_path)
        test_instance.test_medium_file_edit_baseline(project_path)
        test_instance.test_large_file_edit_baseline(project_path)
        test_instance.test_concurrent_edits_baseline(project_path)
        test_instance.test_rollback_functionality_baseline(project_path)
        test_instance.test_backup_directory_structure(project_path)
        test_instance.test_disk_space_usage_baseline(project_path)
        
        print("\n=== Baseline Tests Complete ===")