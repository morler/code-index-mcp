#!/usr/bin/env python3
"""
Phase 5: I/O Optimization - Async File Operations and Memory Mapping

Linus风格I/O优化 - 消除阻塞，直接数据操作
"""

import asyncio
import mmap
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiofiles


class AsyncFileReader:
    """异步文件读取器 - 消除I/O阻塞"""

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._memory_mapped_files: Dict[str, mmap.mmap] = {}

    async def read_file_async(
        self, file_path: Union[str, Path], encoding: str = "utf-8"
    ) -> str:
        """异步读取文件内容 - 非阻塞操作"""
        file_path = Path(file_path)

        # 大文件使用内存映射
        if file_path.stat().st_size > 1024 * 1024:  # 1MB+
            return await self._read_large_file_mmap(file_path, encoding)

        # 小文件使用aiofiles
        return await self._read_small_file_async(file_path, encoding)

    async def _read_small_file_async(self, file_path: Path, encoding: str) -> str:
        """小文件异步读取 - aiofiles优化"""
        try:
            async with aiofiles.open(
                file_path, "r", encoding=encoding, errors="ignore"
            ) as f:
                return await f.read()
        except Exception:
            return ""

    async def _read_large_file_mmap(self, file_path: Path, encoding: str) -> str:
        """大文件内存映射读取 - 零拷贝优化"""

        def _mmap_read():
            try:
                with open(file_path, "rb") as f:
                    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                        return mm.read().decode(encoding, errors="ignore")
            except Exception:
                return ""

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _mmap_read)

    async def read_file_lines_async(
        self, file_path: Union[str, Path], encoding: str = "utf-8"
    ) -> List[str]:
        """异步按行读取文件 - 流式处理"""
        file_path = Path(file_path)

        try:
            lines = []
            async with aiofiles.open(
                file_path, "r", encoding=encoding, errors="ignore"
            ) as f:
                async for line in f:
                    lines.append(line.rstrip("\n\r"))
            return lines
        except Exception:
            return []

    async def batch_read_files(
        self, file_paths: List[Union[str, Path]], encoding: str = "utf-8"
    ) -> Dict[str, str]:
        """批量异步读取文件 - 并发优化"""
        tasks = []
        for file_path in file_paths:
            task = self.read_file_async(file_path, encoding)
            tasks.append((str(file_path), task))

        results = {}
        for file_path, task in tasks:
            try:
                content = await task
                results[file_path] = content
            except Exception:
                results[file_path] = ""

        return results

    def close(self):
        """清理资源"""
        for mm in self._memory_mapped_files.values():
            if not mm.closed:
                mm.close()
        self._memory_mapped_files.clear()
        self.executor.shutdown(wait=True)


class OptimizedDirectoryScanner:
    """优化的目录扫描器 - 并行扫描"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def scan_directory_async(
        self, base_path: Path, supported_extensions: set, skip_dirs: set
    ) -> List[str]:
        """异步并行目录扫描 - 消除I/O等待"""

        def _scan_single_dir(dir_path: str) -> List[str]:
            """单个目录扫描 - os.scandir优化"""
            local_files = []
            try:
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            name = entry.name
                            if "." in name:
                                ext = "." + name.split(".")[-1].lower()
                                if ext in supported_extensions:
                                    local_files.append(entry.path)
                        elif entry.is_dir(follow_symlinks=False):
                            if entry.name not in skip_dirs:
                                # 递归扫描子目录
                                local_files.extend(_scan_single_dir(entry.path))
            except (OSError, PermissionError):
                pass
            return local_files

        # 获取根级目录列表
        root_dirs = []
        root_files = []

        try:
            with os.scandir(str(base_path)) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in skip_dirs:
                            root_dirs.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        name = entry.name
                        if "." in name:
                            ext = "." + name.split(".")[-1].lower()
                            if ext in supported_extensions:
                                root_files.append(entry.path)
        except (OSError, PermissionError):
            return []

        # 并行扫描所有根级目录
        loop = asyncio.get_event_loop()
        tasks = []

        for root_dir in root_dirs:
            task = loop.run_in_executor(self.executor, _scan_single_dir, root_dir)
            tasks.append(task)

        # 等待所有扫描任务完成
        all_files = root_files[:]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, list):
                    all_files.extend(result)

        return all_files

    def close(self):
        """清理资源"""
        self.executor.shutdown(wait=True)


# 全局实例 - Linus风格简单直接
_async_file_reader: Optional[AsyncFileReader] = None
_directory_scanner: Optional[OptimizedDirectoryScanner] = None


def get_async_file_reader() -> AsyncFileReader:
    """获取全局异步文件读取器"""
    global _async_file_reader
    if _async_file_reader is None:
        _async_file_reader = AsyncFileReader()
    return _async_file_reader


def get_directory_scanner() -> OptimizedDirectoryScanner:
    """获取全局目录扫描器"""
    global _directory_scanner
    if _directory_scanner is None:
        _directory_scanner = OptimizedDirectoryScanner()
    return _directory_scanner


def cleanup_io_resources():
    """清理全局I/O资源"""
    global _async_file_reader, _directory_scanner

    if _async_file_reader:
        _async_file_reader.close()
        _async_file_reader = None

    if _directory_scanner:
        _directory_scanner.close()
        _directory_scanner = None


# 同步兼容性包装器 - 保持向后兼容
def read_file_optimized(file_path: Union[str, Path], encoding: str = "utf-8") -> str:
    """优化的同步文件读取 - 保持兼容性"""

    async def _read():
        reader = get_async_file_reader()
        return await reader.read_file_async(file_path, encoding)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果在异步上下文中，创建新的事件循环
            import threading

            result = [None]
            exception = [None]

            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result[0] = new_loop.run_until_complete(_read())
                except Exception as e:
                    exception[0] = e
                finally:
                    new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if exception[0]:
                raise exception[0]
            return result[0]
        else:
            return loop.run_until_complete(_read())
    except RuntimeError:
        # 没有事件循环，创建新的
        return asyncio.run(_read())


def read_file_lines_optimized(
    file_path: Union[str, Path], encoding: str = "utf-8"
) -> List[str]:
    """优化的同步按行读取 - 保持兼容性"""

    async def _read():
        reader = get_async_file_reader()
        return await reader.read_file_lines_async(file_path, encoding)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import threading

            result = [None]
            exception = [None]

            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result[0] = new_loop.run_until_complete(_read())
                except Exception as e:
                    exception[0] = e
                finally:
                    new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if exception[0]:
                raise exception[0]
            return result[0]
        else:
            return loop.run_until_complete(_read())
    except RuntimeError:
        return asyncio.run(_read())
