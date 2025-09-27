"""
Linus风格文件监控 - 直接数据操作，零抽象层

Good Taste原则:
1. 文件变化 → 直接更新索引 (无队列，无延迟)
2. 统一事件处理 → 消除if/else特殊情况
3. 简单直接 → 10行核心逻辑搞定复杂监控

改进版本:
- 精细化错误处理，区分不同异常类型
- 内存优化，定期清理事件缓存
- 路径标准化，处理符号链接
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .index import CodeIndex


class FileWatcher:
    """
    Linus风格文件监控器 - 改进版实现

    核心思想: 文件变化立即更新索引，无特殊情况
    改进点: 精细化错误处理，内存优化，路径标准化
    """

    def __init__(self, index: CodeIndex):
        self.index = index
        self.observer: Optional[Observer] = None
        self._is_watching = False
        self._lock = threading.RLock()

        # Linus洞察: 用集合而不是列表避免重复事件
        self._supported_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".go",
            ".zig",
            ".rs",
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
        }

        # 防抖动 - 避免频繁的连续事件
        self._debounce_time = 0.1  # 100ms
        self._last_events: Dict[str, float] = {}

        # 内存优化: 定期清理旧事件缓存
        self._max_cache_size = 1000  # 最大缓存文件数
        self._cache_cleanup_threshold = 300  # 清理阈值(秒)
        self._last_cleanup = time.time()

        # 错误统计 - 用于调试
        self._error_stats = {
            "permission_errors": 0,
            "file_not_found": 0,
            "index_errors": 0,
            "other_errors": 0,
        }

    def start_watching(self) -> bool:
        """开始监控 - Linus原则: 一个函数做一件完整的事"""
        with self._lock:
            if self._is_watching:
                return True  # 已经在监控

            if not self.index.base_path:
                return False  # 无项目路径

            try:
                self.observer = Observer()
                handler = _IndexEventHandler(self)

                # 递归监控整个项目目录
                self.observer.schedule(handler, self.index.base_path, recursive=True)

                self.observer.start()
                self._is_watching = True
                return True

            except Exception:
                return False

    def stop_watching(self) -> None:
        """停止监控 - 改进的资源清理"""
        with self._lock:
            if self.observer and self._is_watching:
                try:
                    self.observer.stop()
                    # 改进: 更长的超时时间，确保线程正确清理
                    if not self.observer.join(timeout=3.0):
                        # 如果3秒内没有正常结束，记录警告但继续
                        logging.warning("File watcher observer did not stop cleanly")
                except Exception as e:
                    logging.error(f"Error stopping file watcher: {e}")
                finally:
                    self.observer = None

            self._is_watching = False
            self._last_events.clear()
            # 重置错误统计
            for key in self._error_stats:
                self._error_stats[key] = 0

    def is_watching(self) -> bool:
        """监控状态查询"""
        return self._is_watching

    def handle_file_event(self, event: FileSystemEvent) -> None:
        """
        统一文件事件处理 - Good Taste: 消除特殊情况

        所有事件都走这一个入口，避免重复逻辑
        """
        if event.is_directory:
            return  # 只处理文件事件

        file_path = event.src_path

        # 防抖动处理 - 避免短时间内重复处理同一文件
        if self._should_debounce(file_path):
            return

        # 文件类型过滤 - 只处理支持的代码文件
        if not self._is_supported_file(file_path):
            return

        # 改进: 标准化文件路径，处理符号链接
        normalized_path = self._normalize_file_path(file_path)

        # 改进: 精细化错误处理，分类处理不同异常
        try:
            # 文件存在 → 强制更新索引
            if os.path.exists(normalized_path):
                self.index.force_update_file(normalized_path)
            else:
                # 文件被删除 → 从索引中移除
                self.index.remove_file(normalized_path)

        except PermissionError:
            self._error_stats["permission_errors"] += 1
            logging.debug(f"Permission denied accessing file: {normalized_path}")
        except FileNotFoundError:
            self._error_stats["file_not_found"] += 1
            # 文件已被删除，确保从索引中移除
            try:
                self.index.remove_file(normalized_path)
            except Exception:
                pass
        except OSError as e:
            self._error_stats["other_errors"] += 1
            logging.debug(f"OS error processing file {normalized_path}: {e}")
        except Exception as e:
            self._error_stats["index_errors"] += 1
            logging.debug(f"Index error processing file {normalized_path}: {e}")
            # 索引错误不影响文件监控继续运行

    def _should_debounce(self, file_path: str) -> bool:
        """防抖动检查 - 改进版，包含内存优化"""
        current_time = time.time()

        # 内存优化: 定期清理旧事件缓存
        self._cleanup_old_events_if_needed(current_time)

        last_time = self._last_events.get(file_path, 0)

        if current_time - last_time < self._debounce_time:
            return True  # 需要防抖

        self._last_events[file_path] = current_time
        return False

    def _cleanup_old_events_if_needed(self, current_time: float) -> None:
        """内存优化: 定期清理过期的事件缓存"""
        # 检查是否需要清理
        if (
            current_time - self._last_cleanup < self._cache_cleanup_threshold
            and len(self._last_events) < self._max_cache_size
        ):
            return

        # 清理超过阈值时间的旧事件
        cutoff_time = current_time - self._cache_cleanup_threshold
        old_keys = [
            path
            for path, timestamp in self._last_events.items()
            if timestamp < cutoff_time
        ]

        for key in old_keys:
            del self._last_events[key]

        # 如果缓存仍然太大，保留最新的条目
        if len(self._last_events) > self._max_cache_size:
            # 按时间戳排序，保留最新的max_cache_size个
            sorted_events = sorted(
                self._last_events.items(), key=lambda x: x[1], reverse=True
            )
            self._last_events = dict(sorted_events[: self._max_cache_size])

        self._last_cleanup = current_time

    def _is_supported_file(self, file_path: str) -> bool:
        """检查是否为支持的文件类型 - 避免无效监控"""
        try:
            return Path(file_path).suffix.lower() in self._supported_extensions
        except Exception:
            return False

    def _normalize_file_path(self, file_path: str) -> str:
        """标准化文件路径 - 处理符号链接和路径标准化"""
        try:
            path_obj = Path(file_path)

            # 解析符号链接到实际路径
            if path_obj.is_symlink():
                resolved_path = path_obj.resolve()
                # 确保解析后的路径存在且在项目目录内
                if resolved_path.exists() and str(resolved_path).startswith(
                    str(Path(self.index.base_path).resolve())
                ):
                    return str(resolved_path)

            # 标准化路径（解决相对路径、.、..等问题）
            return str(path_obj.resolve())

        except (OSError, RuntimeError):
            # 如果路径解析失败，返回原始路径
            return file_path

    def get_stats(self) -> dict:
        """监控统计信息 - 改进版，包含错误统计"""
        return {
            "is_watching": self._is_watching,
            "base_path": self.index.base_path,
            "supported_extensions": list(self._supported_extensions),
            "debounce_time": self._debounce_time,
            "tracked_events": len(self._last_events),
            "max_cache_size": self._max_cache_size,
            "cache_cleanup_threshold": self._cache_cleanup_threshold,
            "error_stats": self._error_stats.copy(),
            "memory_usage": {
                "event_cache_size": len(self._last_events),
                "cache_utilization": f"{len(self._last_events)}/{self._max_cache_size}",
            },
        }


class _IndexEventHandler(FileSystemEventHandler):
    """
    私有事件处理器 - Linus风格: 最小化公共接口
    """

    def __init__(self, watcher: FileWatcher):
        self.watcher = watcher

    def on_any_event(self, event: FileSystemEvent) -> None:
        """
        统一事件入口 - Good Taste实现

        不管是created/modified/deleted，都用同一个处理逻辑
        让FileWatcher决定具体操作，消除重复代码
        """
        self.watcher.handle_file_event(event)


# Linus原则: 简单的全局访问模式
_global_watcher: Optional[FileWatcher] = None
_watcher_lock = threading.RLock()


def get_file_watcher() -> Optional[FileWatcher]:
    """获取全局文件监控器 - 可能为空"""
    return _global_watcher


def start_auto_indexing(index: CodeIndex) -> bool:
    """
    启动自动索引 - 主要入口函数

    返回: True表示成功启动，False表示失败
    """
    global _global_watcher

    with _watcher_lock:
        # 如果已有监控器在运行，先停止
        if _global_watcher:
            _global_watcher.stop_watching()

        _global_watcher = FileWatcher(index)
        return _global_watcher.start_watching()


def stop_auto_indexing() -> None:
    """停止自动索引 - 清理全局资源"""
    global _global_watcher

    with _watcher_lock:
        if _global_watcher:
            _global_watcher.stop_watching()
            _global_watcher = None


def is_auto_indexing_active() -> bool:
    """检查自动索引是否活跃"""
    with _watcher_lock:
        return _global_watcher is not None and _global_watcher.is_watching()


def get_watcher_stats() -> dict:
    """获取监控统计信息 - 调试工具"""
    with _watcher_lock:
        if _global_watcher:
            return _global_watcher.get_stats()
        return {"is_watching": False, "message": "No watcher active"}
