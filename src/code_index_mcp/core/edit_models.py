"""
Memory-based Backup Data Structures

Implements EditOperation, FileState, and EditStatus classes for
in-memory backup system. Replaces disk-based backup with memory structures.

Design Principles:
- Direct data structures - no service abstractions
- Type safety - comprehensive validation
- Memory efficiency - minimal overhead
- Thread safety - concurrent access support
- Performance - optimized for fast operations
"""

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class EditStatus(Enum):
    """Edit operation status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class EditOperationError(Exception):
    """Base class for edit operation errors"""

    pass


class MemoryLimitExceededError(EditOperationError):
    """Raised when file too large for memory backup"""

    pass


class FileLockError(EditOperationError):
    """Raised when file cannot be locked"""

    pass


class FileCorruptionError(EditOperationError):
    """Raised when file checksum mismatch detected"""

    pass


@dataclass
class FileState:
    """
    Tracks file state during editing operations for rollback capability

    Attributes:
        path: Absolute file path
        checksum: MD5 checksum of file content
        size: File size in bytes
        modified_time: Last modification timestamp
        is_locked: Whether file is currently locked
        lock_owner: Process ID that owns the lock
        encoding: File encoding (default: utf-8)
    """

    path: str
    checksum: str
    size: int
    modified_time: datetime
    is_locked: bool = False
    lock_owner: Optional[int] = None
    encoding: str = "utf-8"

    @classmethod
    def from_file(cls, file_path: Union[str, Path], encoding: str = "utf-8") -> "FileState":
        """Create FileState from existing file"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read file content
            content = file_path.read_text(encoding=encoding)

            # Calculate checksum
            checksum = hashlib.md5(content.encode(encoding)).hexdigest()

            # Get file stats
            stat = file_path.stat()

            return cls(
                path=str(file_path.absolute()),
                checksum=checksum,
                size=len(content.encode(encoding)),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                encoding=encoding,
            )

        except UnicodeDecodeError as e:
            raise FileCorruptionError(f"File encoding error: {e}")
        except Exception as e:
            raise EditOperationError(f"Failed to read file state: {e}")

    def validate_rollback_safety(self, current_state: "FileState") -> Tuple[bool, Optional[str]]:
        """
        Validate if rollback is safe given current file state

        Args:
            current_state: Current file state to validate against

        Returns:
            (is_safe, reason) - Whether rollback is safe and reason if not
        """
        # Check if file path matches
        if self.path != current_state.path:
            return False, f"File path mismatch: {self.path} != {current_state.path}"

        # Check if file has been modified by another process
        # (significant size change might indicate external modification)
        size_diff = abs(self.size - current_state.size)
        if size_diff > max(self.size, current_state.size) * 0.1:  # 10% threshold
            return False, f"File size changed significantly: {self.size} -> {current_state.size}"

        # Check if file is locked by another process
        if current_state.is_locked and current_state.lock_owner != self.lock_owner:
            return False, f"File is locked by another process: {current_state.lock_owner}"

        return True, None

    def is_valid(self, content: str) -> bool:
        """
        Validate if content matches this file state

        Args:
            content: Content to validate

        Returns:
            True if content matches this file state
        """
        import hashlib

        # Calculate checksum of content
        content_checksum = hashlib.md5(content.encode(self.encoding)).hexdigest()

        # Check if checksum matches
        return content_checksum == self.checksum

    def has_externally_modified(
        self, current_state: "FileState", time_threshold_seconds: float = 1.0
    ) -> bool:
        """
        Check if file has been modified by external process

        Args:
            current_state: Current file state
            time_threshold_seconds: Time threshold for considering modification as external

        Returns:
            True if file was likely modified externally
        """
        # Check if checksum differs (content changed)
        if self.checksum != current_state.checksum:
            return True

        # Check if modification time is significantly newer
        time_diff = (current_state.modified_time - self.modified_time).total_seconds()
        if time_diff > time_threshold_seconds:
            return True

        return False

    def can_safely_rollback(
        self, current_content: str, current_state: Optional["FileState"] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Comprehensive check if rollback is safe

        Args:
            current_content: Current file content
            current_state: Current file state (optional, will be calculated if not provided)

        Returns:
            (can_rollback, reason) - Whether rollback is safe and reason if not
        """
        # If current state not provided, create it from content
        if current_state is None:
            try:
                current_checksum = hashlib.md5(current_content.encode(self.encoding)).hexdigest()
                current_size = len(current_content.encode(self.encoding))

                current_state = FileState(
                    path=self.path,
                    checksum=current_checksum,
                    size=current_size,
                    modified_time=datetime.now(),
                    encoding=self.encoding,
                )
            except Exception as e:
                return False, f"Failed to analyze current state: {e}"

        # Validate rollback safety
        is_safe, reason = self.validate_rollback_safety(current_state)
        if not is_safe:
            return False, reason

        # Check for external modifications
        if self.has_externally_modified(current_state):
            return False, "File has been modified by external process"

        return True, None

    def get_rollback_risk_assessment(self, current_state: "FileState") -> Dict[str, Any]:
        """
        Get detailed risk assessment for rollback operation

        Args:
            current_state: Current file state to assess against

        Returns:
            Dictionary with risk assessment details
        """
        risks = []
        risk_level = "low"

        # Check content changes
        if self.checksum != current_state.checksum:
            risks.append("Content has been modified")
            risk_level = "medium"

        # Check size changes
        size_diff = abs(self.size - current_state.size)
        size_change_percent = (
            (size_diff / max(self.size, current_state.size)) * 100
            if max(self.size, current_state.size) > 0
            else 0
        )
        if size_change_percent > 50:
            risks.append(f"Large size change: {size_change_percent:.1f}%")
            risk_level = "high"
        elif size_change_percent > 10:
            risks.append(f"Moderate size change: {size_change_percent:.1f}%")
            if risk_level == "low":
                risk_level = "medium"

        # Check time changes
        time_diff = (current_state.modified_time - self.modified_time).total_seconds()
        if time_diff > 300:  # 5 minutes
            risks.append(f"File modified long ago: {time_diff:.0f} seconds")
            risk_level = "medium"

        # Check locks
        if current_state.is_locked and current_state.lock_owner != self.lock_owner:
            risks.append(f"File locked by another process: {current_state.lock_owner}")
            risk_level = "high"

        return {
            "risk_level": risk_level,
            "risks": risks,
            "size_change_percent": size_change_percent,
            "time_diff_seconds": time_diff,
            "content_changed": self.checksum != current_state.checksum,
            "is_locked": current_state.is_locked,
            "can_rollback": len(risks) == 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "path": self.path,
            "checksum": self.checksum,
            "size": self.size,
            "modified_time": self.modified_time.isoformat(),
            "is_locked": self.is_locked,
            "lock_owner": self.lock_owner,
            "encoding": self.encoding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileState":
        """Create from dictionary"""
        return cls(
            path=data["path"],
            checksum=data["checksum"],
            size=data["size"],
            modified_time=datetime.fromisoformat(data["modified_time"]),
            is_locked=data.get("is_locked", False),
            lock_owner=data.get("lock_owner"),
            encoding=data.get("encoding", "utf-8"),
        )


@dataclass
class EditOperation:
    """
    Represents a file editing operation with in-memory backup capability

    Attributes:
        file_path: Absolute path to file being edited
        original_content: Original file content (backup)
        new_content: New file content to write
        status: Current operation status
        created_at: Operation creation timestamp
        memory_size: Memory usage in bytes
        operation_id: Unique operation identifier
        error_message: Error message if operation failed
        file_state: Original file state metadata
        timeout_seconds: Operation timeout
    """

    file_path: str
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    status: EditStatus = EditStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    memory_size: int = 0
    operation_id: str = field(default_factory=lambda: f"edit_{int(time.time() * 1000000)}")
    error_message: Optional[str] = None
    file_state: Optional[FileState] = None
    timeout_seconds: float = 30.0

    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def __post_init__(self):
        """Initialize operation after creation"""
        if self.original_content:
            self.memory_size = len(self.original_content.encode("utf-8"))

        # Validate file path
        if not Path(self.file_path).is_absolute():
            raise ValueError("file_path must be absolute")

    def set_original_content(self, content: str, encoding: str = "utf-8") -> None:
        """Set original content and update memory size"""
        with self._lock:
            self.original_content = content
            self.memory_size = len(content.encode(encoding))

    def set_new_content(self, content: str, encoding: str = "utf-8") -> None:
        """Set new content and validate size"""
        with self._lock:
            content_size = len(content.encode(encoding))

            # Check memory limits
            max_size_mb = 10  # 10MB limit per file
            if content_size > max_size_mb * 1024 * 1024:
                raise MemoryLimitExceededError(
                    f"File too large: {content_size / (1024*1024):.1f}MB > {max_size_mb}MB"
                )

            self.new_content = content

    def set_status(self, status: EditStatus, error_message: Optional[str] = None) -> None:
        """Update operation status"""
        with self._lock:
            self.status = status
            if error_message:
                self.error_message = error_message

    def get_duration_seconds(self) -> float:
        """Get operation duration in seconds"""
        return (datetime.now() - self.created_at).total_seconds()

    def is_expired(self) -> bool:
        """Check if operation has timed out"""
        return self.get_duration_seconds() > self.timeout_seconds

    def can_proceed(self) -> bool:
        """Check if operation can proceed (not failed or expired)"""
        with self._lock:
            return (
                self.status in [EditStatus.PENDING, EditStatus.IN_PROGRESS]
                and not self.is_expired()
            )

    def validate_content_match(self, current_content: str) -> bool:
        """Validate that original content matches current file state"""
        with self._lock:
            if not self.original_content:
                return False

            return self.original_content == current_content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        with self._lock:
            return {
                "operation_id": self.operation_id,
                "file_path": self.file_path,
                "status": self.status.value,
                "created_at": self.created_at.isoformat(),
                "memory_size": self.memory_size,
                "error_message": self.error_message,
                "file_state": self.file_state.to_dict() if self.file_state else None,
                "timeout_seconds": self.timeout_seconds,
                "duration_seconds": self.get_duration_seconds(),
                "is_expired": self.is_expired(),
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EditOperation":
        """Create from dictionary"""
        return cls(
            file_path=data["file_path"],
            status=EditStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            memory_size=data["memory_size"],
            operation_id=data["operation_id"],
            error_message=data.get("error_message"),
            file_state=FileState.from_dict(data["file_state"]) if data.get("file_state") else None,
            timeout_seconds=data.get("timeout_seconds", 30.0),
        )


@dataclass
class MemoryBackupManager:
    """
    Manages in-memory backups with LRU eviction policy

    Attributes:
        max_memory_mb: Maximum memory usage for backups
        current_memory_mb: Current memory usage
        backup_cache: Dictionary of file_path -> EditOperation
        access_order: List of file paths in LRU order
        max_backups: Maximum number of backup entries
    """

    # Configuration loaded from config system
    max_memory_mb: int = field(init=False)
    max_file_size_mb: int = field(init=False)
    max_backups: int = field(init=False)
    backup_timeout_seconds: int = field(init=False)
    memory_warning_threshold: float = field(init=False)

    # Runtime state
    current_memory_mb: float = 0.0
    backup_cache: Dict[str, EditOperation] = field(default_factory=dict)
    access_order: List[str] = field(default_factory=list)

    # Thread safety
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def __post_init__(self):
        """Load configuration after dataclass initialization"""
        try:
            from ..config import get_memory_backup_config

            config = get_memory_backup_config()

            self.max_memory_mb = config.max_memory_mb
            self.max_file_size_mb = config.max_file_size_mb
            self.max_backups = config.max_backups
            self.backup_timeout_seconds = config.backup_timeout_seconds
            self.memory_warning_threshold = config.memory_warning_threshold
        except ImportError:
            # Fallback to defaults if config not available
            self.max_memory_mb = 50
            self.max_file_size_mb = 10
            self.max_backups = 1000
            self.backup_timeout_seconds = 300
            self.memory_warning_threshold = 0.8

    def add_backup(self, operation: EditOperation) -> bool:
        """Add backup to memory cache with LRU eviction"""
        with self._lock:
            file_path = operation.file_path

            # Check file size limit
            required_memory = operation.memory_size / (1024 * 1024)  # Convert to MB
            if required_memory > self.max_file_size_mb:
                return False

            # Check if we need to evict
            required_memory = operation.memory_size / (1024 * 1024)  # Convert to MB
            if not self._ensure_space(required_memory):
                return False

            # Remove existing backup for same file if present
            if file_path in self.backup_cache:
                self._remove_backup_internal(file_path)

            # Add new backup
            self.backup_cache[file_path] = operation
            self.access_order.append(file_path)
            self.current_memory_mb += required_memory

            return True

    def get_backup(self, file_path: str) -> Optional[EditOperation]:
        """Retrieve backup from cache"""
        with self._lock:
            if file_path not in self.backup_cache:
                return None

            # Update access order (move to end)
            self.access_order.remove(file_path)
            self.access_order.append(file_path)

            return self.backup_cache[file_path]

    def remove_backup(self, file_path: str) -> bool:
        """Remove backup from cache"""
        with self._lock:
            return self._remove_backup_internal(file_path)

    def _remove_backup_internal(self, file_path: str) -> bool:
        """Internal backup removal (assumes lock held)"""
        if file_path not in self.backup_cache:
            return False

        operation = self.backup_cache[file_path]
        memory_freed = operation.memory_size / (1024 * 1024)

        del self.backup_cache[file_path]
        if file_path in self.access_order:
            self.access_order.remove(file_path)

        self.current_memory_mb = max(0, self.current_memory_mb - memory_freed)
        return True

    def _ensure_space(self, required_memory_mb: float) -> bool:
        """Evict old backups to make room"""
        # Check if single file exceeds limit
        if required_memory_mb > self.max_memory_mb:
            return False

        # Evict until we have enough space
        while (
            self.current_memory_mb + required_memory_mb > self.max_memory_mb
            or len(self.backup_cache) >= self.max_backups
        ):

            if not self.access_order:
                return False  # Nothing to evict but still not enough space

            # Remove least recently used
            lru_path = self.access_order[0]
            self._remove_backup_internal(lru_path)

        return True

    def evict_if_needed(self, required_memory: int) -> None:
        """Evict old backups to make room (bytes input)"""
        with self._lock:
            required_memory_mb = required_memory / (1024 * 1024)
            self._ensure_space(required_memory_mb)

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        with self._lock:
            return {
                "current_mb": self.current_memory_mb,
                "max_mb": self.max_memory_mb,
                "usage_percent": (self.current_memory_mb / self.max_memory_mb) * 100,
                "backup_count": len(self.backup_cache),
                "max_backups": self.max_backups,
            }

    def cleanup_expired(self, max_age_seconds: float = 3600) -> int:
        """Clean up expired operations"""
        with self._lock:
            expired_paths = []

            for file_path, operation in self.backup_cache.items():
                if operation.is_expired():
                    expired_paths.append(file_path)

            for path in expired_paths:
                self._remove_backup_internal(path)

            return len(expired_paths)

    def clear_all(self) -> None:
        """Clear all backups"""
        with self._lock:
            self.backup_cache.clear()
            self.access_order.clear()
            self.current_memory_mb = 0.0

    def get_backup_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get backup information for a specific file"""
        with self._lock:
            operation = self.backup_cache.get(file_path)
            return operation.to_dict() if operation else None

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups with their information"""
        with self._lock:
            return [
                {
                    "file_path": file_path,
                    "operation_id": op.operation_id,
                    "status": op.status.value,
                    "memory_size_mb": op.memory_size / (1024 * 1024),
                    "created_at": op.created_at.isoformat(),
                    "duration_seconds": op.get_duration_seconds(),
                }
                for file_path, op in self.backup_cache.items()
            ]

    def replace_disk_backup(
        self, file_path: Union[str, Path], disk_backup_path: Optional[Union[str, Path]] = None
    ) -> bool:
        """
        Replace disk backup with memory backup

        This method finds an existing disk backup and replaces it with a memory backup.
        If disk_backup_path is not provided, it will search for common backup file patterns.

        Args:
            file_path: Path to the original file
            disk_backup_path: Optional path to the disk backup file

        Returns:
            True if replacement successful, False otherwise
        """
        file_path = Path(file_path)

        with self._lock:
            try:
                # Read current file content for backup
                if not file_path.exists():
                    return False

                original_content = file_path.read_text(encoding="utf-8")

                # If we already have a memory backup, just clean up disk backup
                file_path_str = str(file_path.absolute())
                if file_path_str in self.backup_cache:
                    # Remove disk backup if specified
                    if disk_backup_path:
                        backup_path = Path(disk_backup_path)
                        if backup_path.exists():
                            backup_path.unlink()
                    else:
                        # Search for and remove common backup files
                        self._cleanup_disk_backups(file_path)

                    return True

                # Create memory backup operation
                operation = EditOperation(
                    file_path=file_path_str, original_content=original_content
                )

                # Add to memory cache
                if self.add_backup(operation):
                    # Remove disk backup if specified
                    if disk_backup_path:
                        backup_path = Path(disk_backup_path)
                        if backup_path.exists():
                            backup_path.unlink()
                    else:
                        # Search for and remove common backup files
                        self._cleanup_disk_backups(file_path)

                    return True

                return False

            except Exception:
                return False

    def _cleanup_disk_backups(self, file_path: Path) -> None:
        """Clean up common disk backup files for the given file"""
        backup_patterns = [
            file_path.with_suffix(file_path.suffix + ".bak"),
            file_path.with_suffix(file_path.suffix + ".backup"),
            file_path.parent / (file_path.name + "~"),
            file_path.with_name(f".{file_path.name}.swp"),
            file_path.parent / ".edit_backup" / file_path.name,
        ]

        for backup_path in backup_patterns:
            try:
                if backup_path.exists():
                    backup_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

    def rollback_file(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Rollback file to its original content using memory backup

        This method restores a file to its original state using the stored backup.
        It includes validation and error handling to ensure safe rollback operations.

        Args:
            file_path: Path to the file to rollback

        Returns:
            (success, error_message) - Success status and error message if failed
        """
        file_path = Path(file_path)
        file_path_str = str(file_path.absolute())

        with self._lock:
            try:
                # Check if backup exists
                if file_path_str not in self.backup_cache:
                    return False, f"No backup found for {file_path_str}"

                operation = self.backup_cache[file_path_str]

                # Validate backup has original content
                if not operation.original_content:
                    return False, f"Backup for {file_path_str} has no original content"

                # Check if file still exists
                if not file_path.exists():
                    return False, f"File {file_path_str} no longer exists"

                # Read current content for validation
                try:
                    current_content = file_path.read_text(encoding="utf-8")
                except Exception as e:
                    return False, f"Failed to read current file content: {e}"

                # Perform rollback
                try:
                    file_path.write_text(operation.original_content, encoding="utf-8")
                except Exception as e:
                    return False, f"Failed to write original content: {e}"

                # Update operation status
                operation.set_status(EditStatus.ROLLED_BACK)

                # Update access order (move to end since we just used it)
                if file_path_str in self.access_order:
                    self.access_order.remove(file_path_str)
                self.access_order.append(file_path_str)

                return True, None

            except Exception as e:
                return False, f"Rollback failed: {e}"

    def validate_rollback_possible(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validate if rollback is possible for the given file

        Args:
            file_path: Path to the file to validate

        Returns:
            (is_possible, reason) - Whether rollback is possible and reason if not
        """
        file_path = Path(file_path)
        file_path_str = str(file_path.absolute())

        with self._lock:
            # Check if backup exists
            if file_path_str not in self.backup_cache:
                return False, f"No backup found for {file_path_str}"

            operation = self.backup_cache[file_path_str]

            # Validate backup has original content
            if not operation.original_content:
                return False, f"Backup for {file_path_str} has no original content"

            # Check if file still exists
            if not file_path.exists():
                return False, f"File {file_path_str} no longer exists"

            # Check if operation is in a state that allows rollback
            if operation.status == EditStatus.ROLLED_BACK:
                return False, f"File {file_path_str} has already been rolled back"

            return True, None

    def get_rollback_preview(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Get preview of what rollback would do without actually performing it

        Args:
            file_path: Path to the file to preview rollback for

        Returns:
            Dictionary with rollback preview info, or None if no backup exists
        """
        file_path = Path(file_path)
        file_path_str = str(file_path.absolute())

        with self._lock:
            if file_path_str not in self.backup_cache:
                return None

            operation = self.backup_cache[file_path_str]

            # Read current content
            try:
                current_content = (
                    file_path.read_text(encoding="utf-8") if file_path.exists() else ""
                )
            except Exception:
                current_content = "<unreadable>"

            return {
                "file_path": file_path_str,
                "operation_id": operation.operation_id,
                "current_status": operation.status.value,
                "original_content_length": len(operation.original_content or ""),
                "current_content_length": len(current_content),
                "content_differs": current_content != (operation.original_content or ""),
                "backup_age_seconds": operation.get_duration_seconds(),
                "can_rollback": operation.original_content is not None
                and operation.status != EditStatus.ROLLED_BACK,
            }


# Global backup manager instance
_global_backup_manager: Optional[MemoryBackupManager] = None


def get_backup_manager() -> MemoryBackupManager:
    """Get or create global backup manager"""
    global _global_backup_manager
    if _global_backup_manager is None:
        _global_backup_manager = MemoryBackupManager()
    return _global_backup_manager


def create_backup_manager(max_memory_mb: int = 50) -> MemoryBackupManager:
    """Create new backup manager instance"""
    manager = MemoryBackupManager()
    manager.max_memory_mb = max_memory_mb
    return manager


# Convenience functions
def add_file_backup(file_path: str, original_content: str) -> str:
    """Add file backup to global manager"""
    manager = get_backup_manager()
    operation = EditOperation(file_path=file_path)
    operation.set_original_content(original_content)

    if manager.add_backup(operation):
        return operation.operation_id
    else:
        raise MemoryLimitExceededError("Failed to add backup - memory limit exceeded")


def get_file_backup(file_path: str) -> Optional[EditOperation]:
    """Get file backup from global manager"""
    manager = get_backup_manager()
    return manager.get_backup(file_path)


def remove_file_backup(file_path: str) -> bool:
    """Remove file backup from global manager"""
    manager = get_backup_manager()
    return manager.remove_backup(file_path)


def rollback_file(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """Rollback file using global backup manager"""
    manager = get_backup_manager()
    return manager.rollback_file(file_path)


def validate_rollback_possible(file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
    """Validate if rollback is possible using global backup manager"""
    manager = get_backup_manager()
    return manager.validate_rollback_possible(file_path)


def get_rollback_preview(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Get rollback preview using global backup manager"""
    manager = get_backup_manager()
    return manager.get_rollback_preview(file_path)


def get_memory_status() -> Dict[str, float]:
    """Get memory status from global manager"""
    manager = get_backup_manager()
    return manager.get_memory_usage()
