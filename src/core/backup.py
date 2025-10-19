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

import hashlib
import json
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .edit_models import (
    EditOperation,
    EditOperationError,
    EditStatus,
    FileCorruptionError,
    FileState,
    MemoryBackupManager,
    MemoryLimitExceededError,
)
from .file_lock import FileLockError, acquire_file_lock, release_file_lock

# Import core components
from .memory_monitor import MemoryThreshold, get_memory_monitor


class BackupSystem:
    """
    Unified backup system that combines memory management, file locking,
    and edit operations into a single cohesive interface.

    This is the main entry point for all memory-based backup operations.
    """

    def __init__(self):
        # Load configuration
        try:
            from ..config import get_memory_backup_config

            config = get_memory_backup_config()

            self.max_memory_mb = config.max_memory_mb
            self.max_file_size_mb = config.max_file_size_mb
            self.lock_timeout_seconds = config.backup_timeout_seconds
        except ImportError:
            # Fallback to defaults
            self.max_memory_mb = 50
            self.max_file_size_mb = 10
            self.lock_timeout_seconds = 30
        except Exception:
            self.max_memory_mb = 50
            self.max_file_size_mb = 10
            self.lock_timeout_seconds = 30

        # Core components
        self.memory_manager = MemoryBackupManager()
        self.memory_monitor = get_memory_monitor()

        # Thread safety
        self._lock = threading.RLock()

        # Configure memory monitoring
        self.memory_monitor.max_memory_mb = self.max_memory_mb
        self.memory_monitor.threshold = MemoryThreshold(
            warning_percent=80.0,
            critical_percent=90.0,
            absolute_limit_mb=self.max_memory_mb + 20.0,  # 20MB buffer
            backup_limit_mb=self.max_memory_mb,
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
                    file_path, lock_type="exclusive", timeout=self.lock_timeout_seconds
                )
            except Exception as e:
                raise FileLockError(f"Failed to acquire lock for {file_path}: {e}")

            try:
                # Create file state
                file_state = FileState.from_file(file_path)

                # Read file content
                original_content = file_path.read_text(encoding="utf-8")

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
                    operation.memory_size / (1024 * 1024), "backup_creation"
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
                    file_path, lock_type="exclusive", timeout=self.lock_timeout_seconds
                )
            except Exception:
                return False

            try:
                # Validate current file state if it exists
                if file_path.exists():
                    current_content = file_path.read_text(encoding="utf-8")
                    if operation.file_state and not operation.file_state.is_valid(current_content):
                        # File was modified externally, don't restore
                        return False

                # Restore content
                file_path.write_text(operation.original_content, encoding="utf-8")

                # Update operation status
                operation.set_status(EditStatus.ROLLED_BACK)

                return True

            except Exception:
                return False
            finally:
                release_file_lock(file_path)

    def apply_edit(
        self,
        file_path: Union[str, Path],
        new_content: str,
        expected_old_content: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
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
                current_content = file_path.read_text(encoding="utf-8")
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
                    file_path, lock_type="exclusive", timeout=self.lock_timeout_seconds
                )
            except Exception as e:
                self.memory_manager.remove_backup(str(file_path))
                return False, f"Failed to acquire lock: {e}"

            try:
                # Write new content
                file_path.write_text(new_content, encoding="utf-8")

                # Update file state to reflect new content for rollback validation
                try:
                    operation.file_state = FileState.from_file(file_path)
                except Exception:
                    # If we can't update file state, clear it to allow rollback
                    operation.file_state = None

                # Update operation status
                operation.set_status(EditStatus.COMPLETED)

                # Release memory for successful edit
                memory_freed = operation.memory_size / (1024 * 1024)
                self.memory_monitor.release_operation(memory_freed)

                return True, None

            except Exception as e:
                # Enhanced rollback on failure
                rollback_success = False
                rollback_error = None

                try:
                    if operation.original_content:
                        # Validate rollback safety before proceeding
                        current_content = file_path.read_text(encoding="utf-8")
                        current_state = FileState.from_file(file_path)

                        # Use FileState rollback validation if available
                        if operation.file_state:
                            can_rollback, reason = operation.file_state.can_safely_rollback(
                                current_content, current_state
                            )
                            if not can_rollback:
                                operation.set_status(
                                    EditStatus.FAILED, f"Rollback unsafe: {reason}"
                                )
                                return False, f"Edit failed and rollback unsafe: {reason}"

                        # Perform rollback
                        file_path.write_text(operation.original_content, encoding="utf-8")
                        operation.set_status(EditStatus.ROLLED_BACK)
                        rollback_success = True

                except Exception as rollback_exc:
                    rollback_error = str(rollback_exc)
                    operation.set_status(EditStatus.FAILED, f"Rollback failed: {rollback_error}")

                # Construct error message
                if rollback_success:
                    error_msg = f"Edit failed but rollback succeeded: {e}"
                elif rollback_error:
                    error_msg = (
                        f"Edit failed and rollback failed: {e}. Rollback error: {rollback_error}"
                    )
                else:
                    error_msg = f"Edit failed: {e}"

                return False, error_msg
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
                    "lock_timeout_seconds": self.lock_timeout_seconds,
                },
                "timestamp": time.time(),
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

    def crash_recovery(self) -> Dict[str, Any]:
        """
        Perform crash recovery analysis and cleanup

        This method analyzes the current state of backups and identifies any
        operations that may have been interrupted by a crash or system failure.

        Returns:
            Dictionary with recovery analysis and actions taken
        """
        recovery_report: Dict[str, Any] = {
            "timestamp": time.time(),
            "total_backups": 0,
            "analyzed_backups": 0,
            "incomplete_operations": 0,
            "stale_operations": 0,
            "corrupted_backups": 0,
            "memory_usage_mb": 0,
            "recovered_operations": 0,
            "failed_recoveries": 0,
            "cleaned_backups": 0,
            "actions": [],
            "recommendations": [],
        }

        with self._lock:
            try:
                # Analyze all backup operations
                incomplete_operations = []

                for file_path, operation in self.memory_manager.backup_cache.items():
                    recovery_report["analyzed_backups"] += 1

                    # Check for incomplete operations
                    if operation.status == EditStatus.IN_PROGRESS:
                        incomplete_operations.append((file_path, operation))
                        recovery_report["incomplete_operations"] += 1

                    # Check for very old operations that might be stale
                    elif operation.get_duration_seconds() > 3600:  # 1 hour
                        recovery_report["actions"].append(
                            f"Found stale operation for {file_path} (age: {operation.get_duration_seconds():.0f}s)"
                        )

                # Attempt recovery for incomplete operations
                for file_path, operation in incomplete_operations:
                    try:
                        # Check if file still exists
                        file_obj = Path(file_path)
                        if not file_obj.exists():
                            # File no longer exists, clean up backup
                            self.memory_manager.remove_backup(file_path)
                            recovery_report["cleaned_backups"] += 1
                            recovery_report["actions"].append(
                                f"Cleaned up backup for missing file: {file_path}"
                            )
                            recovery_report["recovered_operations"] += 1
                            continue

                        # Check current file state vs backup
                        try:
                            current_content = file_obj.read_text(encoding="utf-8")
                            current_state = FileState.from_file(file_obj)

                            # If we have original file state, compare
                            if operation.file_state:
                                if operation.file_state.checksum == current_state.checksum:
                                    # File hasn't changed since backup, operation likely completed
                                    operation.set_status(EditStatus.COMPLETED)
                                    recovery_report["recovered_operations"] += 1
                                    recovery_report["actions"].append(
                                        f"Marked operation as completed for {file_path} (no changes detected)"
                                    )
                                else:
                                    # File has changed, need investigation
                                    recovery_report["recommendations"].append(
                                        f"File {file_path} has changed since backup - manual review needed"
                                    )
                                    operation.set_status(
                                        EditStatus.FAILED, "Crash recovery: file state mismatch"
                                    )
                            else:
                                # No file state to compare, assume incomplete
                                operation.set_status(
                                    EditStatus.FAILED, "Crash recovery: incomplete operation"
                                )
                                recovery_report["actions"].append(
                                    f"Marked operation as failed for {file_path} (incomplete)"
                                )

                        except Exception as e:
                            # Error analyzing file, mark as failed
                            operation.set_status(EditStatus.FAILED, f"Crash recovery error: {e}")
                            recovery_report["failed_recoveries"] += 1
                            recovery_report["actions"].append(f"Failed to analyze {file_path}: {e}")

                    except Exception as e:
                        recovery_report["failed_recoveries"] += 1
                        recovery_report["actions"].append(f"Recovery failed for {file_path}: {e}")

                # Clean up expired operations
                expired_count = self.memory_manager.cleanup_expired(max_age_seconds=7200)  # 2 hours
                if expired_count > 0:
                    recovery_report["cleaned_backups"] += expired_count
                    recovery_report["actions"].append(
                        f"Cleaned up {expired_count} expired backup operations"
                    )

                # Add recommendations based on analysis
                if recovery_report["incomplete_operations"] > 0:
                    recovery_report["recommendations"].append(
                        f"Found {recovery_report['incomplete_operations']} incomplete operations - review recommended"
                    )

                if recovery_report["failed_recoveries"] > 0:
                    recovery_report["recommendations"].append(
                        f"{recovery_report['failed_recoveries']} operations failed recovery - manual intervention may be needed"
                    )

                # Memory usage check
                memory_status = self.memory_manager.get_memory_usage()
                if memory_status["usage_percent"] > 80:
                    recovery_report["recommendations"].append(
                        f"High memory usage ({memory_status['usage_percent']:.1f}%) - consider cleanup"
                    )

                recovery_report["actions"].append("Crash recovery analysis completed")

            except Exception as e:
                recovery_report["actions"].append(f"Crash recovery failed: {e}")
                recovery_report["recommendations"].append(
                    "System may be in inconsistent state - full restart recommended"
                )

        return recovery_report

    def emergency_rollback_all(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Emergency rollback of all in-progress operations

        This is a last resort measure to restore system consistency.
        Requires explicit confirmation to prevent accidental data loss.

        Args:
            confirm: Must be True to proceed with emergency rollback

        Returns:
            Dictionary with rollback results and statistics
        """
        if not confirm:
            return {
                "success": False,
                "error": "Emergency rollback requires explicit confirmation",
                "rolled_back": 0,
                "failed": 0,
                "actions": [],
            }

        rollback_report: Dict[str, Any] = {
            "timestamp": time.time(),
            "total_operations": 0,
            "rolled_back_operations": 0,
            "failed_rollbacks": 0,
            "warnings": [],
        }

        with self._lock:
            try:
                # Find all operations that need rollback
                operations_to_rollback = []

                for file_path, operation in self.memory_manager.backup_cache.items():
                    # Rollback in-progress or failed operations
                    if operation.status in [EditStatus.IN_PROGRESS, EditStatus.FAILED]:
                        if operation.original_content:
                            operations_to_rollback.append((file_path, operation))

                rollback_report["actions"].append(
                    f"Found {len(operations_to_rollback)} operations requiring emergency rollback"
                )

                # Perform rollbacks
                for file_path, operation in operations_to_rollback:
                    try:
                        file_obj = Path(file_path)

                        # Check if file exists
                        if not file_obj.exists():
                            rollback_report["actions"].append(
                                f"Skipping rollback for missing file: {file_path}"
                            )
                            continue

                        # Validate rollback safety if possible
                        if operation.file_state:
                            try:
                                current_content = file_obj.read_text(encoding="utf-8")
                                current_state = FileState.from_file(file_obj)
                                can_rollback, reason = operation.file_state.can_safely_rollback(
                                    current_content, current_state
                                )
                                if not can_rollback:
                                    rollback_report["warnings"].append(
                                        f"Unsafe rollback for {file_path}: {reason}"
                                    )
                                    continue
                            except Exception:
                                # If validation fails, proceed with caution
                                rollback_report["warnings"].append(
                                    f"Could not validate rollback safety for {file_path}"
                                )

                        # Perform rollback
                        if operation.original_content is not None:
                            file_obj.write_text(operation.original_content, encoding="utf-8")
                        else:
                            raise EditOperationError("No original content available for rollback")
                        operation.set_status(EditStatus.ROLLED_BACK)
                        rollback_report["rolled_back_operations"] += 1
                        rollback_report["actions"].append(f"Successfully rolled back: {file_path}")

                    except Exception as e:
                        rollback_report["failed_rollbacks"] += 1
                        rollback_report["actions"].append(f"Failed to rollback {file_path}: {e}")

                # Clean up memory after emergency rollback
                for file_path, operation in operations_to_rollback:
                    if operation.status == EditStatus.ROLLED_BACK:
                        memory_freed = getattr(operation, "memory_size", 0) / (1024 * 1024)
                        self.memory_monitor.release_operation(memory_freed)
                        self.memory_manager.remove_backup(file_path)

                if rollback_report["rolled_back_operations"] > 0:
                    rollback_report["actions"].append(
                        f"Emergency rollback completed: {rollback_report['rolled_back_operations']} files restored"
                    )

                if rollback_report["warnings"]:
                    rollback_report["actions"].append(
                        f"Generated {len(rollback_report['warnings'])} warnings during rollback"
                    )

            except Exception as e:
                rollback_report["success"] = False
                rollback_report["error"] = str(e)
                rollback_report["actions"].append(f"Emergency rollback failed: {e}")

        return rollback_report


# Global backup system instance
_global_backup_system: Optional[BackupSystem] = None


def get_backup_system() -> BackupSystem:
    """Get or create global backup system"""
    global _global_backup_system
    if _global_backup_system is None:
        _global_backup_system = BackupSystem()
    return _global_backup_system


def create_backup_system() -> BackupSystem:
    """Create backup system with configuration"""
    return BackupSystem()


# Convenience functions for common operations
def backup_file(file_path: Union[str, Path]) -> str:
    """Backup file using global system"""
    system = get_backup_system()
    return system.backup_file(file_path)


def restore_file(file_path: Union[str, Path]) -> bool:
    """Restore file using global system"""
    system = get_backup_system()
    return system.restore_file(file_path)


def apply_edit_with_backup(
    file_path: Union[str, Path], new_content: str, expected_old_content: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Apply edit with backup using global system"""
    system = get_backup_system()
    return system.apply_edit(file_path, new_content, expected_old_content)


def get_backup_status() -> Dict[str, Any]:
    """Get backup system status"""
    system = get_backup_system()
    return system.get_system_status()


def crash_recovery() -> Dict[str, Any]:
    """Perform crash recovery analysis using global backup system"""
    system = get_backup_system()
    return system.crash_recovery()


def emergency_rollback_all(confirm: bool = False) -> Dict[str, Any]:
    """Emergency rollback of all in-progress operations using global backup system"""
    system = get_backup_system()
    return system.emergency_rollback_all(confirm)
