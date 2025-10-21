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
            from ..code_index_mcp.config import get_memory_backup_config

            config = get_memory_backup_config()

            self.max_memory_mb = config.max_memory_mb
            self.max_file_size_mb = config.max_file_size_mb
            self.lock_timeout_seconds = min(
                config.backup_timeout_seconds, 30.0
            )  # Cap at 30 seconds
        except ImportError:
            # Fallback to defaults
            self.max_memory_mb = 50
            self.max_file_size_mb = 10
            self.lock_timeout_seconds = 5
        except Exception:
            self.max_memory_mb = 50
            self.max_file_size_mb = 10
            self.lock_timeout_seconds = 5

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
            self._validate_backup_file(file_path)

            # Don't acquire lock here - let apply_edit handle it
            operation = self._create_backup_operation(file_path)
            self._store_backup_operation(operation)
            self._finalize_backup_operation(operation)
            return operation.operation_id

    def _validate_backup_file(self, file_path: Path) -> None:
        """Validate file for backup operation."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise MemoryLimitExceededError(
                f"File too large: {file_size_mb:.1f}MB > {self.max_file_size_mb}MB"
            )

    def _acquire_backup_lock(self, file_path: Path) -> Any:
        """Acquire file lock for backup operation."""
        try:
            from .file_lock import acquire_file_lock

            return acquire_file_lock(
                file_path, lock_type="exclusive", timeout=self.lock_timeout_seconds
            )
        except Exception as e:
            raise FileLockError(f"Failed to acquire lock for {file_path}: {e}")

    def _create_backup_operation(self, file_path: Path) -> EditOperation:
        """Create backup operation for file."""
        # Create file state
        file_state = FileState.from_file(file_path)

        # Read file content
        original_content = file_path.read_text(encoding="utf-8")

        # Create edit operation
        operation = EditOperation(file_path=str(file_path.absolute()))
        operation.set_original_content(original_content)
        operation.file_state = file_state
        operation.set_status(EditStatus.IN_PROGRESS)

        return operation

    def _store_backup_operation(self, operation: Any) -> None:
        """Store backup operation in memory manager."""
        if not self.memory_manager.add_backup(operation):
            raise MemoryLimitExceededError(
                f"Cannot add backup - memory limit exceeded: "
                f"{self.memory_manager.current_memory_mb:.1f}MB"
            )

        # Record memory operation
        self.memory_monitor.record_operation(
            operation.memory_size / (1024 * 1024), "backup_creation"
        )

    def _finalize_backup_operation(self, operation: Any) -> None:
        """Finalize backup operation as completed."""
        operation.set_status(EditStatus.COMPLETED)

    def _cleanup_failed_backup(
        self,
        file_path: Path,
        operation: Any,
        error: Exception,
    ) -> None:
        """Clean up after failed backup operation."""
        self.memory_manager.remove_backup(str(file_path))
        operation.set_status(EditStatus.FAILED, str(error))

    def _release_backup_lock(self, file_lock: Optional[Any]) -> None:
        """Release backup lock file."""
        if file_lock is not None:
            try:
                from .file_lock import release_file_lock

                release_file_lock(
                    file_lock.file_path
                    if hasattr(file_lock, "file_path")
                    else file_lock
                )
            except Exception:
                pass

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
                    if operation.file_state and not operation.file_state.is_valid(
                        current_content
                    ):
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

        operation, error = self._create_backup_for_edit(file_path)
        if not operation:
            return False, error or "Failed to create backup"

        if not self._validate_edit_content(operation, file_path, expected_old_content):
            return False, "Content validation failed"

        if not self._prepare_edit_content(operation, new_content, file_path):
            return False, "Failed to prepare edit content"

        file_lock = None
        try:
            file_lock = self._acquire_edit_lock(file_path)
            if not file_lock:
                return False, "Failed to acquire lock"
            return self._execute_edit(operation, file_path, new_content)
        except Exception as e:
            return self._handle_edit_failure(operation, file_path, e)
        finally:
            if file_lock:
                release_file_lock(file_path)

    def _create_backup_for_edit(
        self, file_path: Path
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Create backup for edit operation."""
        try:
            operation_id = self.backup_file(file_path)
            operation = self.memory_manager.get_backup(str(file_path))
            return operation, None
        except FileNotFoundError as e:
            return None, str(e)
        except Exception as e:
            return None, f"Backup failed: {e}"

    def _validate_edit_content(
        self,
        operation: Any,
        file_path: Path,
        expected_old_content: Optional[str],
    ) -> bool:
        """Validate expected content before edit."""
        if expected_old_content is None:
            return True

        current_content = file_path.read_text(encoding="utf-8")
        if not operation.validate_content_match(expected_old_content):
            # Try to match with current content
            operation.set_original_content(current_content)
            if not operation.validate_content_match(expected_old_content):
                return False

        return True

    def _prepare_edit_content(
        self,
        operation: Any,
        new_content: str,
        file_path: Path,
    ) -> bool:
        """Prepare content for edit operation."""
        try:
            operation.set_new_content(new_content)
            return True
        except MemoryLimitExceededError:
            self.memory_manager.remove_backup(str(file_path))
            return False

    def _acquire_edit_lock(self, file_path: Path) -> bool:
        """Acquire file lock for edit operation."""
        try:
            acquire_file_lock(
                file_path, lock_type="exclusive", timeout=self.lock_timeout_seconds
            )
            return True
        except Exception as e:
            self.memory_manager.remove_backup(str(file_path))
            return False

    def _execute_edit(
        self,
        operation: Any,
        file_path: Path,
        new_content: str,
    ) -> Tuple[bool, Optional[str]]:
        """Execute the edit operation."""
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

    def _handle_edit_failure(
        self,
        operation: Any,
        file_path: Path,
        edit_error: Exception,
    ) -> Tuple[bool, str]:
        """Handle edit failure with rollback."""
        rollback_success, rollback_error = self._attempt_rollback(operation, file_path)
        error_msg = self._construct_error_message(
            edit_error, rollback_success, rollback_error
        )
        return False, error_msg

    def _attempt_rollback(
        self,
        operation: Any,
        file_path: Path,
    ) -> Tuple[bool, Optional[str]]:
        """Attempt to rollback failed edit."""
        if not operation.original_content:
            return False, "No original content available"

        try:
            # Validate rollback safety before proceeding
            if not self._validate_rollback_safety_for_edit(operation, file_path):
                return False, "Rollback unsafe"

            # Perform rollback
            file_path.write_text(operation.original_content, encoding="utf-8")
            operation.set_status(EditStatus.ROLLED_BACK)
            return True, None

        except Exception as e:
            operation.set_status(EditStatus.FAILED, f"Rollback failed: {e}")
            return False, str(e)

    def _validate_rollback_safety_for_edit(
        self,
        operation: EditOperation,
        file_path: Path,
    ) -> bool:
        """Validate rollback safety for edit operation."""
        if not operation.file_state:
            return True  # No validation available, proceed

        try:
            current_content = file_path.read_text(encoding="utf-8")
            current_state = FileState.from_file(file_path)
            can_rollback, reason = operation.file_state.can_safely_rollback(
                current_content, current_state
            )
            if not can_rollback:
                operation.set_status(EditStatus.FAILED, f"Rollback unsafe: {reason}")
            return can_rollback
        except Exception:
            return True  # Validation failed, proceed with caution

    def _construct_error_message(
        self,
        edit_error: Exception,
        rollback_success: bool,
        rollback_error: Optional[str],
    ) -> str:
        """Construct appropriate error message."""
        if rollback_success:
            return f"Edit failed but rollback succeeded: {edit_error}"
        elif rollback_error:
            return f"Edit failed and rollback failed: {edit_error}. Rollback error: {rollback_error}"
        else:
            return f"Edit failed: {edit_error}"

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

    def _create_recovery_report(self) -> Dict[str, Any]:
        """Create empty recovery report template."""
        return {
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

    def _analyze_backup_operations(
        self, recovery_report: Dict[str, Any]
    ) -> List[Tuple[str, Any]]:
        """Analyze backup operations and identify incomplete ones."""
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

        return incomplete_operations

    def _recover_incomplete_operation(
        self, file_path: str, operation, recovery_report: Dict[str, Any]
    ) -> None:
        """Attempt to recover a single incomplete operation."""
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
                return

            # Check current file state vs backup
            self._analyze_file_state(file_path, operation, recovery_report)

        except Exception as e:
            recovery_report["failed_recoveries"] += 1
            recovery_report["actions"].append(f"Recovery failed for {file_path}: {e}")

    def _analyze_file_state(
        self, file_path: str, operation, recovery_report: Dict[str, Any]
    ) -> None:
        """Analyze file state for recovery."""
        try:
            file_obj = Path(file_path)
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

    def _add_recovery_recommendations(self, recovery_report: Dict[str, Any]) -> None:
        """Add recommendations based on recovery analysis."""
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

    def crash_recovery(self) -> Dict[str, Any]:
        """
        Perform crash recovery analysis and cleanup

        This method analyzes the current state of backups and identifies any
        operations that may have been interrupted by a crash or system failure.

        Returns:
            Dictionary with recovery analysis and actions taken
        """
        recovery_report = self._create_recovery_report()

        with self._lock:
            try:
                # Analyze all backup operations
                incomplete_operations = self._analyze_backup_operations(recovery_report)

                # Attempt recovery for incomplete operations
                for file_path, operation in incomplete_operations:
                    self._recover_incomplete_operation(
                        file_path, operation, recovery_report
                    )

                # Clean up expired operations
                expired_count = self.memory_manager.cleanup_expired(
                    max_age_seconds=7200
                )  # 2 hours
                if expired_count > 0:
                    recovery_report["cleaned_backups"] += expired_count
                    recovery_report["actions"].append(
                        f"Cleaned up {expired_count} expired backup operations"
                    )

                # Add recommendations based on analysis
                self._add_recovery_recommendations(recovery_report)

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

        rollback_report = self._create_rollback_report()

        with self._lock:
            try:
                operations_to_rollback = self._find_operations_needing_rollback(
                    rollback_report
                )
                self._perform_emergency_rollbacks(
                    operations_to_rollback, rollback_report
                )
                self._cleanup_after_rollback(operations_to_rollback, rollback_report)
                self._add_rollback_summary(rollback_report)

            except Exception as e:
                rollback_report["success"] = False
                rollback_report["error"] = str(e)
                rollback_report["actions"].append(f"Emergency rollback failed: {e}")

        return rollback_report

    def _create_rollback_report(self) -> Dict[str, Any]:
        """Create rollback report template."""
        return {
            "timestamp": time.time(),
            "total_operations": 0,
            "rolled_back_operations": 0,
            "failed_rollbacks": 0,
            "warnings": [],
            "actions": [],
        }

    def _find_operations_needing_rollback(
        self, rollback_report: Dict[str, Any]
    ) -> List[Tuple[str, Any]]:
        """Find all operations that need emergency rollback."""
        operations_to_rollback = []

        for file_path, operation in self.memory_manager.backup_cache.items():
            # Rollback in-progress or failed operations
            if operation.status in [EditStatus.IN_PROGRESS, EditStatus.FAILED]:
                if operation.original_content:
                    operations_to_rollback.append((file_path, operation))

        rollback_report["actions"].append(
            f"Found {len(operations_to_rollback)} operations requiring emergency rollback"
        )
        return operations_to_rollback

    def _perform_emergency_rollbacks(
        self,
        operations_to_rollback: List[Tuple[str, Any]],
        rollback_report: Dict[str, Any],
    ) -> None:
        """Perform emergency rollback operations."""
        for file_path, operation in operations_to_rollback:
            try:
                if not self._validate_and_prepare_rollback(
                    file_path, operation, rollback_report
                ):
                    continue

                self._execute_rollback(file_path, operation)
                rollback_report["rolled_back_operations"] += 1
                rollback_report["actions"].append(
                    f"Successfully rolled back: {file_path}"
                )

            except Exception as e:
                rollback_report["failed_rollbacks"] += 1
                rollback_report["actions"].append(
                    f"Failed to rollback {file_path}: {e}"
                )

    def _validate_and_prepare_rollback(
        self,
        file_path: str,
        operation: Any,
        rollback_report: Dict[str, Any],
    ) -> bool:
        """Validate rollback safety and prepare file."""
        file_obj = Path(file_path)

        # Check if file exists
        if not file_obj.exists():
            rollback_report["actions"].append(
                f"Skipping rollback for missing file: {file_path}"
            )
            return False

        # Validate rollback safety if possible
        if operation.file_state:
            if not self._validate_rollback_safety(file_obj, operation, rollback_report):
                return False

        return True

    def _validate_rollback_safety(
        self,
        file_obj: Path,
        operation: Any,
        rollback_report: Dict[str, Any],
    ) -> bool:
        """Validate if rollback is safe for the given file."""
        try:
            current_content = file_obj.read_text(encoding="utf-8")
            current_state = FileState.from_file(file_obj)
            can_rollback, reason = operation.file_state.can_safely_rollback(
                current_content, current_state
            )
            if not can_rollback:
                rollback_report["warnings"].append(
                    f"Unsafe rollback for {file_obj}: {reason}"
                )
                return False
        except Exception:
            # If validation fails, proceed with caution
            rollback_report["warnings"].append(
                f"Could not validate rollback safety for {file_obj}"
            )

        return True

    def _execute_rollback(self, file_path: str, operation: Any) -> None:
        """Execute the actual rollback operation."""
        file_obj = Path(file_path)

        if operation.original_content is not None:
            file_obj.write_text(operation.original_content, encoding="utf-8")
        else:
            raise EditOperationError("No original content available for rollback")

        operation.set_status(EditStatus.ROLLED_BACK)

    def _cleanup_after_rollback(
        self,
        operations_to_rollback: List[Tuple[str, Any]],
        rollback_report: Dict[str, Any],
    ) -> None:
        """Clean up memory after emergency rollback."""
        for file_path, operation in operations_to_rollback:
            if operation.status == EditStatus.ROLLED_BACK:
                memory_freed = getattr(operation, "memory_size", 0) / (1024 * 1024)
                self.memory_monitor.release_operation(memory_freed)
                self.memory_manager.remove_backup(file_path)

    def _add_rollback_summary(self, rollback_report: Dict[str, Any]) -> None:
        """Add summary information to rollback report."""
        if rollback_report["rolled_back_operations"] > 0:
            rollback_report["actions"].append(
                f"Emergency rollback completed: {rollback_report['rolled_back_operations']} files restored"
            )

        if rollback_report["warnings"]:
            rollback_report["actions"].append(
                f"Generated {len(rollback_report['warnings'])} warnings during rollback"
            )


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
    file_path: Union[str, Path],
    new_content: str,
    expected_old_content: Optional[str] = None,
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
