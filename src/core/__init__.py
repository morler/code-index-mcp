"""
Core module - Linus-style unified architecture (Phase 1)

Single data structure, no abstractions.
"""

from .index import CodeIndex, FileInfo, SymbolInfo, SearchQuery, SearchResult
from .index import get_index, set_project_path, index_exists

__all__ = [
    "CodeIndex",
    "FileInfo",
    "SymbolInfo",
    "SearchQuery",
    "SearchResult",
    "get_index",
    "set_project_path",
    "index_exists"
]