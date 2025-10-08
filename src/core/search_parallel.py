"""
Parallel Search Engine - Phase 3并行搜索模块

Linus风格拆分 - 专注并行搜索逻辑
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from .index import CodeIndex, SearchQuery


class ParallelSearchMixin:
    """并行搜索混入 - Linus风格模块化"""

    def __init__(self, index: CodeIndex):
        self.index = index
        self._thread_pool: Optional[ThreadPoolExecutor] = None
        self._optimal_workers = min(4, max(1, len(index.files) // 10))

    @property
    def thread_pool(self):
        """懒加载线程池"""
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self._optimal_workers)
        return self._thread_pool

    def _should_use_parallel(self, file_count: int) -> bool:
        """判断是否使用并行 - 简单阈值"""
        return file_count >= 50

    def _read_file_lines(self, file_path: str) -> List[str]:
        """读取文件行 - 复用逻辑"""
        try:
            return (
                (Path(self.index.base_path) / file_path)
                .read_text(encoding="utf-8", errors="ignore")
                .split("\n")
            )
        except Exception:
            return []

    def search_text_parallel(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """并行文本搜索"""
        file_items = list(self.index.files.items())
        chunk_size = max(1, len(file_items) // self._optimal_workers)
        file_chunks = [
            file_items[i : i + chunk_size]
            for i in range(0, len(file_items), chunk_size)
        ]

        # 并行处理
        futures = []
        for chunk in file_chunks:
            future = self.thread_pool.submit(self._search_text_chunk, query, chunk)
            futures.append(future)

        # 收集结果
        matches = []
        for future in futures:
            chunk_matches = future.result()
            matches.extend(chunk_matches)
            # 早期退出
            if query.limit and len(matches) >= query.limit:
                matches = matches[: query.limit]
                break

        return matches

    def _search_text_chunk(
        self, query: SearchQuery, file_chunk: List
    ) -> List[Dict[str, Any]]:
        """文本搜索文件块"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for file_path, file_info in file_chunk:
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                search_line = line.lower() if not query.case_sensitive else line
                if pattern in search_line:
                    matches.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "content": line.strip(),
                            "language": file_info.language,
                        }
                    )
                    # 块级早期退出
                    if (
                        query.limit
                        and len(matches) >= query.limit // self._optimal_workers
                    ):
                        return matches
        return matches

    def search_regex_parallel(self, query: SearchQuery, regex) -> List[Dict[str, Any]]:
        """并行正则搜索"""
        file_items = list(self.index.files.items())
        chunk_size = max(1, len(file_items) // self._optimal_workers)
        file_chunks = [
            file_items[i : i + chunk_size]
            for i in range(0, len(file_items), chunk_size)
        ]

        # 并行处理
        futures = []
        for chunk in file_chunks:
            future = self.thread_pool.submit(
                self._search_regex_chunk, query, regex, chunk
            )
            futures.append(future)

        # 收集结果
        matches = []
        for future in futures:
            chunk_matches = future.result()
            matches.extend(chunk_matches)
            # 早期退出
            if query.limit and len(matches) >= query.limit:
                matches = matches[: query.limit]
                break

        return matches

    def _search_regex_chunk(
        self, query: SearchQuery, regex, file_chunk: List
    ) -> List[Dict[str, Any]]:
        """正则搜索文件块"""
        matches = []
        for file_path, file_info in file_chunk:
            lines = self._read_file_lines(file_path)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    matches.append(
                        {
                            "file": file_path,
                            "line": line_num,
                            "content": line.strip(),
                            "language": file_info.language,
                        }
                    )
                    # 块级早期退出
                    if (
                        query.limit
                        and len(matches) >= query.limit // self._optimal_workers
                    ):
                        return matches
        return matches

    def __del__(self):
        """清理资源"""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)
