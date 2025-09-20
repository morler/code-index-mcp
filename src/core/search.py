"""
Search Engine - 搜索实现模块

从index.py中拆分出来的搜索逻辑
按照plans.md要求独立化搜索功能
"""

from typing import Dict, List, Any
import time
from pathlib import Path

from .index import SearchQuery, SearchResult, CodeIndex


class SearchEngine:
    """搜索引擎 - 直接数据操作"""

    def __init__(self, index: CodeIndex):
        self.index = index

    def search(self, query: SearchQuery) -> SearchResult:
        """统一搜索分派"""
        start_time = time.time()

        # 简单分派 - 无特殊情况
        search_methods = {
            "text": self._search_text,
            "regex": self._search_regex,
            "symbol": self._search_symbol,
            "references": self._find_references,
            "definition": self._find_definition,
            "callers": self._find_callers
        }

        search_method = search_methods.get(query.type)
        matches = search_method(query) if search_method else []

        return SearchResult(
            matches=matches,
            total_count=len(matches),
            search_time=time.time() - start_time
        )

    def _read_file_lines(self, file_path: str) -> List[str]:
        """读取文件行 - 复用逻辑"""
        try:
            return (Path(self.index.base_path) / file_path).read_text(encoding='utf-8', errors='ignore').split('\n')
        except Exception:
            return []

    def _search_text(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """文本搜索 - 最简实现"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for file_path, file_info in self.index.files.items():
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                search_line = line.lower() if not query.case_sensitive else line
                if pattern in search_line:
                    matches.append({
                        "file": file_path,
                        "line": line_num,
                        "content": line.strip(),
                        "language": file_info.language
                    })
        return matches

    def _search_regex(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """正则搜索 - 最简实现"""
        import re
        try:
            regex = re.compile(query.pattern, 0 if query.case_sensitive else re.IGNORECASE)
        except re.error:
            return []
        matches = []
        for file_path, file_info in self.index.files.items():
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({
                        "file": file_path,
                        "line": line_num,
                        "content": line.strip(),
                        "language": file_info.language
                    })
        return matches

    def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索 - 最简实现"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for symbol_name, symbol_info in self.index.symbols.items():
            search_name = symbol_name.lower() if not query.case_sensitive else symbol_name
            if pattern in search_name:
                matches.append({
                    "symbol": symbol_name,
                    "type": symbol_info.type,
                    "file": symbol_info.file,
                    "line": symbol_info.line
                })
        return matches

    def _find_references(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找引用 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        return [
            {"file": ref.split(':')[0], "line": int(ref.split(':')[1]), "type": "reference"}
            for ref in (symbol_info.references if symbol_info else [])
            if ':' in ref
        ]

    def _find_definition(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找定义 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        return [{
            "file": symbol_info.file,
            "line": symbol_info.line,
            "type": "definition"
        }] if symbol_info else []

    def _find_callers(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找调用者 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []
        matches = []
        for caller in symbol_info.called_by:
            caller_info = self.index.symbols.get(caller)
            if caller_info:
                matches.append({
                    "symbol": caller,
                    "file": caller_info.file,
                    "line": caller_info.line,
                    "type": "caller"
                })
        return matches