#!/usr/bin/env python3
"""Test LRU eviction under memory pressure"""

import tempfile
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from code_index_mcp.core.edit_models import MemoryBackupManager, EditOperation
from code_index_mcp.config import reset_config
import pytest


class TestLRUEviction:
    """Test LRU eviction behavior under memory pressure"""
    
    def test_lru_eviction_basic_functionality(self):
        """Test basic LRU eviction functionality"""
        # Reset config and set small limits
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "3",  # 3MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create multiple files that will exceed memory limit
            files = []
            operations = []
            
            for i in range(4):
                file_path = project_path / f"file_{i}.txt"
                content = f"x" * (800 * 1024)  # 800KB each
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                files.append(file_path)
                operations.append(operation)
            
            # Add first 3 files (should succeed, total 2.4MB < 3MB)
            for i in range(3):
                success = manager.add_backup(operations[i])
                assert success, f"File {i} should be added successfully"
                print(f"   Added file {i}, Memory: {manager.current_memory_mb:.2f}MB, Cache: {len(manager.backup_cache)}")
            
            # Add 4th file (should trigger LRU eviction)
            success = manager.add_backup(operations[3])
            assert success, "4th file should trigger LRU eviction and succeed"
            print(f"   Added file 3, Memory: {manager.current_memory_mb:.2f}MB, Cache: {len(manager.backup_cache)}")
            
            # Verify LRU eviction: first file should be evicted
            assert len(manager.backup_cache) == 3, "Should have 3 files after eviction"
            assert str(files[0]) not in manager.backup_cache, "First file should be evicted"
            assert str(files[1]) in manager.backup_cache, "Second file should remain"
            assert str(files[2]) in manager.backup_cache, "Third file should remain"
            assert str(files[3]) in manager.backup_cache, "Fourth file should be added"
            
            # Verify access order is updated correctly
            expected_order = [str(files[1]), str(files[2]), str(files[3])]
            assert manager.access_order == expected_order, f"Access order should be {expected_order}"
            
            print("✅ LRU eviction works correctly")
    
    def test_lru_eviction_access_pattern(self):
        """Test LRU eviction respects access patterns"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "3",  # 3MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "2"  # 2MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create files
            files = []
            operations = []
            
            for i in range(3):
                file_path = project_path / f"file_{i}.txt"
                content = f"x" * (900 * 1024)  # 900KB each
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                files.append(file_path)
                operations.append(operation)
            
            # Add all 3 files
            for i in range(3):
                success = manager.add_backup(operations[i])
                assert success, f"File {i} should be added"
            
            print(f"   After adding 3 files: Memory={manager.current_memory_mb:.2f}MB, Cache={len(manager.backup_cache)}")
            
            # Access the first file (should make it most recently used)
            backup = manager.get_backup(str(files[0]))
            assert backup is not None, "Should retrieve first file"
            print(f"   Accessed file 0, Access order: {[Path(f).name for f in manager.access_order]}")
            
            # Add a 4th file to trigger eviction
            file_4 = project_path / "file_4.txt"
            content_4 = "x" * (900 * 1024)  # 900KB
            file_4.write_text(content_4)
            
            operation_4 = EditOperation(
                file_path=str(file_4),
                original_content=content_4
            )
            
            success = manager.add_backup(operation_4)
            assert success, "4th file should be added"
            
            print(f"   After adding 4th file: Memory={manager.current_memory_mb:.2f}MB, Cache={len(manager.backup_cache)}")
            print(f"   Final access order: {[Path(f).name for f in manager.access_order]}")
            
            # Verify that file 1 (not file 0) was evicted since file 0 was accessed
            assert len(manager.backup_cache) == 3, "Should have 3 files"
            assert str(files[0]) in manager.backup_cache, "File 0 should remain (was accessed)"
            assert str(files[1]) not in manager.backup_cache, "File 1 should be evicted (least recently used)"
            assert str(files[2]) in manager.backup_cache, "File 2 should remain"
            assert str(file_4) in manager.backup_cache, "File 4 should be added"
            
            print("✅ LRU eviction respects access patterns")
    
    def test_lru_eviction_memory_pressure(self):
        """Test LRU eviction under extreme memory pressure"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "2",  # 2MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create many small files
            files_added = 0
            for i in range(10):
                file_path = project_path / f"file_{i}.txt"
                content = "x" * (600 * 1024)  # 600KB each
                file_path.write_text(content)
                
                operation = EditOperation(
                    file_path=str(file_path),
                    original_content=content
                )
                
                success = manager.add_backup(operation)
                if success:
                    files_added += 1
                    print(f"   File {i}: Added, Memory={manager.current_memory_mb:.2f}MB, Cache={len(manager.backup_cache)}")
                else:
                    print(f"   File {i}: Failed to add")
                    break
            
            # Should be able to add at most 3 files (600KB * 3 = 1.8MB < 2MB)
            assert files_added >= 3, f"Should add at least 3 files, added {files_added}"
            assert len(manager.backup_cache) <= 3, f"Should have at most 3 files, has {len(manager.backup_cache)}"
            assert manager.current_memory_mb <= manager.max_memory_mb, "Memory usage should not exceed limit"
            
            print(f"✅ Memory pressure test passed: {files_added} files added, {len(manager.backup_cache)} in cache")
    
    def test_lru_eviction_edge_cases(self):
        """Test LRU eviction edge cases"""
        reset_config()
        
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "1",  # 1MB limit
            "CODE_INDEX_MAX_FILE_SIZE_MB": "1"  # 1MB per file
        }
        
        for var, value in env_vars.items():
            os.environ[var] = value
        
        reset_config()
        
        manager = MemoryBackupManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Test case 1: Single file exactly at limit
            file_1 = project_path / "file_1.txt"
            content_1 = "x" * (1024 * 1024)  # 1MB exactly
            file_1.write_text(content_1)
            
            operation_1 = EditOperation(
                file_path=str(file_1),
                original_content=content_1
            )
            
            success = manager.add_backup(operation_1)
            assert success, "File at exact limit should be added"
            assert len(manager.backup_cache) == 1, "Should have 1 file"
            
            # Test case 2: Try to add second file (should evict first)
            file_2 = project_path / "file_2.txt"
            content_2 = "x" * (900 * 1024)  # 900KB
            file_2.write_text(content_2)
            
            operation_2 = EditOperation(
                file_path=str(file_2),
                original_content=content_2
            )
            
            success = manager.add_backup(operation_2)
            assert success, "Second file should trigger eviction and be added"
            assert len(manager.backup_cache) == 1, "Should still have 1 file"
            assert str(file_1) not in manager.backup_cache, "First file should be evicted"
            assert str(file_2) in manager.backup_cache, "Second file should be added"
            
            print("✅ Edge cases handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])