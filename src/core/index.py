"""Linus-style core data structures."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import time
import threading

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


@dataclass
class SearchResult:
    matches: List[Dict[str, Any]]
    total_count: int
    search_time: float


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