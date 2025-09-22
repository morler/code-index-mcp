"""
增量索引更新 - Linus风格实现
只处理变更文件，避免全量重建

Bad programmers worry about the code. Good programmers worry about data structures.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field

from .index import CodeIndex, FileInfo
from .builder import IndexBuilder, safe_file_operation


@dataclass
class FileChangeTracker:
    """文件变更跟踪器 - Linus原则: 直接数据操作"""
    file_hashes: Dict[str, str] = field(default_factory=dict)
    file_mtimes: Dict[str, float] = field(default_factory=dict)
    
    def get_file_hash(self, file_path: str) -> str:
        """计算文件哈希 - 统一接口"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (IOError, OSError):
            return ""
    
    def get_file_mtime(self, file_path: str) -> float:
        """获取文件修改时间 - 统一接口"""
        try:
            return os.path.getmtime(file_path)
        except (IOError, OSError):
            return 0.0
    
    def is_file_changed(self, file_path: str) -> bool:
        """检查文件是否变更 - Good Taste: 统一变更检测"""
        # 如果文件从未被跟踪过，认为是新文件（不是变更）
        if file_path not in self.file_hashes and file_path not in self.file_mtimes:
            return True
        
        # 优先使用修改时间检测（性能优化）
        current_mtime = self.get_file_mtime(file_path)
        cached_mtime = self.file_mtimes.get(file_path, 0.0)
        
        if current_mtime == cached_mtime and cached_mtime != 0.0:
            return False
        
        # 修改时间不同时，进行哈希验证（确保准确性）
        current_hash = self.get_file_hash(file_path)
        cached_hash = self.file_hashes.get(file_path, "")
        
        return current_hash != cached_hash
    
    def update_file_tracking(self, file_path: str) -> None:
        """更新文件跟踪信息 - 原子操作"""
        self.file_hashes[file_path] = self.get_file_hash(file_path)
        self.file_mtimes[file_path] = self.get_file_mtime(file_path)
    
    def remove_file_tracking(self, file_path: str) -> None:
        """移除文件跟踪 - 清理操作"""
        self.file_hashes.pop(file_path, None)
        self.file_mtimes.pop(file_path, None)


class IncrementalIndexer:
    """
    增量索引器 - Linus风格: 只处理变更文件
    
    核心原则:
    1. 避免全量重建 - 只处理变更
    2. 直接数据操作 - 无抽象层
    3. 原子更新 - 要么成功要么失败
    """
    
    def __init__(self, index: CodeIndex):
        self.index = index
        self.builder = IndexBuilder(index)
        self.tracker = FileChangeTracker()
        
    def update_index(self, root_path: str = None) -> Dict[str, int]:
        """
        增量更新索引 - 主入口
        
        返回统计信息: {"updated": N, "added": N, "removed": N}
        """
        if root_path:
            self.index.base_path = root_path
            
        # Linus原则: 数据驱动的操作流程
        current_files = self._scan_current_files()
        indexed_files = set(self.index.files.keys())
        
        stats = {"updated": 0, "added": 0, "removed": 0}
        
        # 处理文件变更
        for file_path in current_files:
            if file_path in indexed_files:
                if self._update_file_if_changed(file_path):
                    stats["updated"] += 1
            else:
                self._add_new_file(file_path)
                stats["added"] += 1
        
        # 处理删除的文件
        for file_path in indexed_files - current_files:
            self._remove_file(file_path)
            stats["removed"] += 1
            
        return stats
    
    def _scan_current_files(self) -> Set[str]:
        """扫描当前文件 - 复用IndexBuilder逻辑"""
        return set(self.builder._scan_files())
    
    @safe_file_operation
    def _update_file_if_changed(self, file_path: str) -> bool:
        """更新变更文件 - 原子操作"""
        # 如果文件从未被跟踪，先初始化跟踪信息，但不认为是变更
        if file_path not in self.tracker.file_hashes:
            self.tracker.update_file_tracking(file_path)
            return False  # 初次跟踪不算变更
        
        if not self.tracker.is_file_changed(file_path):
            return False
            
        # 移除旧索引数据
        self._remove_file_symbols(file_path)
        
        # 重新索引文件
        self.builder._index_file(file_path)
        
        # 更新跟踪信息
        self.tracker.update_file_tracking(file_path)
        
        return True
    
    @safe_file_operation
    def _add_new_file(self, file_path: str) -> None:
        """添加新文件 - 标准索引流程"""
        self.builder._index_file(file_path)
        self.tracker.update_file_tracking(file_path)
    
    def _remove_file(self, file_path: str) -> None:
        """移除文件索引 - 清理操作"""
        # 从文件索引中移除
        self.index.files.pop(file_path, None)
        
        # 移除相关符号
        self._remove_file_symbols(file_path)
        
        # 移除跟踪
        self.tracker.remove_file_tracking(file_path)
    
    def _remove_file_symbols(self, file_path: str) -> None:
        """移除文件相关符号 - Linus原则: 直接数据操作"""
        # 找到所有属于该文件的符号并移除
        symbols_to_remove = [
            symbol_name for symbol_name, symbol_info in self.index.symbols.items()
            if symbol_info.file == file_path
        ]
        
        for symbol_name in symbols_to_remove:
            self.index.symbols.pop(symbol_name, None)
    
    def force_update_file(self, file_path: str) -> bool:
        """强制更新指定文件 - 忽略变更检测"""
        if not Path(file_path).exists():
            self._remove_file(file_path)
            return True
        
        self._remove_file_symbols(file_path)
        self.builder._index_file(file_path)
        self.tracker.update_file_tracking(file_path)
        return True
    
    def get_changed_files(self) -> List[str]:
        """获取变更文件列表 - 诊断工具"""
        changed_files = []
        for file_path in self._scan_current_files():
            if self.tracker.is_file_changed(file_path):
                changed_files.append(file_path)
        return changed_files
    
    def get_stats(self) -> Dict[str, int]:
        """获取增量索引统计 - 监控信息"""
        current_files = self._scan_current_files()
        indexed_files = set(self.index.files.keys())
        
        return {
            "tracked_files": len(self.tracker.file_hashes),
            "current_files": len(current_files),
            "indexed_files": len(indexed_files),
            "changed_files": len(self.get_changed_files()),
            "missing_files": len(indexed_files - current_files),
            "new_files": len(current_files - indexed_files)
        }


# Linus原则: 简单的全局访问模式
_global_incremental_indexer: Optional[IncrementalIndexer] = None


def get_incremental_indexer() -> IncrementalIndexer:
    """获取全局增量索引器 - 单例模式"""
    global _global_incremental_indexer
    if _global_incremental_indexer is None:
        from .index import get_index
        _global_incremental_indexer = IncrementalIndexer(get_index())
    return _global_incremental_indexer


def reset_incremental_indexer() -> None:
    """重置增量索引器 - 测试辅助"""
    global _global_incremental_indexer
    _global_incremental_indexer = None