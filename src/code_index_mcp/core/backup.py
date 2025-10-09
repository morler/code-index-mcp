"""
Memory-based Backup System

Replaces disk-based backup with in-memory LRU cache system.
Integrates file locking, memory monitoring, and edit operations.

Design Principles:
- Direct data manipulation - no service abstractions
- Unified interface - single entry point for all backup operations
- Performance optimized - minimal overhead
- Memory efficient - LRU eviction with limits
- Thread safe - concurrent operation support
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Union

try:
    from .memory_monitor import get_memory_monitor, MemoryThreshold
    from .file_lock import acquire_file_lock, release_file_lock, FileLockError
    from .edit_models import (
        EditOperation, FileState, EditStatus, MemoryBackupManager,
        MemoryLimitExceededError, FileCorruptionError, EditOperationError
    )
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    core_path = Path(__file__).parent
    sys.path.insert(0, str(core_path))
    
    from memory_monitor import get_memory_monitor, MemoryThreshold
    from file_lock import acquire_file_lock, release_file_lock, FileLockError
    from edit_models import (
        EditOperation, FileState, EditStatus, MemoryBackupManager,
        MemoryLimitExceededError, FileCorruptionError, EditOperationError
    )

class BackupSystem:
    """
    Unified backup system that combines memory management, file locking,
    and edit operations into a single cohesive interface.
    
    This is the main entry point for all memory-based backup operations.
    """
    
    def __init__(self, 
                 max_memory_mb: float = 50.0,
                 max_file_size_mb: float = 10.0,
                 lock_timeout_seconds: float = 30.0):
        self.max_memory_mb = max_memory_mb
        self.max_file_size_mb = max_file_size_mb
        self.lock_timeout_seconds = lock_timeout_seconds
        
        # Core components
        self.memory_manager = MemoryBackupManager(max_memory_mb=max_memory_mb)
        self.memory_monitor = get_memory_monitor()
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Configure memory monitoring
        self.memory_monitor.max_memory_mb = max_memory_mb
        self.memory_monitor.threshold = MemoryThreshold(
            warning_percent=80.0,
            critical_percent=90.0,
            absolute_limit_mb=max_memory_mb + 20.0,  # 20MB buffer
            backup_limit_mb=max_memory_mb
        )
    
    def backup_file(self, file_path: Union[str, Path]) -> str:
        """
        Create in-memory backup of a file
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Operation ID for tracking
            
        Raises:
            FileNotFoundError: File doesn't exist
            MemoryLimitExceededError: File too large or memory limit exceeded
            FileLockError: Cannot acquire file lock
            FileCorruptionError: File cannot be read
        """
        file_path = Path(file_path)
        
        with self._lock:
            # Validate file exists
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                raise MemoryLimitExceededError(
                    f"File too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB"
                )
            
            # Acquire file lock
            try:
                file_lock = acquire_file_lock(
                    file_path, 
                    lock_type='exclusive', 
                    timeout=self.lock_timeout_seconds
                )
            except Exception as e:
                raise FileLockError(f"Failed to acquire lock for {file_path}: {e}")
            
            try:
                # Create file state
                file_state = FileState.from_file(file_path)
                
                # Read file content
                original_content = file_path.read_text(encoding='utf-8')
                
                # Create edit operation
                operation = EditOperation(file_path=str(file_path.absolute()))
                operation.set_original_content(original_content)
                operation.file_state = file_state
                operation.set_status(EditStatus.IN_PROGRESS)
                
                # Add to memory manager
                if not self.memory_manager.add_backup(operation):
                    raise MemoryLimitExceededError(
                        f"Cannot add backup - memory limit exceeded: "
                        f"{self.memory_manager.current_memory_mb:.1f}MB"
                    )
                
                # Record memory operation
                self.memory_monitor.record_operation(
                    operation.memory_size / (1024 * 1024),
                    "backup_creation"
                )
                
                operation.set_status(EditStatus.COMPLETED)
                return operation.operation_id
                
            except Exception as e:
                # Clean up on failure
                self.memory_manager.remove_backup(str(file_path))
                operation.set_status(EditStatus.FAILED, str(e))
                raise
            finally:
                # Always release lock
                release_file_lock(file_path)
    
    def restore_file(self, file_path: Union[str, Path]) -> bool:
        """
        Restore file from in-memory backup
        
        Args:
            file_path: Path to file to restore
            
        Returns:
            True if restore successful, False otherwise
        """
        file_path = Path(file_path)
        
        with self._lock:
            # Get backup operation
            operation = self.memory_manager.get_backup(str(file_path))
            if not operation:
                return False
            
            if not operation.original_content:
                return False
            
            # Acquire file lock
            try:
                file_lock = acquire_file_lock(
                    file_path,
                    lock_type='exclusive',
                    timeout=self.lock_timeout_seconds
                )
            except Exception:
                return False
            
            try:
                # Validate current file state if it exists
                if file_path.exists():
                    current_content = file_path.read_text(encoding='utf-8')
                    if operation.file_state and not operation.file_state.is_valid(current_content):
                        # File was modified externally, don't restore
                        return False
                
                # Restore content
                file_path.write_text(operation.original_content, encoding='utf-8')
                
                # Update operation status
                operation.set_status(EditStatus.ROLLED_BACK)
                
                return True
                
            except Exception:
                return False
            finally:
                release_file_lock(file_path)
    
    def apply_edit(self, 
                   file_path: Union[str, Path],
                   new_content: str,
                   expected_old_content: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Apply edit with memory backup
        
        Args:
            file_path: Path to file to edit
            new_content: New content to write
            expected_old_content: Expected current content (for validation)
            
        Returns:
            (success, error_message)
        """
        file_path = Path(file_path)
        
        with self._lock:
            # Create backup first
            try:
                operation_id = self.backup_file(file_path)
                operation = self.memory_manager.get_backup(str(file_path))
                if not operation:
                    return False, "Failed to create backup"
                
            except Exception as e:
                return False, f"Backup failed: {e}"
            
            # Validate expected content if provided
            if expected_old_content is not None:
                current_content = file_path.read_text(encoding='utf-8')
                if not operation.validate_content_match(expected_old_content):
                    # Try to match with current content
                    operation.set_original_content(current_content)
                    if not operation.validate_content_match(expected_old_content):
                        return False, "Content validation failed"
            
            # Set new content
            try:
                operation.set_new_content(new_content)
            except MemoryLimitExceededError as e:
                self.memory_manager.remove_backup(str(file_path))
                return False, str(e)
            
            # Acquire file lock for edit
            try:
                file_lock = acquire_file_lock(
                    file_path,
                    lock_type='exclusive',
                    timeout=self.lock_timeout_seconds
                )
            except Exception as e:
                self.memory_manager.remove_backup(str(file_path))
                return False, f"Failed to acquire lock: {e}"
            
            try:
                # Write new content
                file_path.write_text(new_content, encoding='utf-8')
                
                # Update operation status
                operation.set_status(EditStatus.COMPLETED)
                
                # Release memory for successful edit
                memory_freed = operation.memory_size / (1024 * 1024)
                self.memory_monitor.release_operation(memory_freed)
                
                return True, None
                
            except Exception as e:
                # Rollback on failure
                try:
                    if operation.original_content:
                        file_path.write_text(operation.original_content, encoding='utf-8')
                        operation.set_status(EditStatus.ROLLED_BACK)
                except Exception:
                    operation.set_status(EditStatus.FAILED, f"Rollback failed: {e}")
                
                return False, f"Edit failed: {e}"
            finally:
                release_file_lock(file_path)
    
    def get_backup_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get backup information for a file"""
        with self._lock:
            return self.memory_manager.get_backup_info(str(file_path))
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all active backups"""
        with self._lock:
            return self.memory_manager.list_backups()
    
    def remove_backup(self, file_path: Union[str, Path]) -> bool:
        """Remove backup for a file"""
        file_path = Path(file_path)
        
        with self._lock:
            operation = self.memory_manager.get_backup(str(file_path))
            if operation:
                # Release memory
                memory_freed = operation.memory_size / (1024 * 1024)
                self.memory_monitor.release_operation(memory_freed)
                
                # Remove from manager
                return self.memory_manager.remove_backup(str(file_path))
            
            return False
    
    def cleanup_expired_backups(self, max_age_seconds: float = 3600) -> int:
        """Clean up expired backups"""
        with self._lock:
            return self.memory_manager.cleanup_expired(max_age_seconds)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        with self._lock:
            memory_status = self.memory_monitor.get_current_usage()
            backup_status = self.memory_manager.get_memory_usage()
            
            return {
                "memory": memory_status,
                "backups": backup_status,
                "limits": {
                    "max_memory_mb": self.max_memory_mb,
                    "max_file_size_mb": self.max_file_size_mb,
                    "lock_timeout_seconds": self.lock_timeout_seconds
                },
                "timestamp": time.time()
            }
    
    def clear_all_backups(self) -> None:
        """Clear all backups (emergency use only)"""
        with self._lock:
            # Release all memory
            for operation in self.memory_manager.backup_cache.values():
                memory_freed = operation.memory_size / (1024 * 1024)
                self.memory_monitor.release_operation(memory_freed)
            
            # Clear manager
            self.memory_manager.clear_all()

# Global backup system instance
_global_backup_system: Optional[BackupSystem] = None

def get_backup_system() -> BackupSystem:
    """Get or create global backup system"""
    global _global_backup_system
    if _global_backup_system is None:
        _global_backup_system = BackupSystem()
    return _global_backup_system

def create_backup_system(max_memory_mb: float = 50.0,
                        max_file_size_mb: float = 10.0,
                        lock_timeout_seconds: float = 30.0) -> BackupSystem:
    """Create new backup system instance"""
    return BackupSystem(
        max_memory_mb=max_memory_mb,
        max_file_size_mb=max_file_size_mb,
        lock_timeout_seconds=lock_timeout_seconds
    )

# Convenience functions for common operations
def backup_file(file_path: Union[str, Path]) -> str:
    """Backup file using global system"""
    system = get_backup_system()
    return system.backup_file(file_path)

def restore_file(file_path: Union[str, Path]) -> bool:
    """Restore file using global system"""
    system = get_backup_system()
    return system.restore_file(file_path)

def apply_edit_with_backup(file_path: Union[str, Path],
                          new_content: str,
                          expected_old_content: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Apply edit with backup using global system"""
    system = get_backup_system()
    return system.apply_edit(file_path, new_content, expected_old_content)

def get_backup_status() -> Dict[str, Any]:
    """Get backup system status"""
    system = get_backup_system()
    return system.get_system_status()