"""
Cross-platform File Locking Mechanism

Provides OS-level file locking for concurrent edit protection.
Supports fcntl on Unix/Linux and LockFileEx on Windows with fallbacks.

Design Principles:
- Direct OS calls - no abstractions
- Cross-platform compatibility
- Automatic cleanup on process termination
- Timeout-based deadlock prevention
- Graceful degradation when locking unavailable
"""

import errno
import os
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, TextIO, Union

# Platform-specific imports
if sys.platform == "win32":
    try:
        import msvcrt

        import pywintypes
        import win32con
        import win32file

        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    try:
        import fcntl

        WIN32_AVAILABLE = False
    except ImportError:
        WIN32_AVAILABLE = False


@dataclass
class LockInfo:
    """File lock information"""

    file_path: str
    lock_type: str  # 'exclusive' or 'shared'
    owner_pid: int
    acquired_at: float
    timeout_seconds: float

    @property
    def age_seconds(self) -> float:
        """Get lock age in seconds"""
        return time.time() - self.acquired_at

    def is_expired(self, max_age_seconds: float = 30.0) -> bool:
        """Check if lock is expired"""
        return self.age_seconds > max_age_seconds


class FileLockError(Exception):
    """Base class for file locking errors"""

    pass


class LockTimeoutError(FileLockError):
    """Raised when lock acquisition times out"""

    pass


class LockAcquisitionError(FileLockError):
    """Raised when lock cannot be acquired"""

    pass


class LockReleaseError(FileLockError):
    """Raised when lock cannot be released"""

    pass


class FileLock:
    """
    Cross-platform file locking implementation

    Features:
    - Exclusive and shared locking modes
    - Timeout-based acquisition
    - Automatic cleanup on process exit
    - Cross-process synchronization
    - Deadlock prevention
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        lock_type: str = "exclusive",
        timeout_seconds: float = 30.0,
        retry_interval: float = 0.1,
    ):
        self.file_path = Path(file_path)
        self.lock_type = lock_type.lower()
        self.timeout_seconds = timeout_seconds
        self.retry_interval = retry_interval

        # Lock state
        self._locked = False
        self._lock_file: Optional[TextIO] = None
        self._lock_info: Optional[LockInfo] = None
        self._platform_lock: Any = None

        # Thread safety
        self._lock = threading.RLock()

        # Validate lock type
        if self.lock_type not in ("exclusive", "shared"):
            raise ValueError(
                f"Invalid lock type: {self.lock_type}. Must be 'exclusive' or 'shared'"
            )

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire file lock

        Args:
            blocking: Whether to block until lock is acquired
            timeout: Custom timeout (overrides instance timeout)

        Returns:
            True if lock acquired, False otherwise
        """
        with self._lock:
            if self._locked:
                return True  # Already locked by this instance

            timeout = timeout if timeout is not None else self.timeout_seconds
            start_time = time.time()

            while True:
                try:
                    # Attempt to acquire lock
                    if self._try_acquire():
                        self._locked = True
                        self._lock_info = LockInfo(
                            file_path=str(self.file_path),
                            lock_type=self.lock_type,
                            owner_pid=os.getpid(),
                            acquired_at=time.time(),
                            timeout_seconds=timeout,
                        )
                        return True

                except Exception as e:
                    if not self._is_retryable_error(e):
                        raise LockAcquisitionError(f"Failed to acquire lock: {e}")

                # Check timeout
                if not blocking:
                    return False

                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise LockTimeoutError(f"Lock acquisition timed out after {timeout:.1f}s")

                # Wait before retry
                time.sleep(self.retry_interval)

    def release(self) -> None:
        """Release file lock"""
        with self._lock:
            if not self._locked:
                return  # Already released

            try:
                self._try_release()
                self._locked = False
                self._lock_info = None

            except Exception as e:
                raise LockReleaseError(f"Failed to release lock: {e}")
            finally:
                # Cleanup resources
                self._cleanup()

    def is_locked(self) -> bool:
        """Check if lock is held by this instance"""
        with self._lock:
            return self._locked

    def get_lock_info(self) -> Optional[LockInfo]:
        """Get current lock information"""
        with self._lock:
            return self._lock_info

    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()

    def _try_acquire(self) -> bool:
        """Platform-specific lock acquisition attempt"""
        if WIN32_AVAILABLE:
            return self._try_acquire_win32()
        elif sys.platform != "win32":
            return self._try_acquire_fcntl()
        else:
            # Fallback for Windows without win32 modules
            return self._try_acquire_file_based()

    def _try_release(self) -> None:
        """Platform-specific lock release"""
        if WIN32_AVAILABLE:
            self._try_release_win32()
        elif sys.platform != "win32":
            self._try_release_fcntl()
        else:
            # Fallback for Windows without win32 modules
            self._try_release_file_based()

    def _try_acquire_win32(self) -> bool:
        """Windows lock acquisition using LockFileEx"""
        try:
            # Open file handle
            handle = win32file.CreateFile(
                str(self.file_path),
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,  # No sharing
                None,
                win32con.OPEN_ALWAYS,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )

            if handle == win32file.INVALID_HANDLE_VALUE:
                return False

            # Determine lock flags
            if self.lock_type == "exclusive":
                lock_flags = win32con.LOCKFILE_EXCLUSIVE_LOCK
            else:
                lock_flags = 0

            # Try to acquire lock
            overlapped = pywintypes.OVERLAPPED()
            result = win32file.LockFileEx(
                handle,
                lock_flags,
                0,  # Reserved
                0xFFFF0000,  # Lock entire file
                0x0000FFFF,
                overlapped,
            )

            if result:
                self._lock_file = handle
                self._platform_lock = overlapped
                return True
            else:
                win32file.CloseHandle(handle)
                return False

        except Exception:
            return False

    def _try_release_win32(self) -> None:
        """Windows lock release"""
        if self._lock_file:
            try:
                overlapped = pywintypes.OVERLAPPED()
                win32file.UnlockFileEx(
                    self._lock_file,
                    0,  # Reserved
                    0xFFFF0000,  # Unlock entire file
                    0x0000FFFF,
                    overlapped,
                )
                win32file.CloseHandle(self._lock_file)
            except Exception:
                pass  # Best effort cleanup
            finally:
                self._lock_file = None

    def _try_acquire_fcntl(self) -> bool:
        """Unix/Linux lock acquisition using fcntl"""
        if sys.platform == "win32":
            # fcntl not available on Windows
            return False

        try:
            import fcntl

            # Open file
            self._lock_file = open(self.file_path, "r+")

            # Determine lock type
            if self.lock_type == "exclusive":
                lock_type = fcntl.LOCK_EX
            else:
                lock_type = fcntl.LOCK_SH

            # Try to acquire lock (non-blocking)
            fcntl.flock(self._lock_file.fileno(), lock_type | fcntl.LOCK_NB)
            return True

        except (IOError, OSError) as e:
            # Clean up file handle on failure
            if self._lock_file:
                try:
                    self._lock_file.close()
                except Exception:
                    pass
                self._lock_file = None

            # Check if lock would block (already locked)
            if hasattr(e, "errno") and e.errno in (errno.EACCES, errno.EAGAIN):
                return False
            raise
        except Exception:
            # Clean up file handle on any error
            if self._lock_file:
                try:
                    self._lock_file.close()
                except Exception:
                    pass
                self._lock_file = None
            raise

    def _try_release_fcntl(self) -> None:
        """Unix/Linux lock release"""
        if self._lock_file and sys.platform != "win32":
            try:
                import fcntl

                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
            except Exception:
                pass  # Best effort cleanup
            finally:
                self._lock_file = None

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is retryable (temporary)"""
        if WIN32_AVAILABLE and hasattr(win32file, "ERROR_LOCK_VIOLATION"):
            # Windows retryable errors
            retryable_errors = (
                win32file.ERROR_LOCK_VIOLATION,
                win32file.ERROR_SHARING_VIOLATION,
            )
            return getattr(error, "winerror", None) in retryable_errors
        else:
            # Unix retryable errors
            return isinstance(error, (IOError, OSError)) and error.errno in (
                errno.EACCES,
                errno.EAGAIN,
                errno.EINTR,
            )

    def _try_acquire_file_based(self) -> bool:
        """File-based lock acquisition (fallback for Windows without win32)"""
        try:
            lock_file_path = self.file_path.with_suffix(self.file_path.suffix + ".lock")

            # Check if lock file already exists
            if lock_file_path.exists():
                # Check if lock is stale (older than 30 seconds)
                lock_age = time.time() - lock_file_path.stat().st_mtime
                if lock_age < 30.0:
                    return False  # Lock is active
                else:
                    # Remove stale lock file
                    try:
                        lock_file_path.unlink()
                    except Exception:
                        return False

            # Create lock file with PID
            lock_content = f"{os.getpid()}\n{time.time()}\n{self.lock_type}\n"
            lock_file_path.write_text(lock_content)

            # Double-check that we created it (race condition protection)
            content = lock_file_path.read_text()
            if content.startswith(str(os.getpid())):
                # Don't assign Path to TextIO variable
                return True
            else:
                # Race condition - another process got there first
                try:
                    lock_file_path.unlink()
                except Exception:
                    pass
                return False

        except Exception:
            return False

    def _try_release_file_based(self) -> None:
        """File-based lock release (fallback)"""
        if self._lock_file:
            try:
                if isinstance(self._lock_file, Path):
                    # It's a lock file path
                    if self._lock_file.exists():
                        content = self._lock_file.read_text()
                        if content.startswith(str(os.getpid())):
                            self._lock_file.unlink()
                else:
                    # It's a file handle
                    self._lock_file.close()
            except Exception:
                pass  # Best effort cleanup
            finally:
                self._lock_file = None

    def _cleanup(self) -> None:
        """Clean up platform-specific resources"""
        if WIN32_AVAILABLE:
            if self._lock_file:
                try:
                    win32file.CloseHandle(self._lock_file)
                except Exception:
                    pass
                self._lock_file = None
        elif sys.platform != "win32":
            if self._lock_file:
                try:
                    self._lock_file.close()
                except Exception:
                    pass
                self._lock_file = None
        else:
            # File-based cleanup
            self._try_release_file_based()


class LockManager:
    """
    Global lock manager for coordinating file locks across the application

    Features:
    - Track all active locks
    - Prevent deadlocks
    - Cleanup stale locks
    - Lock statistics
    """

    def __init__(self):
        self._locks: dict[str, FileLock] = {}
        self._lock = threading.RLock()

        # Register cleanup on exit
        import atexit

        atexit.register(self.cleanup_all_locks)

    def acquire_lock(
        self, file_path: Union[str, Path], lock_type: str = "exclusive", timeout: float = 30.0
    ) -> FileLock:
        """Acquire or get existing file lock"""
        with self._lock:
            file_key = str(Path(file_path).resolve())

            # Check if lock already exists
            if file_key in self._locks:
                existing_lock = self._locks[file_key]
                if existing_lock.is_locked():
                    if existing_lock.lock_type == lock_type or lock_type == "shared":
                        return existing_lock
                    else:
                        raise LockAcquisitionError(
                            f"File already locked with incompatible type: {existing_lock.lock_type}"
                        )
                else:
                    # Remove stale lock
                    del self._locks[file_key]

            # Create new lock
            new_lock = FileLock(file_path, lock_type, timeout)
            new_lock.acquire()
            self._locks[file_key] = new_lock
            return new_lock

    def release_lock(self, file_path: Union[str, Path]) -> None:
        """Release specific file lock"""
        with self._lock:
            file_key = str(Path(file_path).resolve())
            if file_key in self._locks:
                lock = self._locks[file_key]
                lock.release()
                del self._locks[file_key]

    def cleanup_all_locks(self) -> None:
        """Release all locks (called on exit)"""
        with self._lock:
            for lock in self._locks.values():
                try:
                    lock.release()
                except Exception:
                    pass  # Best effort
            self._locks.clear()

    def get_lock_statistics(self) -> Dict[str, Any]:
        """Get statistics about active locks"""
        with self._lock:
            stats: Dict[str, Any] = {
                "total_locks": len(self._locks),
                "exclusive_locks": 0,
                "shared_locks": 0,
                "locks": [],
            }

            for file_key, lock in self._locks.items():
                if lock.is_locked():
                    lock_info = lock.get_lock_info()
                    if lock_info:
                        stats["locks"].append(
                            {
                                "file": file_key,
                                "type": lock_info.lock_type,
                                "owner_pid": lock_info.owner_pid,
                                "age_seconds": lock_info.age_seconds,
                            }
                        )

                        if lock_info.lock_type == "exclusive":
                            stats["exclusive_locks"] += 1
                        else:
                            stats["shared_locks"] += 1

            return stats

    def cleanup_stale_locks(self, max_age_seconds: float = 300.0) -> int:
        """Clean up stale locks (older than max_age_seconds)"""
        with self._lock:
            stale_count = 0
            stale_keys = []

            for file_key, lock in self._locks.items():
                if lock.is_locked():
                    lock_info = lock.get_lock_info()
                    if lock_info and lock_info.is_expired(max_age_seconds):
                        stale_keys.append(file_key)

            for file_key in stale_keys:
                try:
                    self._locks[file_key].release()
                    del self._locks[file_key]
                    stale_count += 1
                except Exception:
                    pass  # Best effort

            return stale_count


# Global lock manager instance
_global_lock_manager: Optional[LockManager] = None


def get_lock_manager() -> LockManager:
    """Get or create global lock manager"""
    global _global_lock_manager
    if _global_lock_manager is None:
        _global_lock_manager = LockManager()
    return _global_lock_manager


# Convenience functions
def acquire_file_lock(
    file_path: Union[str, Path], lock_type: str = "exclusive", timeout: float = 30.0
) -> FileLock:
    """Acquire file lock using global manager"""
    manager = get_lock_manager()
    return manager.acquire_lock(file_path, lock_type, timeout)


def release_file_lock(file_path: Union[str, Path]) -> None:
    """Release file lock using global manager"""
    manager = get_lock_manager()
    manager.release_lock(file_path)


def is_file_locked(file_path: Union[str, Path]) -> bool:
    """Check if file is currently locked"""
    file_path = Path(file_path)

    # Check for file-based locks (Windows fallback)
    if sys.platform == "win32" and not WIN32_AVAILABLE:
        lock_file_path = file_path.with_suffix(file_path.suffix + ".lock")
        if lock_file_path.exists():
            # Check if lock is stale
            lock_age = time.time() - lock_file_path.stat().st_mtime
            return lock_age < 30.0
        return False

    # For other platforms, try to acquire lock
    try:
        lock = FileLock(file_path, timeout_seconds=0.1)
        acquired = lock.acquire(blocking=False)
        if acquired:
            lock.release()
        return not acquired
    except Exception:
        return True  # Assume locked on error


# Context manager convenience
@contextmanager
def file_lock(file_path: Union[str, Path], lock_type: str = "exclusive", timeout: float = 30.0):
    """Context manager for file locking"""
    lock = acquire_file_lock(file_path, lock_type, timeout)
    try:
        yield lock
    finally:
        release_file_lock(file_path)
