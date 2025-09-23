"""
Search Engine - Linus风格重构版本

Phase 3并行搜索引擎 - 符合200行限制
"""

from typing import Dict, List, Any
import time
import re
from pathlib import Path

from .index import SearchQuery, SearchResult, CodeIndex
from .search_parallel import ParallelSearchMixin
from .search_cache import SearchCacheMixin


class SearchEngine(ParallelSearchMixin, SearchCacheMixin):
    """搜索引擎 - Linus风格组合设计"""

    def __init__(self, index: CodeIndex):
        ParallelSearchMixin.__init__(self, index)
        SearchCacheMixin.__init__(self, index)

    def search(self, query: SearchQuery) -> SearchResult:
        """统一搜索分派 - Phase 3优化版本"""
        start_time = time.time()

        # Phase 3: 搜索结果缓存
        cache_key = self.get_cache_key(query)
        cached_result = self.get_cached_result(cache_key)
        if cached_result:
            return cached_result

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

        # Phase 3: 早期退出优化
        if query.limit and len(matches) > query.limit:
            matches = matches[:query.limit]

        result = SearchResult(
            matches=matches,
            total_count=len(matches),
            search_time=time.time() - start_time
        )

        # 缓存结果
        self.cache_result(cache_key, result)
        return result

    def _search_text(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """文本搜索 - 智能单/多线程选择"""
        file_count = len(self.index.files)

        if self._should_use_parallel(file_count):
            return self.search_text_parallel(query)
        else:
            return self._search_text_single(query)

    def _search_text_single(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """单线程文本搜索"""
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
                    if query.limit and len(matches) >= query.limit:
                        return matches
        return matches

    def _search_regex(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """正则搜索 - 智能单/多线程选择"""
        try:
            regex = re.compile(query.pattern, 0 if query.case_sensitive else re.IGNORECASE)
        except re.error:
            return []

        file_count = len(self.index.files)

        if self._should_use_parallel(file_count):
            return self.search_regex_parallel(query, regex)
        else:
            return self._search_regex_single(query, regex)

    def _search_regex_single(self, query: SearchQuery, regex) -> List[Dict[str, Any]]:
        """单线程正则搜索"""
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
                    if query.limit and len(matches) >= query.limit:
                        return matches
        return matches

    def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索 - 直接数据访问"""
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
                if query.limit and len(matches) >= query.limit:
                    break
        return matches

    def _find_references(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找引用 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []
        return [
            {"file": ref.split(':')[0], "line": int(ref.split(':')[1]), "type": "reference"}
            for ref in symbol_info.references
            if ':' in ref
        ][:query.limit] if query.limit else [
            {"file": ref.split(':')[0], "line": int(ref.split(':')[1]), "type": "reference"}
            for ref in symbol_info.references
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
                if query.limit and len(matches) >= query.limit:
                    break
        return matches