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
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .backup import apply_edit_with_backup, get_backup_system
from .memory_monitor import check_memory_limits

# Constants for content validation
TAB_TO_SPACES = 4  # 制表符转空格数量
MAX_ERROR_PREVIEW = 100  # 错误信息预览长度
MAX_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB 最大内容大小限制
PARTIAL_MATCH_THRESHOLD = 0.8  # 部分匹配阈值


def normalize_whitespace(content: str) -> str:
    """
    标准化空白字符，处理换行符、制表符和空格的差异。

    Args:
        content: 原始内容

    Returns:
        标准化后的内容
    """
    # 标准化换行符为 LF
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")

    # 将制表符转换为空格（使用常量）
    tab_spaces = " " * TAB_TO_SPACES
    normalized = normalized.replace("\t", tab_spaces)

    # 标准化行尾空白字符
    lines = normalized.split("\n")
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)


def calculate_line_position(lines: List[str], line_index: int) -> int:
    """
    计算指定行在原始内容中的字节位置。

    Args:
        lines: 行列表
        line_index: 行索引

    Returns:
        字节位置
    """
    position = 0
    for i in range(line_index):
        position += len(lines[i].encode("utf-8")) + len("\n")
    return position


def validate_content_safely(
    content: str, search_content: str
) -> Tuple[bool, Optional[str]]:
    """
    安全验证内容，包含大小限制和基本检查。

    Args:
        content: 完整内容
        search_content: 要搜索的内容

    Returns:
        (is_safe, error_message)
    """
    if len(content.encode("utf-8")) > MAX_CONTENT_SIZE:
        return (
            False,
            f"Content too large for validation (max {MAX_CONTENT_SIZE // (1024 * 1024)}MB)",
        )

    if not search_content.strip():
        return True, None

    return True, None


def find_content_match(
    content: str, search_content: str
) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    查找内容匹配，支持灵活的空白字符处理。

    Args:
        content: 完整内容
        search_content: 要搜索的内容

    Returns:
        (found, error_message, match_position)
    """
    # 安全检查
    is_safe, error_msg = validate_content_safely(content, search_content)
    if not is_safe:
        return False, error_msg, None

    if not search_content.strip():
        return True, None, None

    # 首先尝试精确匹配
    exact_pos = content.find(search_content)
    if exact_pos != -1:
        return True, None, exact_pos

    # 预计算标准化内容（避免重复计算）
    normalized_content = normalize_whitespace(content)
    normalized_search = normalize_whitespace(search_content)

    # 尝试标准化匹配
    norm_pos = normalized_content.find(normalized_search)
    if norm_pos != -1:
        # 在原始内容中找到对应位置
        original_lines = content.split("\n")
        search_lines = search_content.split("\n")

        # 使用辅助函数计算位置
        match_pos = _find_original_position(
            original_lines, search_lines, normalized_search
        )
        if match_pos is not None:
            return True, None, match_pos

        # 如果逐行匹配失败，使用标准化位置
        return True, None, norm_pos

    # 尝试部分匹配（用于删除操作）
    partial_pos = _find_partial_match(content, search_content)
    if partial_pos is not None:
        return True, None, partial_pos

    # 生成详细的错误信息
    return False, _generate_error_details(content, search_content), None


def _find_original_position(
    original_lines: List[str], search_lines: List[str], normalized_search: str
) -> Optional[int]:
    """
    在原始内容中找到标准化匹配的位置。

    Args:
        original_lines: 原始内容行列表
        search_lines: 搜索内容行列表
        normalized_search: 标准化后的搜索内容

    Returns:
        匹配位置或None
    """
    # 预计算所有可能的候选位置的标准化内容
    for i in range(len(original_lines) - len(search_lines) + 1):
        match_candidate = "\n".join(original_lines[i : i + len(search_lines)])
        if normalize_whitespace(match_candidate) == normalized_search:
            return calculate_line_position(original_lines, i)

    return None


def _find_partial_match(content: str, search_content: str) -> Optional[int]:
    """
    查找部分匹配，用于删除操作。

    Args:
        content: 完整内容
        search_content: 搜索内容

    Returns:
        匹配位置或None
    """
    search_lines = [line.strip() for line in search_content.split("\n") if line.strip()]
    if not search_lines:
        return None

    content_lines = content.split("\n")

    for i in range(len(content_lines) - len(search_lines) + 1):
        content_section = content_lines[i : i + len(search_lines)]

        # 更严格的匹配条件：检查相似度
        matches = 0
        for search_line, content_line in zip(search_lines, content_section):
            if search_line in content_line:
                matches += 1

        # 只有当匹配度达到阈值时才认为找到匹配
        if matches / len(search_lines) >= PARTIAL_MATCH_THRESHOLD:
            return calculate_line_position(content_lines, i)

    return None


def _generate_error_details(content: str, search_content: str) -> str:
    """
    生成详细的错误信息。

    Args:
        content: 完整内容
        search_content: 搜索内容

    Returns:
        错误信息字符串
    """
    error_lines = []
    error_lines.append("Content mismatch details:")
    error_lines.append(
        f"Expected content (first {MAX_ERROR_PREVIEW} chars): {repr(search_content[:MAX_ERROR_PREVIEW])}"
    )
    error_lines.append(
        f"Actual content (first {MAX_ERROR_PREVIEW} chars): {repr(content[:MAX_ERROR_PREVIEW])}"
    )

    if search_content.strip() not in content:
        error_lines.append("Search content not found in file")

    return "\n".join(error_lines)


def _process_edit_operation(
    current_content: str, old_content: str, new_content: str, match_pos: Optional[int]
) -> str:
    """
    处理编辑操作（删除或替换）。

    Args:
        current_content: 当前文件内容
        old_content: 要替换的旧内容
        new_content: 新内容
        match_pos: 匹配位置

    Returns:
        处理后的内容
    """
    if not new_content.strip():
        # 删除操作
        if match_pos is not None:
            # 精确删除：使用匹配位置和实际找到的内容长度
            actual_old_content = _extract_content_at_position(
                current_content, old_content, match_pos
            )
            before = current_content[:match_pos]
            after = current_content[match_pos + len(actual_old_content) :]
            return before + after
        else:
            # 回退：删除所有出现
            return current_content.replace(old_content, "")
    else:
        # 替换操作
        if match_pos is not None:
            # 精确替换
            actual_old_content = _extract_content_at_position(
                current_content, old_content, match_pos
            )
            before = current_content[:match_pos]
            after = current_content[match_pos + len(actual_old_content) :]
            return before + new_content + after
        else:
            # 回退：简单替换
            return current_content.replace(old_content, new_content)


def _extract_content_at_position(
    content: str, expected_content: str, position: int
) -> str:
    """
    在指定位置提取实际匹配的内容。

    Args:
        content: 完整内容
        expected_content: 期望的内容
        position: 位置

    Returns:
        实际匹配的内容
    """
    # 尝试提取期望长度的内容
    end_pos = position + len(expected_content)
    if end_pos <= len(content):
        extracted = content[position:end_pos]
        # 检查是否匹配（考虑标准化）
        if normalize_whitespace(extracted) == normalize_whitespace(expected_content):
            return extracted

    # 如果不匹配，尝试找到最佳匹配
    lines = content[position:].split("\n")
    expected_lines = expected_content.split("\n")

    best_match = ""
    for i in range(min(len(lines), len(expected_lines) + 2)):  # 允许一些额外行
        candidate = "\n".join(lines[: i + 1])
        if normalize_whitespace(candidate).startswith(
            normalize_whitespace(expected_lines[0])
        ):
            best_match = candidate
        else:
            break

    return best_match or expected_content


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

            # Enhanced content validation with flexible whitespace handling
            if old_content and old_content.strip():
                # Use enhanced content matching
                found, error_msg, match_pos = find_content_match(
                    current_content, old_content
                )

                if not found:
                    return (
                        False,
                        f"Content validation failed for {file_path}:\n{error_msg}",
                    )

                # Process the edit operation with enhanced precision
                validated_new_content = _process_edit_operation(
                    current_content, old_content, new_content, match_pos
                )
            else:
                validated_new_content = new_content

            # Apply edit with memory backup (skip validation since we already did it)
            success, error = apply_edit_with_backup(
                file_path,
                validated_new_content,
                None,  # Skip validation in backup system
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
                    return (
                        False,
                        f"Edit operation failed but emergency rollback succeeded: {e}",
                    )
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

    def edit_files_atomic(
        self, edits: List[Tuple[str, str, str]]
    ) -> Tuple[bool, Optional[str]]:
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
                success, error = self.edit_file_atomic(
                    file_path, old_content, new_content
                )
                if not success:
                    failed_edits.append((file_path, str(error)))
                    # Enhanced rollback for successful edits
                    rollback_errors = []
                    for edited_file in successful_edits:
                        try:
                            # Use enhanced rollback mechanism
                            from .edit_models import rollback_file

                            rollback_success, rollback_error = rollback_file(
                                edited_file
                            )
                            if not rollback_success:
                                rollback_errors.append(
                                    f"{edited_file}: {rollback_error}"
                                )
                        except ImportError:
                            # Fallback to backup system restore
                            try:
                                self.backup_system.restore_file(edited_file)
                            except Exception:
                                rollback_errors.append(
                                    f"{edited_file}: fallback rollback failed"
                                )
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
                        rollback_errors.append(
                            f"{edited_file}: fallback rollback failed"
                        )
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
