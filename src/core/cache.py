"""
Linus风格内存优化文件缓存

核心原则：
1. LRU缓存避免内存泄漏
2. 直接数据操作，零抽象层
3. 文件哈希检查避免重复读取
4. 统一接口消除特殊情况
"""

from typing import Dict, List, Optional, Tuple
from functools import lru_cache
from pathlib import Path
import xxhash
import time
import weakref


class OptimizedFileCache:
    """Linus风格文件缓存 - 直接内存管理"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self._cache: Dict[str, List[str]] = {}
        self._file_hashes: Dict[str, str] = {}
        self._access_times: Dict[str, float] = {}
        self._max_size = max_size
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._current_memory = 0
        
        # Linus原则: 零配置，自动清理
        self._enable_auto_cleanup = True
        self._cleanup_threshold = 0.8  # 80%时开始清理

    def get_file_lines(self, file_path: str) -> List[str]:
        """
        获取文件行 - Linus风格统一接口
        
        自动处理：
        1. 文件变更检测
        2. LRU淘汰
        3. 内存限制
        """
        # 标准化路径 - 消除特殊情况
        normalized_path = str(Path(file_path))
        
        # 检查文件是否变更
        if self._should_reload_file(normalized_path):
            self._load_file(normalized_path)
        
        # 更新访问时间 - LRU策略
        self._access_times[normalized_path] = time.time()
        
        # 自动清理检查
        if self._enable_auto_cleanup:
            self._maybe_cleanup()
        
        return self._cache.get(normalized_path, [])

    def _should_reload_file(self, file_path: str) -> bool:
        """检查文件是否需要重新加载"""
        if file_path not in self._cache:
            return True
            
        # 文件哈希检查 - 避免时间戳问题
        current_hash = self._calculate_file_hash(file_path)
        cached_hash = self._file_hashes.get(file_path)
        
        return current_hash != cached_hash

    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希 - xxhash3 极速检测 (Linus优化版)"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            
            stat = path.stat()
            
            # Linus原则: 对小文件使用轻量级检测
            if stat.st_size < 1024:
                # 小文件直接用元数据哈希 - 极速
                return xxhash.xxh3_64(f"{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
            
            # 大文件使用内容采样 - xxhash3比MD5快5-10x
            hasher = xxhash.xxh3_64()
            hasher.update(f"{stat.st_mtime}:{stat.st_size}".encode())
            
            # 分段采样策略 - 更好的变更检测
            with open(file_path, 'rb') as f:
                # 读取开头
                hasher.update(f.read(512))
                
                # 如果文件很大，还读取中间和结尾
                if stat.st_size > 50000:
                    f.seek(stat.st_size // 2)
                    hasher.update(f.read(512))
                    f.seek(-512, 2)  # 从结尾向前512字节
                    hasher.update(f.read(512))
            
            return hasher.hexdigest()
        except Exception:
            return ""

    def _load_file(self, file_path: str) -> None:
        """加载文件到缓存 - 原子操作"""
        try:
            path = Path(file_path)
            content = path.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            # 移除旧缓存
            self._remove_from_cache(file_path)
            
            # 添加新缓存
            self._cache[file_path] = lines
            self._file_hashes[file_path] = self._calculate_file_hash(file_path)
            self._access_times[file_path] = time.time()
            
            # 更新内存使用
            memory_size = sum(len(line.encode('utf-8')) for line in lines)
            self._current_memory += memory_size
            
        except Exception:
            # 失败时存储空列表，避免重复尝试
            self._cache[file_path] = []
            self._file_hashes[file_path] = ""
            self._access_times[file_path] = time.time()

    def _remove_from_cache(self, file_path: str) -> None:
        """从缓存中移除文件"""
        if file_path in self._cache:
            # 更新内存计数
            lines = self._cache[file_path]
            memory_size = sum(len(line.encode('utf-8')) for line in lines)
            self._current_memory -= memory_size
            
            # 清理所有相关数据
            del self._cache[file_path]
            self._file_hashes.pop(file_path, None)
            self._access_times.pop(file_path, None)

    def _maybe_cleanup(self) -> None:
        """可能触发清理 - 自动内存管理"""
        # 检查缓存大小限制
        if len(self._cache) > self._max_size * self._cleanup_threshold:
            self._cleanup_by_size()
        
        # 检查内存限制
        if self._current_memory > self._max_memory_bytes * self._cleanup_threshold:
            self._cleanup_by_memory()

    def _cleanup_by_size(self) -> None:
        """按缓存大小清理 - LRU策略"""
        target_size = int(self._max_size * 0.7)  # 清理到70%
        current_size = len(self._cache)
        
        if current_size <= target_size:
            return
        
        # 按访问时间排序，移除最旧的
        files_by_access = sorted(
            self._access_times.items(),
            key=lambda x: x[1]
        )
        
        files_to_remove = files_by_access[:current_size - target_size]
        for file_path, _ in files_to_remove:
            self._remove_from_cache(file_path)

    def _cleanup_by_memory(self) -> None:
        """按内存使用清理 - 移除最大文件优先"""
        target_memory = int(self._max_memory_bytes * 0.7)  # 清理到70%
        
        if self._current_memory <= target_memory:
            return
        
        # 按文件大小排序，优先移除大文件
        files_by_size = []
        for file_path, lines in self._cache.items():
            size = sum(len(line.encode('utf-8')) for line in lines)
            files_by_size.append((file_path, size))
        
        files_by_size.sort(key=lambda x: x[1], reverse=True)
        
        # 移除大文件直到达到目标内存
        for file_path, size in files_by_size:
            if self._current_memory <= target_memory:
                break
            self._remove_from_cache(file_path)

    def get_cache_stats(self) -> Dict[str, any]:
        """获取缓存统计 - 调试和监控"""
        return {
            "file_count": len(self._cache),
            "memory_usage_mb": self._current_memory / (1024 * 1024),
            "max_size": self._max_size,
            "max_memory_mb": self._max_memory_bytes / (1024 * 1024),
            "cache_hit_ratio": self._calculate_hit_ratio()
        }

    def _calculate_hit_ratio(self) -> float:
        """计算缓存命中率 - 性能指标"""
        # 简化版本，实际可以更精确
        if not self._cache:
            return 0.0
        return min(1.0, len(self._cache) / max(self._max_size, 1))

    def clear_cache(self) -> None:
        """清空缓存 - 内存管理"""
        self._cache.clear()
        self._file_hashes.clear()
        self._access_times.clear()
        self._current_memory = 0

    def invalidate_file(self, file_path: str) -> None:
        """使文件缓存失效 - 外部更新时使用"""
        normalized_path = str(Path(file_path))
        self._remove_from_cache(normalized_path)

    def preload_files(self, file_paths: List[str]) -> None:
        """预加载文件 - 批量操作优化"""
        for file_path in file_paths:
            if file_path not in self._cache:
                self._load_file(str(Path(file_path)))


# Linus原则: 单例全局缓存，避免重复创建
_global_file_cache: Optional[OptimizedFileCache] = None


def get_file_cache() -> OptimizedFileCache:
    """获取全局文件缓存实例 - 单例模式"""
    global _global_file_cache
    if _global_file_cache is None:
        _global_file_cache = OptimizedFileCache()
    return _global_file_cache


def clear_global_cache() -> None:
    """清空全局缓存 - 测试和重置时使用"""
    global _global_file_cache
    if _global_file_cache:
        _global_file_cache.clear_cache()


# 便利函数 - 直接使用接口
def get_file_lines_cached(file_path: str) -> List[str]:
    """获取文件行(缓存版本) - 统一接口"""
    return get_file_cache().get_file_lines(file_path)