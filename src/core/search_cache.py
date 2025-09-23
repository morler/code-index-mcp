"""
Phase 4 Query Result Caching - 智能搜索结果缓存

Linus风格直接数据操作 - 文件依赖感知缓存
"""

import hashlib
import time
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from functools import lru_cache

from .index import SearchQuery, SearchResult, CodeIndex


class AdvancedQueryCache:
    """Phase 4: 高级查询结果缓存 - 10x性能提升目标"""

    def __init__(self, max_cache_entries: int = 200):
        # 核心缓存数据 - 直接字典操作
        self._query_cache: Dict[str, SearchResult] = {}
        self._file_dependencies: Dict[str, Set[str]] = {}  # cache_key -> file_paths
        self._file_signatures: Dict[str, str] = {}  # file_path -> signature
        self._access_times: Dict[str, float] = {}  # cache_key -> last_access
        
        # 缓存统计 - 性能监控
        self._cache_hits = 0
        self._cache_misses = 0
        self._invalidations = 0
        self._max_entries = max_cache_entries

    def get_query_result(self, query: SearchQuery, index: CodeIndex) -> Optional[SearchResult]:
        """获取查询缓存结果 - 智能依赖检查"""
        cache_key = self._generate_cache_key(query)
        
        # 检查缓存是否存在
        if cache_key not in self._query_cache:
            self._cache_misses += 1
            return None
        
        # 智能依赖验证 - 只检查相关文件
        if self._is_cache_valid(cache_key, index):
            self._cache_hits += 1
            self._access_times[cache_key] = time.time()
            return self._query_cache[cache_key]
        else:
            # 缓存失效 - 清理
            self._invalidate_cache_entry(cache_key)
            self._cache_misses += 1
            return None

    def cache_query_result(self, query: SearchQuery, result: SearchResult, index: CodeIndex):
        """缓存查询结果 - 记录文件依赖"""
        cache_key = self._generate_cache_key(query)
        
        # LRU清理 - 保持缓存大小限制
        if len(self._query_cache) >= self._max_entries:
            self._evict_least_recently_used()
        
        # 缓存结果和依赖
        self._query_cache[cache_key] = result
        self._access_times[cache_key] = time.time()
        
        # 记录文件依赖 - 用于智能失效
        dependencies = self._extract_file_dependencies(query, result, index)
        self._file_dependencies[cache_key] = dependencies
        
        # 更新文件签名快照
        for file_path in dependencies:
            self._file_signatures[file_path] = self._calculate_file_signature(file_path, index)

    def invalidate_file_changes(self, changed_files: Set[str], index: CodeIndex):
        """文件变更时的智能缓存失效"""
        invalidated_keys = set()
        
        for cache_key, dependencies in self._file_dependencies.items():
            # 检查是否有依赖文件发生变更
            if dependencies.intersection(changed_files):
                invalidated_keys.add(cache_key)
        
        for cache_key in invalidated_keys:
            self._invalidate_cache_entry(cache_key)
            self._invalidations += 1

    def _generate_cache_key(self, query: SearchQuery) -> str:
        """生成查询缓存键 - 精确查询指纹"""
        query_data = {
            'type': query.type,
            'pattern': query.pattern,
            'file_pattern': query.file_pattern,
            'case_sensitive': query.case_sensitive,
            'limit': query.limit
        }
        query_str = "|".join(f"{k}:{v}" for k, v in sorted(query_data.items()))
        return f"query_{hashlib.md5(query_str.encode()).hexdigest()}"

    def _is_cache_valid(self, cache_key: str, index: CodeIndex) -> bool:
        """检查缓存有效性 - 只验证依赖文件"""
        dependencies = self._file_dependencies.get(cache_key, set())
        
        for file_path in dependencies:
            old_signature = self._file_signatures.get(file_path, "")
            current_signature = self._calculate_file_signature(file_path, index)
            
            if old_signature != current_signature:
                return False
        
        return True

    def _calculate_file_signature(self, file_path: str, index: CodeIndex) -> str:
        """计算文件签名 - 复用Phase2超快速策略"""
        try:
            full_path = Path(index.base_path) / file_path
            if not full_path.exists():
                return "deleted"
            
            stat = full_path.stat()
            
            # Phase2策略: 大文件元数据，小文件内容hash
            if stat.st_size >= 10240:  # 10KB threshold
                return f"{stat.st_mtime}:{stat.st_size}:{stat.st_ino}"
            else:
                # 小文件内容hash - 确保准确性
                content = full_path.read_bytes()
                return f"content_{hashlib.md5(content).hexdigest()}"
        except:
            return "error"

    def _extract_file_dependencies(self, query: SearchQuery, result: SearchResult, index: CodeIndex) -> Set[str]:
        """提取查询的文件依赖 - 智能依赖分析"""
        dependencies = set()
        
        # 从结果中提取直接依赖文件
        for match in result.matches:
            if 'file' in match:
                dependencies.add(match['file'])
        
        # 根据查询类型添加额外依赖
        if query.type in ['symbol', 'references', 'definition', 'callers']:
            # 符号查询可能涉及多个文件
            for file_path in index.files.keys():
                if query.file_pattern is None or self._matches_pattern(file_path, query.file_pattern):
                    dependencies.add(file_path)
        elif query.type in ['text', 'regex']:
            # 文本搜索依赖所有匹配的文件
            if query.file_pattern:
                for file_path in index.files.keys():
                    if self._matches_pattern(file_path, query.file_pattern):
                        dependencies.add(file_path)
            else:
                # 无文件模式限制 - 依赖所有文件
                dependencies.update(index.files.keys())
        
        return dependencies

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """文件模式匹配 - 简单glob支持"""
        if '*' in pattern:
            # 简单通配符支持
            import fnmatch
            return fnmatch.fnmatch(file_path, pattern)
        return pattern in file_path

    def _evict_least_recently_used(self):
        """LRU驱逐策略 - 清理最久未访问的缓存"""
        if not self._access_times:
            return
        
        # 找到最久未访问的缓存键
        oldest_key = min(self._access_times.keys(), 
                        key=lambda k: self._access_times[k])
        
        self._invalidate_cache_entry(oldest_key)

    def _invalidate_cache_entry(self, cache_key: str):
        """失效单个缓存条目"""
        self._query_cache.pop(cache_key, None)
        self._file_dependencies.pop(cache_key, None)
        self._access_times.pop(cache_key, None)
        
        # 清理孤立的文件签名
        used_files = set()
        for deps in self._file_dependencies.values():
            used_files.update(deps)
        
        orphaned_files = set(self._file_signatures.keys()) - used_files
        for file_path in orphaned_files:
            self._file_signatures.pop(file_path, None)

    def get_cache_stats(self) -> Dict[str, any]:
        """获取缓存统计信息"""
        total_requests = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / max(total_requests, 1)
        
        return {
            "entries": len(self._query_cache),
            "max_entries": self._max_entries,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": round(hit_ratio, 3),
            "invalidations": self._invalidations,
            "tracked_files": len(self._file_signatures),
            "memory_usage_estimate": self._estimate_memory_usage()
        }

    def _estimate_memory_usage(self) -> str:
        """估算缓存内存使用"""
        # 粗略估算
        result_size = len(self._query_cache) * 1024  # 每个结果约1KB
        deps_size = sum(len(deps) * 50 for deps in self._file_dependencies.values())  # 依赖关系
        sig_size = len(self._file_signatures) * 100  # 文件签名
        
        total_kb = (result_size + deps_size + sig_size) / 1024
        
        if total_kb < 1024:
            return f"{total_kb:.1f}KB"
        else:
            return f"{total_kb/1024:.1f}MB"

    def clear_cache(self):
        """清空所有缓存"""
        self._query_cache.clear()
        self._file_dependencies.clear()
        self._file_signatures.clear()
        self._access_times.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._invalidations = 0


class SearchCacheMixin:
    """搜索缓存混入 - Phase 4智能化版本"""

    def __init__(self, index: CodeIndex):
        self.index = index
        self._advanced_cache = AdvancedQueryCache()

    def get_cache_key(self, query: SearchQuery) -> str:
        """向后兼容方法 - 转发到高级缓存"""
        return self._advanced_cache._generate_cache_key(query)

    def get_cached_result(self, cache_key: str) -> Optional[SearchResult]:
        """获取缓存结果 - 使用高级缓存"""
        # 通过cache_key重建query来使用新接口
        # 注意：这是为了向后兼容，理想情况下应该直接传递query对象
        for query_cache_key, result in self._advanced_cache._query_cache.items():
            if query_cache_key == cache_key:
                return result
        return None

    def get_cached_query_result(self, query: SearchQuery) -> Optional[SearchResult]:
        """新的直接查询接口 - 推荐使用"""
        return self._advanced_cache.get_query_result(query, self.index)

    def cache_result(self, cache_key: str, result: SearchResult):
        """向后兼容缓存方法"""
        # 注意：此方法缺少query参数，功能受限
        # 建议使用cache_query_result方法
        pass

    def cache_query_result(self, query: SearchQuery, result: SearchResult):
        """新的查询缓存接口 - 推荐使用"""
        self._advanced_cache.cache_query_result(query, result, self.index)

    def invalidate_file_changes(self, changed_files: Set[str]):
        """文件变更时失效相关缓存"""
        self._advanced_cache.invalidate_file_changes(changed_files, self.index)

    def get_cache_stats(self) -> Dict[str, any]:
        """获取缓存统计信息"""
        return self._advanced_cache.get_cache_stats()

    @lru_cache(maxsize=100)
    def search_cached(self, query_hash: str, file_signatures: tuple):
        """LRU缓存装饰器 - 保留向后兼容性"""
        # 实际缓存逻辑现在在AdvancedQueryCache中处理
        return None