"""
Memory-based Edit Operations

Replaces disk-based backup with in-memory backup system.
Integrates with existing CodeIndex infrastructure.

Design Principles:
- Direct data manipulation - no service abstractions
- Unified interface - compatible with existing CodeIndex
- Performance optimized - minimal overhead
- Memory efficient - LRU eviction with limits
- Thread safe - concurrent operation support
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .backup import apply_edit_with_backup, get_backup_system
from .memory_monitor import check_memory_limits


class MemoryEditOperations:
    """
    Memory-based edit operations that replace disk backup functionality.

    This class provides the same interface as the original disk-based
    edit operations but uses in-memory backup instead.
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path
        self.backup_system = get_backup_system()

    def edit_file_atomic(
        self, file_path: str, old_content: str, new_content: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Atomic file edit with memory backup.

        Replaces the original disk-based backup with memory backup.
        Maintains the same interface for compatibility.

        Args:
            file_path: Path to file to edit
            old_content: Expected current content (for validation)
            new_content: New content to write

        Returns:
            (success, error_message)
        """
        try:
            # Check memory limits first
            memory_ok, memory_error = check_memory_limits("edit_operation")
            if not memory_ok:
                return False, f"Memory limit exceeded: {memory_error}"

            # Validate file path
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return False, f"File not found: {file_path}"

            # Read current content for validation
            try:
                current_content = file_path_obj.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                return False, f"File encoding error: {e}"
            except PermissionError:
                return False, f"Permission denied: {file_path}"

            # Content validation - support partial matching
            if old_content and old_content.strip():
                old_stripped = old_content.strip()
                current_stripped = current_content.strip()

                # Try exact match first
                if old_stripped == current_stripped:
                    validated_new_content = new_content
                # Try partial match
                elif old_stripped in current_stripped:
                    # Update operation to full file replacement
                    if not new_content.strip():
                        # Deletion operation
                        lines = current_content.splitlines()
                        new_lines = []
                        for line in lines:
                            if old_stripped not in line:
                                new_lines.append(line)
                        validated_new_content = "\n".join(new_lines)
                    else:
                        # Replacement operation
                        validated_new_content = current_content.replace(
                            old_stripped, new_content.strip()
                        )
                else:
                    return False, f"Content mismatch - cannot find old_content in {file_path}"
            else:
                validated_new_content = new_content

            # Apply edit with memory backup (includes enhanced rollback)
            success, error = apply_edit_with_backup(
                file_path,
                validated_new_content,
                old_content if old_content and old_content.strip() else None,
            )

            # Enhanced error handling with rollback information
            if not success and error:
                # Check if error contains rollback information
                if "rollback succeeded" in error.lower():
                    # Edit failed but rollback was successful
                    return False, f"Edit failed but file was safely restored: {error}"
                elif "rollback failed" in error.lower():
                    # Both edit and rollback failed - critical error
                    return False, f"CRITICAL: Edit failed and rollback failed: {error}"
                elif "rollback unsafe" in error.lower():
                    # Rollback was prevented for safety reasons
                    return False, f"Edit failed and rollback unsafe: {error}"
                else:
                    # Standard edit failure
                    return False, f"Edit operation failed: {error}"

            return success, error

        except Exception as e:
            # Enhanced exception handling with rollback attempt
            try:
                # Try to use global rollback mechanism as last resort
                from .edit_models import rollback_file

                rollback_success, rollback_error = rollback_file(file_path)
                if rollback_success:
                    return False, f"Edit operation failed but emergency rollback succeeded: {e}"
                else:
                    return (
                        False,
                        f"CRITICAL: Edit operation failed and emergency rollback failed: {e}. Rollback error: {rollback_error}",
                    )
            except ImportError:
                # Fallback if rollback module not available
                return False, f"Edit operation failed: {e}"
            except Exception as rollback_exc:
                return (
                    False,
                    f"CRITICAL: Edit operation failed and emergency rollback failed: {e}. Emergency rollback error: {rollback_exc}",
                )

    def edit_files_atomic(self, edits: List[Tuple[str, str, str]]) -> Tuple[bool, Optional[str]]:
        """
        Atomic multi-file edit with memory backup.

        Args:
            edits: List of (file_path, old_content, new_content) tuples

        Returns:
            (success, error_message)
        """
        # Check memory limits for batch operation
        memory_ok, memory_error = check_memory_limits("batch_edit_operation")
        if not memory_ok:
            return False, f"Memory limit exceeded: {memory_error}"

        # Validate all files first (fail fast)
        for file_path, old_content, new_content in edits:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return False, f"File not found: {file_path}"

        # Apply edits sequentially with memory backup
        successful_edits: List[str] = []
        failed_edits: List[Tuple[str, str]] = []
        try:
            for file_path, old_content, new_content in edits:
                success, error = self.edit_file_atomic(file_path, old_content, new_content)
                if not success:
                    failed_edits.append((file_path, str(error)))
                    # Enhanced rollback for successful edits
                    rollback_errors = []
                    for edited_file in successful_edits:
                        try:
                            # Use enhanced rollback mechanism
                            from .edit_models import rollback_file

                            rollback_success, rollback_error = rollback_file(edited_file)
                            if not rollback_success:
                                rollback_errors.append(f"{edited_file}: {rollback_error}")
                        except ImportError:
                            # Fallback to backup system restore
                            try:
                                self.backup_system.restore_file(edited_file)
                            except Exception:
                                rollback_errors.append(f"{edited_file}: fallback rollback failed")
                        except Exception as rollback_exc:
                            rollback_errors.append(f"{edited_file}: {rollback_exc}")

                    # Construct detailed error message
                    error_msg = f"Edit failed for {file_path}: {error}"
                    if rollback_errors:
                        error_msg += f". Rollback errors: {'; '.join(rollback_errors)}"
                    else:
                        error_msg += ". All successful edits were rolled back."

                    return False, error_msg
                successful_edits.append(file_path)

            return True, None

        except Exception as e:
            # Enhanced rollback on batch exception
            rollback_errors = []
            for edited_file in successful_edits:
                try:
                    # Use enhanced rollback mechanism
                    from .edit_models import rollback_file

                    rollback_success, rollback_error = rollback_file(edited_file)
                    if not rollback_success:
                        rollback_errors.append(f"{edited_file}: {rollback_error}")
                except ImportError:
                    # Fallback to backup system restore
                    try:
                        self.backup_system.restore_file(edited_file)
                    except Exception:
                        rollback_errors.append(f"{edited_file}: fallback rollback failed")
                except Exception as rollback_exc:
                    rollback_errors.append(f"{edited_file}: {rollback_exc}")

            # Construct detailed error message
            error_msg = f"Batch edit failed: {e}"
            if rollback_errors:
                error_msg += f". Rollback errors: {'; '.join(rollback_errors)}"
            elif successful_edits:
                error_msg += ". All successful edits were rolled back."

            return False, error_msg

    def get_backup_status(self) -> Dict[str, Any]:
        """Get current backup system status"""
        return self.backup_system.get_system_status()

    def restore_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Restore file from memory backup.

        Args:
            file_path: Path to file to restore

        Returns:
            (success, error_message)
        """
        try:
            restored = self.backup_system.restore_file(file_path)
            if restored:
                return True, None
            else:
                return False, "No backup found for file"
        except Exception as e:
            return False, f"Restore failed: {e}"

    def cleanup_backups(self, max_age_seconds: float = 3600) -> int:
        """Clean up old backups"""
        return self.backup_system.cleanup_expired_backups(max_age_seconds)


# Global instance for backward compatibility
_global_edit_ops: Optional[MemoryEditOperations] = None


def get_memory_edit_operations(base_path: Optional[str] = None) -> MemoryEditOperations:
    """Get or create global memory edit operations instance"""
    global _global_edit_ops
    if _global_edit_ops is None:
        _global_edit_ops = MemoryEditOperations(base_path)
    return _global_edit_ops


# Compatibility functions for existing code
def edit_file_atomic(
    file_path: str, old_content: str, new_content: str
) -> Tuple[bool, Optional[str]]:
    """Compatibility wrapper for existing code"""
    ops = get_memory_edit_operations()
    return ops.edit_file_atomic(file_path, old_content, new_content)


def edit_files_atomic(edits: List[Tuple[str, str, str]]) -> Tuple[bool, Optional[str]]:
    """Compatibility wrapper for existing code"""
    ops = get_memory_edit_operations()
    return ops.edit_files_atomic(edits)


def get_edit_backup_status() -> Dict[str, Any]:
    """Get backup system status"""
    ops = get_memory_edit_operations()
    return ops.get_backup_status()


def restore_edited_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Restore file from backup"""
    ops = get_memory_edit_operations()
    return ops.restore_file(file_path)
