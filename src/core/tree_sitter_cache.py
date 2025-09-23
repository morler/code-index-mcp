"""
Phase 4 Tree-sitter Parse Caching - 解析树缓存优化

Linus风格直接内存操作 - 80%+解析复用率目标
"""

import hashlib
import time
import weakref
from typing import Dict, Optional, Any, Set
from pathlib import Path

# 延迟导入tree-sitter避免循环依赖
_tree_sitter_imported = False
_Tree = None
_Parser = None


def _ensure_tree_sitter():
    """延迟导入tree-sitter模块"""
    global _tree_sitter_imported, _Tree, _Parser
    if not _tree_sitter_imported:
        try:
            from tree_sitter import Tree, Parser
            _Tree = Tree
            _Parser = Parser
            _tree_sitter_imported = True
        except ImportError:
            pass


class TreeSitterCache:
    """Tree-sitter解析树缓存 - Phase 4核心优化"""

    def __init__(self, max_cache_size: int = 150):
        # 核心缓存数据 - 直接字典操作
        self._tree_cache: Dict[str, Any] = {}  # content_hash -> parsed_tree
        self._content_hashes: Dict[str, str] = {}  # file_path -> content_hash
        self._access_times: Dict[str, float] = {}  # content_hash -> last_access
        self._file_languages: Dict[str, str] = {}  # file_path -> language

        # 内存管理
        self._max_cache_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._parse_times: Dict[str, float] = {}  # content_hash -> parse_time

        # 弱引用追踪避免内存泄漏
        self._weakref_cleanup = weakref.WeakSet()

    def get_parsed_tree(self, file_path: str, content: bytes, language: str, parser: Any) -> Optional[Any]:
        """获取缓存的解析树或创建新的"""
        _ensure_tree_sitter()
        if not _Tree:
            # tree-sitter不可用时返回None
            return None

        # 计算内容hash - 精确缓存key
        content_hash = self._calculate_content_hash(content)

        # 检查缓存
        if content_hash in self._tree_cache:
            self._cache_hits += 1
            self._access_times[content_hash] = time.time()
            return self._tree_cache[content_hash]

        # 缓存未命中 - 解析新树
        start_time = time.time()
        try:
            tree = parser.parse(content)
            parse_time = time.time() - start_time

            # 缓存解析结果
            self._cache_parsed_tree(file_path, content_hash, tree, language, parse_time)
            self._cache_misses += 1

            return tree

        except Exception:
            self._cache_misses += 1
            return None

    def _calculate_content_hash(self, content: bytes) -> str:
        """计算内容hash - 使用快速MD5"""
        # 对于tree-sitter解析，必须使用内容hash确保准确性
        return f"ts_{hashlib.md5(content).hexdigest()}"

    def _cache_parsed_tree(self, file_path: str, content_hash: str, tree: Any, language: str, parse_time: float):
        """缓存解析树和元数据"""
        # LRU清理 - 保持缓存大小限制
        if len(self._tree_cache) >= self._max_cache_size:
            self._evict_least_recently_used()

        # 缓存解析树
        self._tree_cache[content_hash] = tree
        self._content_hashes[file_path] = content_hash
        self._file_languages[file_path] = language
        self._access_times[content_hash] = time.time()
        self._parse_times[content_hash] = parse_time

        # 添加到弱引用追踪
        try:
            self._weakref_cleanup.add(tree)
        except TypeError:
            # 某些对象不支持弱引用
            pass

    def _evict_least_recently_used(self):
        """LRU驱逐策略 - 移除最久未访问的解析树"""
        if not self._access_times:
            return

        # 找到最久未访问的内容hash
        oldest_hash = min(self._access_times.keys(),
                         key=lambda h: self._access_times[h])

        self._remove_cached_tree(oldest_hash)

    def _remove_cached_tree(self, content_hash: str):
        """移除单个缓存条目"""
        self._tree_cache.pop(content_hash, None)
        self._access_times.pop(content_hash, None)
        self._parse_times.pop(content_hash, None)

        # 清理文件路径映射
        files_to_remove = []
        for file_path, hash_val in self._content_hashes.items():
            if hash_val == content_hash:
                files_to_remove.append(file_path)

        for file_path in files_to_remove:
            self._content_hashes.pop(file_path, None)
            self._file_languages.pop(file_path, None)

    def invalidate_file(self, file_path: str):
        """文件变更时失效缓存"""
        if file_path in self._content_hashes:
            content_hash = self._content_hashes[file_path]
            self._remove_cached_tree(content_hash)

    def invalidate_files(self, file_paths: Set[str]):
        """批量失效文件缓存"""
        for file_path in file_paths:
            self.invalidate_file(file_path)

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / max(total_requests, 1)

        # 计算平均解析时间
        avg_parse_time = 0.0
        if self._parse_times:
            avg_parse_time = sum(self._parse_times.values()) / len(self._parse_times)

        # 估算内存使用
        memory_estimate = self._estimate_memory_usage()

        return {
            "cached_trees": len(self._tree_cache),
            "max_cache_size": self._max_cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": round(hit_ratio, 3),
            "avg_parse_time_ms": round(avg_parse_time * 1000, 2),
            "tracked_files": len(self._content_hashes),
            "memory_usage_estimate": memory_estimate,
            "cache_efficiency": "HIGH" if hit_ratio > 0.8 else
                             "MEDIUM" if hit_ratio > 0.6 else "LOW"
        }

    def _estimate_memory_usage(self) -> str:
        """估算缓存内存使用"""
        # 粗略估算 - 每个解析树约50KB
        tree_size = len(self._tree_cache) * 50 * 1024  # 50KB per tree
        meta_size = len(self._content_hashes) * 200  # 元数据约200字节

        total_bytes = tree_size + meta_size

        if total_bytes < 1024 * 1024:
            return f"{total_bytes // 1024}KB"
        else:
            return f"{total_bytes // (1024 * 1024)}MB"

    def clear_cache(self):
        """清空所有缓存"""
        self._tree_cache.clear()
        self._content_hashes.clear()
        self._access_times.clear()
        self._file_languages.clear()
        self._parse_times.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._weakref_cleanup.clear()

    def get_language_stats(self) -> Dict[str, int]:
        """获取语言分布统计"""
        language_counts = {}
        for language in self._file_languages.values():
            language_counts[language] = language_counts.get(language, 0) + 1
        return language_counts

    def preload_trees(self, file_contents: Dict[str, bytes], languages: Dict[str, str], parsers: Dict[str, Any]):
        """批量预加载解析树 - 优化启动时间"""
        for file_path, content in file_contents.items():
            language = languages.get(file_path)
            parser = parsers.get(language)

            if language and parser:
                # 直接调用获取方法进行预加载
                self.get_parsed_tree(file_path, content, language, parser)


# Linus原则: 单例全局缓存，避免重复创建
_global_tree_cache: Optional[TreeSitterCache] = None


def get_tree_cache() -> TreeSitterCache:
    """获取全局Tree-sitter缓存实例 - 单例模式"""
    global _global_tree_cache
    if _global_tree_cache is None:
        _global_tree_cache = TreeSitterCache()
    return _global_tree_cache


def clear_global_tree_cache():
    """清空全局Tree-sitter缓存 - 测试和重置时使用"""
    global _global_tree_cache
    if _global_tree_cache:
        _global_tree_cache.clear_cache()


# 便利函数 - 直接使用接口
def get_cached_tree(file_path: str, content: bytes, language: str, parser: Any) -> Optional[Any]:
    """获取缓存的解析树(缓存版本) - 统一接口"""
    return get_tree_cache().get_parsed_tree(file_path, content, language, parser)


def invalidate_file_tree_cache(file_path: str):
    """使文件解析树缓存失效 - 外部更新时使用"""
    get_tree_cache().invalidate_file(file_path)