"""
Core Index - Linus式数据结构 (Phase 1 最终版)

严格<200行，按照plans.md要求: 单一数据结构
"简单是终极的复杂" - Leonardo da Vinci
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

    这是Phase 1的核心：直接操作数据，无包装器
    """
    base_path: str
    files: Dict[str, FileInfo]
    symbols: Dict[str, SymbolInfo]

    def search(self, query: SearchQuery) -> SearchResult:
        """直接操作数据，无包装器"""
        start_time = time.time()

        # 简单分派
        if query.type == "text":
            matches = self._search_text(query)
        elif query.type == "regex":
            matches = self._search_regex(query)
        elif query.type == "symbol":
            matches = self._search_symbol(query)
        elif query.type == "references":
            matches = self._find_references(query)
        elif query.type == "definition":
            matches = self._find_definition(query)
        elif query.type == "callers":
            matches = self._find_callers(query)
        else:
            matches = []

        return SearchResult(matches=matches, total_count=len(matches), search_time=time.time() - start_time)

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

    # 最简搜索实现 - 核心逻辑留给Phase 2扩展

    def _read_file_lines(self, file_path: str) -> List[str]:
        """读取文件行 - 复用逻辑"""
        from pathlib import Path
        try:
            return (Path(self.base_path) / file_path).read_text(encoding='utf-8', errors='ignore').split('\n')
        except Exception:
            return []

    def _search_text(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """文本搜索 - 最简实现"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for file_path, file_info in self.files.items():
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                search_line = line.lower() if not query.case_sensitive else line
                if pattern in search_line:
                    matches.append({"file": file_path, "line": line_num, "content": line.strip(), "language": file_info.language})
        return matches

    def _search_regex(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """正则搜索 - 最简实现"""
        import re
        try:
            regex = re.compile(query.pattern, 0 if query.case_sensitive else re.IGNORECASE)
        except re.error:
            return []
        matches = []
        for file_path, file_info in self.files.items():
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({"file": file_path, "line": line_num, "content": line.strip(), "language": file_info.language})
        return matches

    def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索 - 最简实现"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for symbol_name, symbol_info in self.symbols.items():
            search_name = symbol_name.lower() if not query.case_sensitive else symbol_name
            if pattern in search_name:
                matches.append({"symbol": symbol_name, "type": symbol_info.type, "file": symbol_info.file, "line": symbol_info.line})
        return matches

    def _find_references(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找引用 - 最简实现"""
        symbol_info = self.symbols.get(query.pattern)
        return [{"file": ref.split(':')[0], "line": int(ref.split(':')[1]), "type": "reference"}
                for ref in (symbol_info.references if symbol_info else []) if ':' in ref]

    def _find_definition(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找定义 - 最简实现"""
        symbol_info = self.symbols.get(query.pattern)
        return [{"file": symbol_info.file, "line": symbol_info.line, "type": "definition"}] if symbol_info else []

    def _find_callers(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找调用者 - 最简实现"""
        symbol_info = self.symbols.get(query.pattern)
        if not symbol_info:
            return []
        matches = []
        for caller in symbol_info.called_by:
            caller_info = self.symbols.get(caller)
            if caller_info:
                matches.append({"symbol": caller, "file": caller_info.file, "line": caller_info.line, "type": "caller"})
        return matches

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