"""Linus-style core data structures."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time


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


_global_index: Optional[CodeIndex] = None


def get_index() -> CodeIndex:
    global _global_index
    if _global_index is None:
        raise RuntimeError("Index not initialized")
    return _global_index


def set_project_path(path: str) -> CodeIndex:
    global _global_index
    _global_index = CodeIndex(base_path=path, files={}, symbols={})
    return _global_index


def index_exists() -> bool:
    return _global_index is not None