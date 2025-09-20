"""
Core Index - Linus式核心数据结构

精简版本：只包含数据结构和基本操作
按照plans.md要求拆分为独立模块
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time


@dataclass
class FileInfo:
    """文件信息 - 核心数据"""
    language: str
    line_count: int
    symbols: Dict[str, List[str]]
    imports: List[str]
    exports: List[str] = field(default_factory=list)


@dataclass
class SymbolInfo:
    """符号信息 - 核心数据"""
    type: str
    file: str
    line: int
    signature: Optional[str] = None
    called_by: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


@dataclass
class SearchQuery:
    """统一搜索接口 - 消除特殊情况"""
    pattern: str
    type: str = "text"
    file_pattern: Optional[str] = None
    case_sensitive: bool = True


@dataclass
class SearchResult:
    """统一搜索结果"""
    matches: List[Dict[str, Any]]
    total_count: int
    search_time: float


@dataclass
class CodeIndex:
    """
    统一数据结构 - 消除所有抽象层

    核心数据操作，搜索逻辑分离到search.py
    """
    base_path: str
    files: Dict[str, FileInfo]
    symbols: Dict[str, SymbolInfo]

    def search(self, query: SearchQuery) -> SearchResult:
        """统一搜索入口 - 委托给搜索引擎"""
        from .search import SearchEngine
        return SearchEngine(self).search(query)

    def find_symbol(self, name: str) -> List[Dict[str, Any]]:
        """统一接口，无特殊情况"""
        return self.search(SearchQuery(pattern=name, type="symbol")).matches

    def add_file(self, file_path: str, file_info: FileInfo):
        """直接数据插入"""
        self.files[file_path] = file_info

    def add_symbol(self, symbol_name: str, symbol_info: SymbolInfo):
        """直接符号插入"""
        self.symbols[symbol_name] = symbol_info

    def get_file(self, file_path: str) -> Optional[FileInfo]:
        """直接数据访问"""
        return self.files.get(file_path)

    def get_symbol(self, symbol_name: str) -> Optional[SymbolInfo]:
        """直接符号访问"""
        return self.symbols.get(symbol_name)

    def get_stats(self) -> Dict[str, Any]:
        """直接统计信息"""
        return {"file_count": len(self.files), "symbol_count": len(self.symbols), "base_path": self.base_path}

    def find_files_by_pattern(self, pattern: str) -> List[str]:
        """直接文件模式匹配"""
        import fnmatch
        return [path for path in self.files.keys() if fnmatch.fnmatch(path, pattern)]


# 全局索引 - Linus式单例
_global_index: Optional[CodeIndex] = None


def get_index() -> CodeIndex:
    """获取全局索引"""
    global _global_index
    if _global_index is None:
        raise RuntimeError("Index not initialized")
    return _global_index


def set_project_path(path: str) -> CodeIndex:
    """设置项目路径 - 初始化索引"""
    global _global_index
    _global_index = CodeIndex(base_path=path, files={}, symbols={})
    return _global_index


def index_exists() -> bool:
    """检查索引是否存在"""
    return _global_index is not None