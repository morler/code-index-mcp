"""
Search Cache - Phase 3搜索缓存模块

Linus风格拆分 - 专注缓存逻辑
"""

import hashlib
from pathlib import Path
from typing import Dict
from functools import lru_cache

from .index import SearchQuery, SearchResult, CodeIndex


class SearchCacheMixin:
    """搜索缓存混入 - Linus风格模块化"""

    def __init__(self, index: CodeIndex):
        self.index = index
        self._result_cache = {}

    def get_cache_key(self, query: SearchQuery) -> str:
        """生成缓存键 - 查询hash + 文件签名"""
        query_str = f"{query.type}:{query.pattern}:{query.case_sensitive}"
        query_hash = hashlib.md5(query_str.encode()).hexdigest()

        # 文件签名 - 基于mtime和size的快速hash
        file_sigs = []
        for file_path, file_info in self.index.files.items():
            try:
                stat = (Path(self.index.base_path) / file_path).stat()
                file_sigs.append(f"{stat.st_mtime}:{stat.st_size}")
            except:
                file_sigs.append("0:0")

        files_hash = hashlib.md5("|".join(sorted(file_sigs)).encode()).hexdigest()[:8]
        return f"{query_hash}:{files_hash}"

    def get_cached_result(self, cache_key: str) -> SearchResult:
        """获取缓存结果"""
        return self._result_cache.get(cache_key)

    def cache_result(self, cache_key: str, result: SearchResult):
        """缓存搜索结果"""
        # 简单LRU - 最多缓存100个结果
        if len(self._result_cache) >= 100:
            # 删除最旧的缓存
            oldest_key = next(iter(self._result_cache))
            del self._result_cache[oldest_key]

        self._result_cache[cache_key] = result

    @lru_cache(maxsize=100)
    def search_cached(self, query_hash: str, file_signatures: tuple):
        """LRU缓存装饰器 - 基于文件签名"""
        # 实际缓存逻辑在cache_result中处理
        return None