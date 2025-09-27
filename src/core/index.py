"""Linus-style core data structures."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Tuple
import time
import threading
import shutil
import re
from pathlib import Path

if TYPE_CHECKING:
    from .scip import SCIPSymbolManager


@dataclass
class FileInfo:
    language: str
    line_count: int
    symbols: Dict[str, List[str]]
    imports: List[str]
    exports: List[str] = field(default_factory=list)


@dataclass
class SymbolInfo:
    type: str
    file: str
    line: int
    signature: Optional[str] = None
    called_by: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


@dataclass
class SearchQuery:
    pattern: str
    type: str = "text"
    file_pattern: Optional[str] = None
    case_sensitive: bool = True
    limit: Optional[int] = 1000  # Phase 3: 早期退出优化 - 默认最大1000结果


@dataclass
class SearchResult:
    matches: List[Dict[str, Any]]
    total_count: int
    search_time: float


@dataclass
class AtomicEdit:
    """原子编辑操作 - Good Taste: 无特殊情况"""
    file_path: str
    old_content: str
    new_content: str
    backup_path: Optional[str] = None


@dataclass
class EditTransaction:
    """编辑事务 - Linus原则: 要么全成功，要么全失败"""
    edits: List[AtomicEdit]
    rollback_data: List[str] = field(default_factory=list)  # 备份文件路径


@dataclass
class CodeIndex:
    base_path: str
    files: Dict[str, FileInfo]
    symbols: Dict[str, SymbolInfo]
    scip_manager: Optional['SCIPSymbolManager'] = None  # SCIP协议支持

    def __post_init__(self):
        """初始化SCIP管理器 - Linus风格：简单直接"""
        if self.scip_manager is None:
            from .scip import create_scip_manager, integrate_with_code_index
            self.scip_manager = create_scip_manager(self.base_path)
            integrate_with_code_index(self, self.scip_manager)

    def search(self, query: SearchQuery) -> SearchResult:
        from .search_optimized import OptimizedSearchEngine
        return OptimizedSearchEngine(self).search(query)

    def find_symbol(self, name: str) -> List[Dict[str, Any]]:
        return self.search(SearchQuery(pattern=name, type="symbol")).matches

    def add_file(self, file_path: str, file_info: FileInfo):
        self.files[file_path] = file_info

    def add_symbol(self, symbol_name: str, symbol_info: SymbolInfo):
        self.symbols[symbol_name] = symbol_info

    def get_file(self, file_path: str) -> Optional[FileInfo]:
        return self.files.get(file_path)

    def get_symbol(self, symbol_name: str) -> Optional[SymbolInfo]:
        return self.symbols.get(symbol_name)

    def get_stats(self) -> Dict[str, Any]:
        return {"file_count": len(self.files), "symbol_count": len(self.symbols), "base_path": self.base_path}

    def find_files_by_pattern(self, pattern: str) -> List[str]:
        import fnmatch
        return [path for path in self.files.keys() if fnmatch.fnmatch(path, pattern)]

    def update_incrementally(self, root_path: str = None) -> Dict[str, int]:
        """增量更新索引 - Linus原则: 只处理变更文件"""
        from .incremental import get_incremental_indexer
        return get_incremental_indexer().update_index(root_path)
    
    def force_update_file(self, file_path: str) -> bool:
        """强制更新指定文件 - 忽略变更检测"""
        from .incremental import get_incremental_indexer
        return get_incremental_indexer().force_update_file(file_path)
    
    def get_changed_files(self) -> List[str]:
        """获取变更文件列表 - 诊断工具"""
        from .incremental import get_incremental_indexer
        return get_incremental_indexer().get_changed_files()
    
    def remove_file(self, file_path: str) -> None:
        """移除文件索引 - 统一接口"""
        self.files.pop(file_path, None)
        # 移除相关符号
        symbols_to_remove = [
            symbol_name for symbol_name, symbol_info in self.symbols.items()
            if symbol_info.file == file_path
        ]
        for symbol_name in symbols_to_remove:
            self.symbols.pop(symbol_name, None)
    
    # ===== 统一编辑接口 - Good Taste: 消除特殊情况 =====

    def edit_file_atomic(self, file_path: str, old_content: str, new_content: str) -> Tuple[bool, Optional[str]]:
        """原子性文件编辑 - 线程安全 + 索引同步"""
        with _index_lock:
            return self._edit_single_file(file_path, old_content, new_content)

    def edit_files_transaction(self, edits: List[AtomicEdit]) -> Tuple[bool, Optional[str]]:
        """事务性多文件编辑 - 全部成功或全部失败"""
        with _index_lock:
            transaction = EditTransaction(edits=edits)
            return self._execute_transaction(transaction)

    def rename_symbol_atomic(self, old_name: str, new_name: str) -> Tuple[bool, Optional[str], int]:
        """原子性符号重命名 - 跨文件事务操作"""
        with _index_lock:
            if not self._validate_symbol_name(old_name) or not self._validate_symbol_name(new_name):
                return False, "Invalid symbol name", 0

            # 查找所有引用
            refs = self.search(SearchQuery(old_name, "symbol")).matches
            edits = []

            for ref in refs:
                file_path = ref.get("file")
                if not file_path:
                    continue

                full_path = self._resolve_file_path(file_path)
                if not full_path.exists():
                    continue

                old_content = full_path.read_text(encoding='utf-8')
                new_content = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, old_content)

                if old_content != new_content:
                    edits.append(AtomicEdit(
                        file_path=str(full_path),
                        old_content=old_content,
                        new_content=new_content
                    ))

            if not edits:
                return True, None, 0

            success, error = self.edit_files_transaction(edits)
            return success, error, len(edits)

    def add_import_atomic(self, file_path: str, import_statement: str) -> Tuple[bool, Optional[str]]:
        """原子性添加导入 - 智能位置插入"""
        with _index_lock:
            full_path = self._resolve_file_path(file_path)
            if not full_path.exists():
                return False, f"File not found: {file_path}"

            old_content = full_path.read_text(encoding='utf-8')

            # 检查是否已存在
            if import_statement in old_content:
                return True, None  # 已存在，无需操作

            # 智能插入位置
            lines = old_content.splitlines()
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_pos = i + 1

            lines.insert(insert_pos, import_statement)
            new_content = '\n'.join(lines)

            return self._edit_single_file(str(full_path), old_content, new_content)

    # ===== 内部实现 - 直接数据操作 =====

    def _edit_single_file(self, file_path: str, old_content: str, new_content: str) -> Tuple[bool, Optional[str]]:
        """单文件编辑 - 内部方法，假设已持有锁"""
        try:
            file_path_obj = Path(file_path)

            # 验证文件状态
            if not file_path_obj.exists():
                return False, f"File not found: {file_path}"

            current_content = file_path_obj.read_text(encoding='utf-8')

            # 内容验证 - 支持部分匹配
            if old_content and old_content.strip():
                if old_content.strip() not in current_content:
                    return False, f"Content mismatch in {file_path}"

                # 如果是部分匹配，更新为完整替换
                if old_content.strip() != current_content.strip():
                    new_content = current_content.replace(old_content.strip(), new_content)

            # 创建备份
            backup_path = self._create_backup(file_path_obj)
            if not backup_path:
                return False, "Failed to create backup"

            # 原子性写入
            file_path_obj.write_text(new_content, encoding='utf-8')

            # 更新索引 - 关键：保持数据一致性
            self._update_file_in_index(str(file_path_obj))

            return True, None

        except Exception as e:
            return False, f"Edit failed: {e}"

    def _execute_transaction(self, transaction: EditTransaction) -> Tuple[bool, Optional[str]]:
        """执行编辑事务 - 内部方法"""
        # Phase 1: 验证所有操作
        for edit in transaction.edits:
            file_path_obj = Path(edit.file_path)
            if not file_path_obj.exists():
                return False, f"File not found: {edit.file_path}"

            try:
                current_content = file_path_obj.read_text(encoding='utf-8')
                if edit.old_content and edit.old_content.strip() not in current_content:
                    return False, f"Content mismatch in {edit.file_path}"
            except Exception as e:
                return False, f"Validation failed for {edit.file_path}: {e}"

        # Phase 2: 创建所有备份
        for edit in transaction.edits:
            backup_path = self._create_backup(Path(edit.file_path))
            if not backup_path:
                self._rollback_transaction(transaction)
                return False, f"Backup failed for {edit.file_path}"
            edit.backup_path = backup_path
            transaction.rollback_data.append(backup_path)

        # Phase 3: 原子性执行所有编辑
        try:
            for edit in transaction.edits:
                file_path_obj = Path(edit.file_path)
                current_content = file_path_obj.read_text(encoding='utf-8')

                # 处理内容替换
                if edit.old_content and edit.old_content.strip():
                    final_content = current_content.replace(edit.old_content.strip(), edit.new_content)
                else:
                    final_content = edit.new_content

                file_path_obj.write_text(final_content, encoding='utf-8')

                # 更新索引
                self._update_file_in_index(str(file_path_obj))

            return True, None

        except Exception as e:
            # 出错时回滚
            self._rollback_transaction(transaction)
            return False, f"Transaction failed: {e}"

    def _rollback_transaction(self, transaction: EditTransaction) -> None:
        """回滚事务 - 恢复所有文件"""
        for edit in transaction.edits:
            if edit.backup_path and Path(edit.backup_path).exists():
                try:
                    shutil.copy2(edit.backup_path, edit.file_path)
                    self._update_file_in_index(edit.file_path)
                except Exception:
                    pass  # 静默处理回滚错误

    def _create_backup(self, file_path: Path) -> Optional[str]:
        """创建备份文件 - 避免冲突"""
        try:
            backup_dir = file_path.parent / ".edit_backup"
            backup_dir.mkdir(exist_ok=True)

            timestamp = int(time.time() * 1000000)  # 微秒级时间戳避免冲突
            backup_name = f"{file_path.name}.{timestamp}.bak"
            backup_path = backup_dir / backup_name

            shutil.copy2(file_path, backup_path)
            return str(backup_path)

        except Exception:
            return None

    def _update_file_in_index(self, file_path: str) -> None:
        """更新文件索引 - 保持数据一致性"""
        try:
            # 强制重新索引文件
            self.force_update_file(file_path)
        except Exception:
            pass  # 索引更新失败不影响文件编辑

    def _resolve_file_path(self, file_path: str) -> Path:
        """解析文件路径 - 统一路径处理"""
        path_obj = Path(file_path)
        if path_obj.is_absolute():
            return path_obj

        base_path = Path(self.base_path) if self.base_path else Path.cwd()
        return base_path / file_path

    def _validate_symbol_name(self, name: str) -> bool:
        """验证符号名 - 简单正则"""
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name.strip())) if name else False

    # SCIP协议方法 - 由integrate_with_code_index添加
    # find_scip_symbol, get_cross_references, export_scip


_global_index: Optional[CodeIndex] = None
_index_lock = threading.RLock()  # 递归锁支持同一线程多次获取


def get_index() -> CodeIndex:
    """获取全局索引 - 线程安全"""
    with _index_lock:
        if _global_index is None:
            raise RuntimeError("Index not initialized")
        return _global_index


def set_project_path(path: str) -> CodeIndex:
    """设置项目路径 - 线程安全的索引构建"""
    with _index_lock:
        global _global_index
        _global_index = CodeIndex(base_path=path, files={}, symbols={})

        # Linus原则: 一个函数做完整的事情 - 自动构建索引
        from .builder import IndexBuilder
        builder = IndexBuilder(_global_index)
        builder.build_index(path)  # 传递路径参数

        return _global_index


def index_exists() -> bool:
    """检查索引是否存在 - 线程安全"""
    with _index_lock:
        return _global_index is not None