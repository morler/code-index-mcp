"""
DEPRECATED: 此文件已弃用

所有编辑功能已迁移到src/core/index.py的CodeIndex类中：
- edit_file_atomic() - 原子性文件编辑
- edit_files_transaction() - 事务性多文件编辑
- rename_symbol_atomic() - 原子性符号重命名
- add_import_atomic() - 原子性导入添加

新实现具有以下优势：
1. 线程安全 - 统一锁机制
2. 事务保证 - 全部成功或全部失败
3. 索引同步 - 编辑后自动更新索引
4. 无竞争条件 - 所有操作通过单一入口

请使用: index.edit_file_atomic() 等新方法
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import os
import re
import shutil
import time
from pathlib import Path

from .index import get_index, SearchQuery
from .builder import handle_edit_errors


@dataclass
class EditOperation:
    """编辑操作 - 纯数据，无方法"""
    file_path: str
    old_content: str
    new_content: str
    backup_path: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class EditResult:
    """编辑结果 - 直接数据访问"""
    success: bool
    operations: List[EditOperation]
    error: Optional[str] = None
    files_changed: int = 0


@handle_edit_errors
def rename_symbol(old_name: str, new_name: str) -> EditResult:
    """重命名符号 - 跨文件操作"""
    if not _validate_symbol_name(old_name) or not _validate_symbol_name(new_name):
        return EditResult(False, [], "Invalid symbol name")

    index = get_index()
    operations = []

    # 查找所有引用
    refs = index.search(SearchQuery(old_name, "symbol")).matches

    for ref in refs:
        file_path = ref.get("file")
        if not file_path:
            continue

        # 使用统一路径解析
        base_path = Path(index.base_path) if index.base_path else Path.cwd()
        full_path = Path(file_path) if Path(file_path).is_absolute() else base_path / file_path
        if not full_path.exists():
            continue

        # 读取原始内容
        old_content = full_path.read_text(encoding='utf-8')

        # 简单替换 - 可扩展为AST操作
        new_content = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, old_content)

        if old_content != new_content:
            operations.append(EditOperation(
                file_path=str(full_path),
                old_content=old_content,
                new_content=new_content
            ))

    return EditResult(True, operations, files_changed=len(operations))


@handle_edit_errors
def add_import(file_path: str, import_statement: str) -> EditResult:
    """添加导入 - 直接文件操作"""
    full_path = Path(file_path)
    if not full_path.exists():
        return EditResult(False, [], f"File not found: {file_path}")

    old_content = full_path.read_text(encoding='utf-8')

    # 检查是否已存在
    if import_statement in old_content:
        return EditResult(True, [], "Import already exists")

    # 简单添加到文件开头
    lines = old_content.splitlines()

    # 找到导入区域
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(('import ', 'from ')):
            insert_pos = i + 1

    lines.insert(insert_pos, import_statement)
    new_content = '\n'.join(lines)

    op = EditOperation(
        file_path=str(full_path),
        old_content=old_content,
        new_content=new_content
    )

    # 立即应用编辑
    success, error = apply_edit(op)
    if success:
        return EditResult(True, [op], files_changed=1)
    else:
        return EditResult(False, [op], error or "Failed to write file")


def apply_edit(operation: EditOperation) -> Tuple[bool, Optional[str]]:
    """应用编辑 - 原子操作，返回成功状态和错误信息"""
    try:
        file_path = Path(operation.file_path)

        # 1. 检查文件是否存在
        if not file_path.exists():
            return False, f"File not found: {operation.file_path}"

        # 2. 读取当前文件内容验证
        try:
            current_content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError as e:
            return False, f"File encoding error: {e}"
        except PermissionError:
            return False, f"Permission denied: {operation.file_path}"

        # 3. 验证old_content匹配（支持部分匹配和删除操作）
        if operation.old_content and operation.old_content.strip():
            old_stripped = operation.old_content.strip()
            current_stripped = current_content.strip()

            # 尝试精确匹配
            if old_stripped == current_stripped:
                pass  # 完全匹配，继续
            # 尝试部分匹配 - old_content应该是current_content的子集
            elif old_stripped in current_stripped:
                # 部分匹配成功，更新操作为完整文件替换
                operation.old_content = current_content

                # 处理删除操作（new_content为空）
                if not operation.new_content.strip():
                    # 删除操作：移除匹配的行或内容
                    lines = current_content.splitlines()
                    new_lines = []
                    for line in lines:
                        if old_stripped not in line:
                            new_lines.append(line)
                    operation.new_content = '\n'.join(new_lines)
                else:
                    # 替换操作：在当前内容中替换匹配的部分
                    operation.new_content = current_content.replace(old_stripped, operation.new_content.strip())
            else:
                return False, f"Content mismatch - cannot find old_content in file. File length: {len(current_content)}, search pattern length: {len(operation.old_content)}"

        # 4. 创建备份
        if operation.backup_path is None:
            backup_dir = file_path.parent / ".edit_backup"
            backup_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            backup_name = f"{file_path.name}.{timestamp}.bak"
            operation.backup_path = str(backup_dir / backup_name)

        try:
            shutil.copy2(operation.file_path, operation.backup_path)
        except PermissionError:
            return False, f"Cannot create backup: permission denied for {operation.backup_path}"
        except OSError as e:
            return False, f"Backup creation failed: {e}"

        # 5. 写入新内容
        try:
            file_path.write_text(operation.new_content, encoding='utf-8')
            return True, None
        except PermissionError:
            return False, f"Cannot write file: permission denied for {operation.file_path}"
        except OSError as e:
            return False, f"Write operation failed: {e}"

    except Exception as e:
        return False, f"Unexpected error: {e}"


def rollback_edit(operation: EditOperation) -> bool:
    """回滚编辑 - 直接恢复"""
    try:
        if operation.backup_path and Path(operation.backup_path).exists():
            shutil.copy2(operation.backup_path, operation.file_path)
            return True
        return False
    except Exception:
        return False


def _validate_symbol_name(name: str) -> bool:
    """验证符号名 - 简单正则"""
    return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name.strip())) if name else False


def _generate_diff(old_content: str, new_content: str) -> str:
    """生成差异 - 标准库实现"""
    import difflib
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    return ''.join(difflib.unified_diff(old_lines, new_lines))