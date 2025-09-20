"""
Linus-style semantic editing - 直接数据操作

替代600+行复杂服务，30行解决问题
无包装器，无抽象层，纯数据结构
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import re
import shutil
import time
from pathlib import Path

from .index import get_index, SearchQuery


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


def rename_symbol(old_name: str, new_name: str) -> EditResult:
    """
    符号重命名 - Linus风格直接实现
    消除特殊情况，统一处理逻辑
    """
    if not _validate_symbol_name(new_name):
        return EditResult(False, [], f"Invalid symbol name: {new_name}")

    try:
        index = get_index()
        operations = []

        # 查找所有引用
        refs = index.search(SearchQuery(old_name, "symbol")).matches

        for ref in refs:
            file_path = ref.get("file")
            if not file_path:
                continue

            # 直接文件操作
            full_path = Path(index.base_path) / file_path
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

    except Exception as e:
        return EditResult(False, [], str(e))


def add_import(file_path: str, import_statement: str) -> EditResult:
    """添加导入 - 直接文件操作"""
    try:
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
        if apply_edit(op):
            return EditResult(True, [op], files_changed=1)
        else:
            return EditResult(False, [op], "Failed to write file")

    except Exception as e:
        return EditResult(False, [], str(e))


def apply_edit(operation: EditOperation) -> bool:
    """应用编辑 - 原子操作"""
    try:
        # 创建备份
        if operation.backup_path is None:
            backup_dir = Path(operation.file_path).parent / ".edit_backup"
            backup_dir.mkdir(exist_ok=True)
            timestamp = int(time.time())
            backup_name = f"{Path(operation.file_path).name}.{timestamp}.bak"
            operation.backup_path = str(backup_dir / backup_name)

        shutil.copy2(operation.file_path, operation.backup_path)

        # 写入新内容
        Path(operation.file_path).write_text(operation.new_content, encoding='utf-8')
        return True

    except Exception:
        return False


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