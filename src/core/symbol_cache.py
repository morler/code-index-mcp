"""
Phase 4 Symbol Index Caching - 符号提取结果缓存

Linus风格直接数据操作 - 90%+符号缓存命中率目标
"""

import hashlib
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from pathlib import Path

from .index import FileInfo, SymbolInfo


class SymbolIndexCache:
    """符号索引缓存 - Phase 4符号提取优化"""

    def __init__(self, max_cache_size: int = 300):
        # 核心缓存数据 - 直接字典操作
        self._symbol_cache: Dict[str, Dict[str, List[str]]] = {}  # file_hash -> symbols
        self._file_info_cache: Dict[str, FileInfo] = {}  # file_hash -> FileInfo
        self._file_hashes: Dict[str, str] = {}  # file_path -> file_hash
        self._access_times: Dict[str, float] = {}  # file_hash -> last_access

        # 符号提取时间统计
        self._extraction_times: Dict[str, float] = {}  # file_hash -> extraction_time
        self._scip_data_cache: Dict[str, List[Dict[str, Any]]] = {}  # file_hash -> scip_data

        # 缓存统计
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = max_cache_size

        # 跨文件符号引用缓存
        self._symbol_references: Dict[str, Set[str]] = {}  # symbol_name -> file_paths
        self._file_dependencies: Dict[str, Set[str]] = {}  # file_path -> dependent_files

    def get_cached_symbols(self, file_path: str, content_hash: str, language: str) -> Optional[Tuple[Dict[str, List[str]], FileInfo, List[Dict[str, Any]]]]:
        """获取缓存的符号提取结果"""
        file_hash = self._generate_file_hash(file_path, content_hash, language)

        # 检查缓存
        if file_hash in self._symbol_cache:
            self._cache_hits += 1
            self._access_times[file_hash] = time.time()

            symbols = self._symbol_cache[file_hash]
            file_info = self._file_info_cache[file_hash]
            scip_data = self._scip_data_cache.get(file_hash, [])

            return symbols, file_info, scip_data

        self._cache_misses += 1
        return None

    def cache_symbol_results(self,
                           file_path: str,
                           content_hash: str,
                           language: str,
                           symbols: Dict[str, List[str]],
                           file_info: FileInfo,
                           scip_data: List[Dict[str, Any]],
                           extraction_time: float):
        """缓存符号提取结果"""
        file_hash = self._generate_file_hash(file_path, content_hash, language)

        # LRU清理 - 保持缓存大小限制
        if len(self._symbol_cache) >= self._max_cache_size:
            self._evict_least_recently_used()

        # 缓存所有相关数据
        self._symbol_cache[file_hash] = symbols
        self._file_info_cache[file_hash] = file_info
        self._scip_data_cache[file_hash] = scip_data
        self._file_hashes[file_path] = file_hash
        self._access_times[file_hash] = time.time()
        self._extraction_times[file_hash] = extraction_time

        # 更新符号引用映射
        self._update_symbol_references(file_path, symbols)

    def _generate_file_hash(self, file_path: str, content_hash: str, language: str) -> str:
        """生成文件符号缓存hash"""
        # 包含路径、内容hash和语言信息确保准确性
        combined = f"{file_path}:{content_hash}:{language}"
        return f"sym_{hashlib.md5(combined.encode()).hexdigest()}"

    def _update_symbol_references(self, file_path: str, symbols: Dict[str, List[str]]):
        """更新符号引用映射 - 用于跨文件依赖追踪"""
        # 清理旧的引用
        for symbol_name, file_paths in self._symbol_references.items():
            file_paths.discard(file_path)

        # 添加新的引用
        for symbol_type, symbol_list in symbols.items():
            for symbol_name in symbol_list:
                if symbol_name not in self._symbol_references:
                    self._symbol_references[symbol_name] = set()
                self._symbol_references[symbol_name].add(file_path)

    def invalidate_file(self, file_path: str):
        """文件变更时失效缓存"""
        if file_path in self._file_hashes:
            file_hash = self._file_hashes[file_path]
            self._remove_cached_entry(file_hash, file_path)

    def invalidate_files(self, file_paths: Set[str]):
        """批量失效文件缓存"""
        for file_path in file_paths:
            self.invalidate_file(file_path)

    def get_symbol_files(self, symbol_name: str) -> Set[str]:
        """获取包含指定符号的文件列表 - 快速符号查找"""
        return self._symbol_references.get(symbol_name, set()).copy()

    def find_dependent_files(self, changed_file: str) -> Set[str]:
        """查找依赖于变更文件的其他文件 - 智能失效"""
        dependent_files = set()

        # 获取变更文件的符号
        file_hash = self._file_hashes.get(changed_file)
        if file_hash and file_hash in self._symbol_cache:
            symbols = self._symbol_cache[file_hash]

            # 查找引用这些符号的其他文件
            for symbol_type, symbol_list in symbols.items():
                for symbol_name in symbol_list:
                    referencing_files = self._symbol_references.get(symbol_name, set())
                    dependent_files.update(referencing_files)

        dependent_files.discard(changed_file)  # 排除自己
        return dependent_files

    def _evict_least_recently_used(self):
        """LRU驱逐策略"""
        if not self._access_times:
            return

        # 找到最久未访问的文件hash
        oldest_hash = min(self._access_times.keys(),
                         key=lambda h: self._access_times[h])

        # 找到对应的文件路径
        file_path = None
        for path, hash_val in self._file_hashes.items():
            if hash_val == oldest_hash:
                file_path = path
                break

        if file_path:
            self._remove_cached_entry(oldest_hash, file_path)

    def _remove_cached_entry(self, file_hash: str, file_path: str):
        """移除单个缓存条目"""
        # 清理所有相关缓存
        self._symbol_cache.pop(file_hash, None)
        self._file_info_cache.pop(file_hash, None)
        self._scip_data_cache.pop(file_hash, None)
        self._access_times.pop(file_hash, None)
        self._extraction_times.pop(file_hash, None)
        self._file_hashes.pop(file_path, None)

        # 清理符号引用
        for symbol_name, file_paths in self._symbol_references.items():
            file_paths.discard(file_path)

        # 清理空的符号引用
        empty_symbols = [name for name, paths in self._symbol_references.items() if not paths]
        for symbol_name in empty_symbols:
            del self._symbol_references[symbol_name]

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self._cache_hits + self._cache_misses
        hit_ratio = self._cache_hits / max(total_requests, 1)

        # 计算平均提取时间
        avg_extraction_time = 0.0
        if self._extraction_times:
            avg_extraction_time = sum(self._extraction_times.values()) / len(self._extraction_times)

        # 符号统计
        total_symbols = 0
        symbol_type_counts = {}
        for symbols in self._symbol_cache.values():
            for symbol_type, symbol_list in symbols.items():
                total_symbols += len(symbol_list)
                symbol_type_counts[symbol_type] = symbol_type_counts.get(symbol_type, 0) + len(symbol_list)

        return {
            "cached_files": len(self._symbol_cache),
            "max_cache_size": self._max_cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": round(hit_ratio, 3),
            "avg_extraction_time_ms": round(avg_extraction_time * 1000, 2),
            "total_symbols": total_symbols,
            "unique_symbol_names": len(self._symbol_references),
            "symbol_type_distribution": symbol_type_counts,
            "memory_usage_estimate": self._estimate_memory_usage(),
            "cache_efficiency": "HIGH" if hit_ratio > 0.9 else
                             "MEDIUM" if hit_ratio > 0.7 else "LOW"
        }

    def _estimate_memory_usage(self) -> str:
        """估算缓存内存使用"""
        # 粗略估算
        symbol_size = len(self._symbol_cache) * 2 * 1024  # 每个文件约2KB符号数据
        file_info_size = len(self._file_info_cache) * 500  # 每个FileInfo约500字节
        scip_size = len(self._scip_data_cache) * 1024  # 每个SCIP数据约1KB
        ref_size = len(self._symbol_references) * 100  # 每个符号引用约100字节

        total_bytes = symbol_size + file_info_size + scip_size + ref_size

        if total_bytes < 1024 * 1024:
            return f"{total_bytes // 1024}KB"
        else:
            return f"{total_bytes // (1024 * 1024)}MB"

    def clear_cache(self):
        """清空所有缓存"""
        self._symbol_cache.clear()
        self._file_info_cache.clear()
        self._scip_data_cache.clear()
        self._file_hashes.clear()
        self._access_times.clear()
        self._extraction_times.clear()
        self._symbol_references.clear()
        self._file_dependencies.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_language_symbol_stats(self) -> Dict[str, Dict[str, int]]:
        """获取各语言的符号分布统计"""
        language_stats = {}

        for file_info in self._file_info_cache.values():
            language = file_info.language
            if language not in language_stats:
                language_stats[language] = {}

            for symbol_type, symbol_list in file_info.symbols.items():
                if symbol_type not in language_stats[language]:
                    language_stats[language][symbol_type] = 0
                language_stats[language][symbol_type] += len(symbol_list)

        return language_stats

    def preload_symbols(self, file_symbol_data: Dict[str, Tuple[str, str, Dict[str, List[str]], FileInfo, List[Dict[str, Any]]]]):
        """批量预加载符号缓存 - 优化启动时间"""
        for file_path, (content_hash, language, symbols, file_info, scip_data) in file_symbol_data.items():
            # 直接调用缓存方法进行预加载
            self.cache_symbol_results(file_path, content_hash, language, symbols, file_info, scip_data, 0.0)


# Linus原则: 单例全局缓存，避免重复创建
_global_symbol_cache: Optional[SymbolIndexCache] = None


def get_symbol_cache() -> SymbolIndexCache:
    """获取全局符号缓存实例 - 单例模式"""
    global _global_symbol_cache
    if _global_symbol_cache is None:
        _global_symbol_cache = SymbolIndexCache()
    return _global_symbol_cache


def clear_global_symbol_cache():
    """清空全局符号缓存 - 测试和重置时使用"""
    global _global_symbol_cache
    if _global_symbol_cache:
        _global_symbol_cache.clear_cache()


# 便利函数 - 直接使用接口
def get_cached_file_symbols(file_path: str, content_hash: str, language: str) -> Optional[Tuple[Dict[str, List[str]], FileInfo, List[Dict[str, Any]]]]:
    """获取缓存的文件符号(缓存版本) - 统一接口"""
    return get_symbol_cache().get_cached_symbols(file_path, content_hash, language)


def cache_file_symbols(file_path: str, content_hash: str, language: str, symbols: Dict[str, List[str]],
                      file_info: FileInfo, scip_data: List[Dict[str, Any]], extraction_time: float):
    """缓存文件符号提取结果 - 统一接口"""
    get_symbol_cache().cache_symbol_results(file_path, content_hash, language, symbols, file_info, scip_data, extraction_time)


def invalidate_file_symbol_cache(file_path: str):
    """使文件符号缓存失效 - 外部更新时使用"""
    get_symbol_cache().invalidate_file(file_path)


def find_symbol_files(symbol_name: str) -> Set[str]:
    """查找包含指定符号的文件 - 快速符号搜索"""
    return get_symbol_cache().get_symbol_files(symbol_name)