"""
Search Engine - Linus式性能优化版本

核心优化：
1. 文件内容缓存 - 避免重复I/O
2. 索引基础搜索 - 直接数据操作
3. 早期终止 - 减少无效计算
"""

from typing import Dict, List, Any, Optional
import time
import re
from pathlib import Path
from functools import lru_cache

from .index import SearchQuery, SearchResult, CodeIndex
from .cache import get_file_cache


class OptimizedSearchEngine:
    """优化搜索引擎 - 直接数据操作 + Linus风格缓存"""

    def __init__(self, index: CodeIndex):
        self.index = index
        self.file_cache = get_file_cache()  # 使用全局优化缓存

    def search(self, query: SearchQuery) -> SearchResult:
        """统一搜索分派 - 零分支"""
        start_time = time.time()

        # 优化的操作注册表 - 按plans.md要求完整实现
        search_ops = {
            "text": self._search_text_optimized,
            "regex": self._search_regex_optimized,
            "symbol": self._search_symbol_direct,
            "references": self._find_references_direct,
            "definition": self._find_definition_direct,
            "callers": self._find_callers_direct,
            "implementations": self._find_implementations_direct,
            "hierarchy": self._find_hierarchy_direct
        }

        search_method = search_ops.get(query.type, lambda q: [])
        matches = search_method(query)

        return SearchResult(
            matches=matches,
            total_count=len(matches),
            search_time=time.time() - start_time
        )

    def _get_file_lines(self, file_path: str) -> List[str]:
        """获取文件行 - 使用优化缓存"""
        return self.file_cache.get_file_lines(file_path)

    @lru_cache(maxsize=500)
    def _get_regex_cached(self, pattern: str, case_sensitive: bool) -> Optional[re.Pattern]:
        """LRU缓存正则表达式编译 - Linus风格内存优化"""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(pattern, flags)
        except re.error:
            return None

    def _get_regex(self, pattern: str, case_sensitive: bool) -> Optional[re.Pattern]:
        """获取正则表达式 - 使用LRU缓存"""
        return self._get_regex_cached(pattern, case_sensitive)

    def _search_text_optimized(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """优化文本搜索 - 预处理 + 早期终止"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []

        for file_path, file_info in self.index.files.items():
            # 文件模式过滤
            if query.file_pattern and not self._match_file_pattern(file_path, query.file_pattern):
                continue

            lines = self._get_file_lines(file_path)
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

    def _search_regex_optimized(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """优化正则搜索 - 缓存编译结果"""
        regex = self._get_regex(query.pattern, query.case_sensitive)
        if not regex:
            return []

        matches = []
        for file_path, file_info in self.index.files.items():
            if query.file_pattern and not self._match_file_pattern(file_path, query.file_pattern):
                continue

            lines = self._get_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append({
                        "file": file_path,
                        "line": line_num,
                        "content": line.strip(),
                        "language": file_info.language
                    })
        return matches

    def _search_symbol_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索 - 直接索引访问"""
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

    def _find_references_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """语义搜索 - 委托给语义操作模块"""
        from .semantic_ops import SemanticOperations
        return SemanticOperations(self.index).find_references_direct(query)

    def _find_definition_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """语义搜索 - 委托给语义操作模块"""
        from .semantic_ops import SemanticOperations
        return SemanticOperations(self.index).find_definition_direct(query)

    def _find_callers_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """语义搜索 - 委托给语义操作模块"""
        from .semantic_ops import SemanticOperations
        return SemanticOperations(self.index).find_callers_direct(query)

    def _find_implementations_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """语义搜索 - 委托给语义操作模块"""
        from .semantic_ops import SemanticOperations
        return SemanticOperations(self.index).find_implementations_direct(query)

    def _find_hierarchy_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """语义搜索 - 委托给语义操作模块"""
        from .semantic_ops import SemanticOperations
        return SemanticOperations(self.index).find_hierarchy_direct(query)

    def _match_file_pattern(self, file_path: str, pattern: str) -> bool:
        """文件模式匹配 - 简单实现"""
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)

    def clear_cache(self):
        """清理缓存 - 内存管理"""
        self.file_cache.clear_cache()
        self._get_regex_cached.cache_clear()  # 清理LRU缓存
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        regex_info = self._get_regex_cached.cache_info()
        return {
            "file_cache": self.file_cache.get_cache_stats(),
            "regex_cache": {
                "hits": regex_info.hits,
                "misses": regex_info.misses,
                "current_size": regex_info.currsize,
                "max_size": regex_info.maxsize
            }
        }