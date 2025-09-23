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
import psutil


def _calculate_smart_cache_size() -> Tuple[int, int]:
    """
    智能计算缓存大小 - Linus风格系统适应
    
    Returns:
        Tuple[max_files, max_memory_mb] - 缓存文件数和内存限制
    """
    try:
        # 获取系统内存信息
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024 ** 3)
        
        # Linus原则: 400 files per GB of system RAM
        max_files = int(400 * total_memory_gb)
        
        # 最大内存使用: 20% of total system memory
        max_memory_mb = int((memory.total * 0.2) / (1024 * 1024))
        
        # 安全下限和上限
        max_files = max(100, min(max_files, 5000))  # 100-5000文件
        max_memory_mb = max(50, min(max_memory_mb, 2048))  # 50MB-2GB
        
        return max_files, max_memory_mb
        
    except Exception:
        # 安全回退 - 保守设置
        return 1000, 100


class OptimizedFileCache:
    """Linus风格文件缓存 - 直接内存管理"""
    
    def __init__(self, max_size: Optional[int] = None, max_memory_mb: Optional[int] = None):
        self._cache: Dict[str, List[str]] = {}
        self._file_hashes: Dict[str, str] = {}
        self._access_times: Dict[str, float] = {}
        
        # 智能LRU: 访问频率和模式跟踪
        self._access_counts: Dict[str, int] = {}  # 访问次数
        self._recent_accesses: Dict[str, List[float]] = {}  # 最近访问时间列表
        
        # 缓存统计 - 性能监控
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
        self._cleanup_count = 0
        self._start_time = time.time()
        
        # 内存压力检测
        self._memory_warnings = 0
        self._emergency_cleanups = 0
        self._last_memory_check = 0
        self._memory_check_interval = 30  # 30秒检查一次系统内存
        
        # 智能缓存大小 - 自动系统检测
        if max_size is None or max_memory_mb is None:
            smart_size, smart_memory = _calculate_smart_cache_size()
            self._max_size = max_size or smart_size
            max_memory_mb = max_memory_mb or smart_memory
        else:
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
        
        # 统计请求数
        self._total_requests += 1
        
        # 检查文件是否变更
        if self._should_reload_file(normalized_path):
            self._load_file(normalized_path)
            self._cache_misses += 1
        else:
            self._cache_hits += 1
        
        # 智能访问跟踪 - 频率+时间
        current_time = time.time()
        self._access_times[normalized_path] = current_time
        self._access_counts[normalized_path] = self._access_counts.get(normalized_path, 0) + 1
        
        # 记录最近访问时间（保留最近10次）
        if normalized_path not in self._recent_accesses:
            self._recent_accesses[normalized_path] = []
        self._recent_accesses[normalized_path].append(current_time)
        if len(self._recent_accesses[normalized_path]) > 10:
            self._recent_accesses[normalized_path].pop(0)
        
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

    def _calculate_file_hash_ultra_fast(self, file_path: str) -> str:
        """Phase2优化: 元数据哈希策略 - 3-5x变更检测加速"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            
            stat = path.stat()
            
            # Phase2策略: 大文件(>10KB)使用纯元数据哈希
            if stat.st_size >= 10240:  # 10KB threshold
                # 大文件: 元数据组合 - 极速且准确
                return f"{stat.st_mtime}:{stat.st_size}:{stat.st_ino}"
            
            # 小文件(<10KB): 保留内容哈希确保准确性
            with open(file_path, 'rb') as f:
                content = f.read()
                return xxhash.xxh3_64(content).hexdigest()
                
        except Exception:
            return ""

    def _calculate_file_hash(self, file_path: str) -> str:
        """向后兼容的文件哈希计算 - 使用超快速策略"""
        return self._calculate_file_hash_ultra_fast(file_path)

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
            self._access_counts.pop(file_path, None)
            self._recent_accesses.pop(file_path, None)

    def _maybe_cleanup(self) -> None:
        """智能清理 - 内存压力感知"""
        current_time = time.time()
        
        # 定期检查系统内存压力
        if current_time - self._last_memory_check > self._memory_check_interval:
            self._check_system_memory_pressure()
            self._last_memory_check = current_time
        
        # 检查缓存大小限制
        if len(self._cache) > self._max_size * self._cleanup_threshold:
            self._cleanup_by_size()
            self._cleanup_count += 1
        
        # 检查内存限制
        if self._current_memory > self._max_memory_bytes * self._cleanup_threshold:
            self._cleanup_by_memory()
            self._cleanup_count += 1
    
    def _check_system_memory_pressure(self) -> None:
        """检查系统内存压力并采取行动"""
        try:
            memory = psutil.virtual_memory()
            available_percent = (memory.available / memory.total) * 100
            
            # 系统内存严重不足时紧急清理
            if available_percent < 10:  # 可用内存 < 10%
                self._emergency_cleanup()
                self._emergency_cleanups += 1
            elif available_percent < 20:  # 可用内存 < 20%
                self._aggressive_cleanup()
                self._memory_warnings += 1
                
        except Exception:
            # psutil失败时忽略，继续正常运行
            pass
    
    def _emergency_cleanup(self) -> None:
        """紧急内存清理 - 清理到30%容量"""
        target_size = int(self._max_size * 0.3)
        current_size = len(self._cache)
        
        if current_size <= target_size:
            return
        
        # 紧急模式：只保留最近30分钟访问的文件
        current_time = time.time()
        recent_threshold = current_time - 1800  # 30分钟
        
        files_to_remove = []
        for file_path, last_access in self._access_times.items():
            if last_access < recent_threshold:
                files_to_remove.append(file_path)
        
        # 如果还不够，按智能评分移除
        if len(self._cache) - len(files_to_remove) > target_size:
            files_with_scores = []
            current_time = time.time()
            
            for file_path in self._cache:
                if file_path not in files_to_remove:
                    last_access = self._access_times.get(file_path, 0)
                    access_count = self._access_counts.get(file_path, 1)
                    
                    # 紧急模式简化评分
                    score = (current_time - last_access) / max(access_count, 1)
                    files_with_scores.append((file_path, score))
            
            files_with_scores.sort(key=lambda x: x[1], reverse=True)
            additional_removes = current_size - target_size - len(files_to_remove)
            files_to_remove.extend([f[0] for f in files_with_scores[:additional_removes]])
        
        for file_path in files_to_remove:
            self._remove_from_cache(file_path)
    
    def _aggressive_cleanup(self) -> None:
        """积极清理 - 清理到50%容量"""
        target_size = int(self._max_size * 0.5)
        target_memory = int(self._max_memory_bytes * 0.5)
        
        # 先按大小清理
        if len(self._cache) > target_size:
            self._cleanup_by_size_to_target(target_size)
        
        # 再按内存清理
        if self._current_memory > target_memory:
            self._cleanup_by_memory_to_target(target_memory)
    
    def _cleanup_by_size_to_target(self, target_size: int) -> None:
        """清理到指定大小"""
        current_size = len(self._cache)
        if current_size <= target_size:
            return
        
        # 使用现有的智能评分系统
        files_with_scores = []
        current_time = time.time()
        
        for file_path in self._cache:
            last_access = self._access_times.get(file_path, 0)
            access_count = self._access_counts.get(file_path, 1)
            recent_accesses = self._recent_accesses.get(file_path, [])
            
            time_score = max(0, current_time - last_access) / 3600
            freq_score = 1.0 / max(1, access_count)
            pattern_score = self._calculate_pattern_score(recent_accesses, current_time)
            
            total_score = time_score + freq_score - pattern_score
            files_with_scores.append((file_path, total_score))
        
        files_with_scores.sort(key=lambda x: x[1], reverse=True)
        files_to_remove = files_with_scores[:current_size - target_size]
        
        for file_path, _ in files_to_remove:
            self._remove_from_cache(file_path)
    
    def _cleanup_by_memory_to_target(self, target_memory: int) -> None:
        """清理到指定内存使用量"""
        if self._current_memory <= target_memory:
            return
        
        # 按文件大小排序，优先移除大文件
        files_by_size = []
        for file_path, lines in self._cache.items():
            size = sum(len(line.encode('utf-8')) for line in lines)
            files_by_size.append((file_path, size))
        
        files_by_size.sort(key=lambda x: x[1], reverse=True)
        
        for file_path, size in files_by_size:
            if self._current_memory <= target_memory:
                break
            self._remove_from_cache(file_path)

    def _cleanup_by_size(self) -> None:
        """智能LRU清理 - 综合评分策略"""
        target_size = int(self._max_size * 0.7)  # 清理到70%
        current_size = len(self._cache)
        
        if current_size <= target_size:
            return
        
        # 智能评分: 时间 + 频率 + 访问模式
        files_with_scores = []
        current_time = time.time()
        
        for file_path in self._cache:
            last_access = self._access_times.get(file_path, 0)
            access_count = self._access_counts.get(file_path, 1)
            recent_accesses = self._recent_accesses.get(file_path, [])
            
            # 时间权重 (越新越重要)
            time_score = max(0, current_time - last_access) / 3600  # 小时
            
            # 频率权重 (高频文件保留)
            freq_score = 1.0 / max(1, access_count)
            
            # 访问模式权重 (规律访问保留)
            pattern_score = self._calculate_pattern_score(recent_accesses, current_time)
            
            # 综合评分 (越低越容易被移除)
            total_score = time_score + freq_score - pattern_score
            files_with_scores.append((file_path, total_score))
        
        # 按综合评分排序，移除评分最高的文件
        files_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        files_to_remove = files_with_scores[:current_size - target_size]
        for file_path, _ in files_to_remove:
            self._remove_from_cache(file_path)
    
    def _calculate_pattern_score(self, recent_accesses: List[float], current_time: float) -> float:
        """计算访问模式评分 - 规律访问获得更高分"""
        if len(recent_accesses) < 2:
            return 0.0
        
        # 计算访问间隔的一致性
        intervals = []
        for i in range(1, len(recent_accesses)):
            intervals.append(recent_accesses[i] - recent_accesses[i-1])
        
        if not intervals:
            return 0.0
        
        # 间隔越一致，模式评分越高
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        
        # 如果最近有访问且间隔规律，给更高分
        time_since_last = current_time - recent_accesses[-1]
        if time_since_last < avg_interval * 2 and variance < avg_interval * 0.5:
            return 2.0  # 高模式分
        
        return 0.0

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
        """获取缓存统计 - 完整性能监控"""
        current_time = time.time()
        uptime_hours = (current_time - self._start_time) / 3600
        
        # 系统内存信息
        try:
            memory = psutil.virtual_memory()
            system_memory_mb = memory.total / (1024 * 1024)
            system_available_mb = memory.available / (1024 * 1024)
        except:
            system_memory_mb = system_available_mb = 0
        
        return {
            # 基础统计
            "file_count": len(self._cache),
            "memory_usage_mb": round(self._current_memory / (1024 * 1024), 2),
            "max_size": self._max_size,
            "max_memory_mb": round(self._max_memory_bytes / (1024 * 1024), 2),
            
            # 性能指标
            "cache_hit_ratio": self._calculate_hit_ratio(),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": self._total_requests,
            
            # 系统统计
            "cleanup_count": self._cleanup_count,
            "memory_warnings": self._memory_warnings,
            "emergency_cleanups": self._emergency_cleanups,
            "uptime_hours": round(uptime_hours, 2),
            "avg_requests_per_hour": round(self._total_requests / max(uptime_hours, 0.01), 2),
            
            # 系统内存
            "system_memory_mb": round(system_memory_mb, 2),
            "system_available_mb": round(system_available_mb, 2),
            "memory_pressure": self._calculate_memory_pressure(),
            
            # 访问模式
            "most_accessed_files": self._get_top_accessed_files(5),
            "recent_activity": self._get_recent_activity_stats()
        }

    def _calculate_hit_ratio(self) -> float:
        """计算真实缓存命中率"""
        if self._total_requests == 0:
            return 0.0
        return round(self._cache_hits / self._total_requests, 3)
    
    def _calculate_memory_pressure(self) -> str:
        """计算内存压力等级"""
        usage_ratio = self._current_memory / self._max_memory_bytes
        if usage_ratio > 0.9:
            return "HIGH"
        elif usage_ratio > 0.7:
            return "MEDIUM"
        elif usage_ratio > 0.5:
            return "LOW"
        else:
            return "NONE"
    
    def _get_top_accessed_files(self, limit: int) -> List[Dict[str, any]]:
        """获取访问最频繁的文件"""
        if not self._access_counts:
            return []
        
        sorted_files = sorted(
            self._access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        result = []
        for file_path, count in sorted_files:
            last_access = self._access_times.get(file_path, 0)
            result.append({
                "file": file_path,
                "access_count": count,
                "last_access_ago_minutes": round((time.time() - last_access) / 60, 1)
            })
        
        return result
    
    def _get_recent_activity_stats(self) -> Dict[str, any]:
        """获取最近活动统计"""
        current_time = time.time()
        recent_threshold = current_time - 3600  # 最近1小时
        
        recent_accesses = 0
        active_files = 0
        
        for file_path, access_time in self._access_times.items():
            if access_time > recent_threshold:
                recent_accesses += self._access_counts.get(file_path, 0)
                active_files += 1
        
        return {
            "recent_accesses_last_hour": recent_accesses,
            "active_files_last_hour": active_files,
            "cache_efficiency": "HIGH" if self._calculate_hit_ratio() > 0.8 else 
                             "MEDIUM" if self._calculate_hit_ratio() > 0.6 else "LOW"
        }

    def clear_cache(self) -> None:
        """清空缓存 - 完整重置"""
        self._cache.clear()
        self._file_hashes.clear()
        self._access_times.clear()
        self._access_counts.clear()
        self._recent_accesses.clear()
        self._current_memory = 0
        
        # 重置统计数据
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
        self._cleanup_count = 0
        self._memory_warnings = 0
        self._emergency_cleanups = 0
        self._start_time = time.time()

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
        # 使用智能缓存大小 - 自动系统检测
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