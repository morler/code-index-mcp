"""
Search Engine - Linus风格重构版本

Phase 3并行搜索引擎 - 符合200行限制
"""

import json
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from .index import CodeIndex, SearchQuery, SearchResult
from .search_cache import SearchCacheMixin
from .search_parallel import ParallelSearchMixin


class SearchEngine(ParallelSearchMixin, SearchCacheMixin):
    """搜索引擎 - Linus风格组合设计"""

    def __init__(self, index: CodeIndex):
        ParallelSearchMixin.__init__(self, index)
        SearchCacheMixin.__init__(self, index)

    def search(self, query: SearchQuery) -> SearchResult:
        """统一搜索分派 - Phase 4智能缓存版本"""
        start_time = time.time()

        # Phase 4: 智能查询结果缓存
        cached_result = self.get_cached_query_result(query)
        if cached_result:
            return cached_result

        # 简单分派 - 无特殊情况
        search_methods = {
            "text": self._search_text,
            "regex": self._search_regex,
            "symbol": self._search_symbol,
            "references": self._find_references,
            "definition": self._find_definition,
            "callers": self._find_callers,
        }

        search_method = search_methods.get(query.type)
        matches = search_method(query) if search_method else []

        # Phase 3: 早期退出优化
        if query.limit and len(matches) > query.limit:
            matches = matches[: query.limit]

        result = SearchResult(
            matches=matches,
            total_count=len(matches),
            search_time=time.time() - start_time,
        )

        # Phase 4: 智能缓存结果和依赖
        self.cache_query_result(query, result)
        return result

    def _search_text(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """文本搜索 - ripgrep优先，fallback到原实现"""
        # 检查ripgrep可用性
        if shutil.which("rg"):
            return self._search_with_ripgrep(query)

        # Fallback到原实现
        file_count = len(self.index.files)
        if self._should_use_parallel(file_count):
            return self.search_text_parallel(query)
        else:
            return self._search_text_single(query)

    def _search_text_single(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """单线程文本搜索"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for file_path, file_info in self.index.files.items():
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
                    if query.limit and len(matches) >= query.limit:
                        return matches
        return matches

    def _search_regex(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """正则搜索 - ripgrep优先，fallback到原实现"""
        # 检查ripgrep可用性
        if shutil.which("rg"):
            return self._search_regex_with_ripgrep(query)

        # Fallback到原实现
        try:
            regex = re.compile(
                query.pattern, 0 if query.case_sensitive else re.IGNORECASE
            )
        except re.error:
            return []

        file_count = len(self.index.files)
        if self._should_use_parallel(file_count):
            return self.search_regex_parallel(query, regex)
        else:
            return self._search_regex_single(query, regex)

    def _search_regex_single(self, query: SearchQuery, regex) -> List[Dict[str, Any]]:
        """单线程正则搜索"""
        matches = []
        for file_path, file_info in self.index.files.items():
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
                    if query.limit and len(matches) >= query.limit:
                        return matches
        return matches

    def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索 - ripgrep优先，fallback到索引搜索"""
        # 检查ripgrep可用性
        if shutil.which("rg"):
            return self._search_symbol_with_ripgrep(query)

        # Fallback到原实现 - 直接数据访问
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for symbol_name, symbol_info in self.index.symbols.items():
            search_name = (
                symbol_name.lower() if not query.case_sensitive else symbol_name
            )
            if pattern in search_name:
                matches.append(
                    {
                        "symbol": symbol_name,
                        "type": symbol_info.type,
                        "file": symbol_info.file,
                        "line": symbol_info.line,
                    }
                )
                if query.limit and len(matches) >= query.limit:
                    break
        return matches

    def _find_references(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找引用 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []
        return (
            [
                {
                    "file": ref.split(":")[0],
                    "line": int(ref.split(":")[1]),
                    "type": "reference",
                }
                for ref in symbol_info.references
                if ":" in ref
            ][: query.limit]
            if query.limit
            else [
                {
                    "file": ref.split(":")[0],
                    "line": int(ref.split(":")[1]),
                    "type": "reference",
                }
                for ref in symbol_info.references
                if ":" in ref
            ]
        )

    def _find_definition(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找定义 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        return (
            [{"file": symbol_info.file, "line": symbol_info.line, "type": "definition"}]
            if symbol_info
            else []
        )

    def _find_callers(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找调用者 - 最简实现"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []
        matches = []
        for caller in symbol_info.called_by:
            caller_info = self.index.symbols.get(caller)
            if caller_info:
                matches.append(
                    {
                        "symbol": caller,
                        "file": caller_info.file,
                        "line": caller_info.line,
                        "type": "caller",
                    }
                )
                if query.limit and len(matches) >= query.limit:
                    break
        return matches

    def _run_ripgrep_command(self, cmd: List[str], timeout: int = 30) -> Optional[str]:
        """公共的ripgrep命令执行方法 - 统一错误处理和超时"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return None

    def _search_with_ripgrep(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """ripgrep搜索实现 - 高性能文本搜索"""
        cmd = ["rg", "--json", "--line-number"]
        if not query.case_sensitive:
            cmd.append("--ignore-case")
        if query.limit:
            cmd.extend(["--max-count", str(query.limit)])

        cmd.extend([query.pattern, self.index.base_path])

        output = self._run_ripgrep_command(cmd)
        if output:
            return self._parse_rg_output(output)
        else:
            # Fallback到原实现
            return self._search_text_single(query)

    def _parse_rg_output(self, output: str) -> List[Dict[str, Any]]:
        """解析ripgrep JSON输出"""
        matches = []
        for line in output.strip().split("\n"):
            if line:
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        file_path = data["data"]["path"]["text"]
                        matches.append(
                            {
                                "file": file_path,
                                "line": data["data"]["line_number"],
                                "content": data["data"]["lines"]["text"].strip(),
                                "language": self._detect_language(file_path),
                            }
                        )
                except json.JSONDecodeError:
                    continue
        return matches

    def _detect_language(self, file_path: str) -> str:
        """检测文件语言类型"""
        file_info = self.index.files.get(file_path)
        return file_info.language if file_info else "unknown"

    def _search_regex_with_ripgrep(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """ripgrep正则搜索实现 - 高性能正则搜索"""
        cmd = ["rg", "--json", "--line-number", "--regexp"]
        if not query.case_sensitive:
            cmd.append("--ignore-case")
        if query.limit:
            cmd.extend(["--max-count", str(query.limit)])

        cmd.extend([query.pattern, self.index.base_path])

        output = self._run_ripgrep_command(cmd)
        if output:
            return self._parse_rg_output(output)
        else:
            # Fallback到原实现
            try:
                regex = re.compile(
                    query.pattern, 0 if query.case_sensitive else re.IGNORECASE
                )
                return self._search_regex_single(query, regex)
            except re.error:
                return []

    def _search_symbol_with_ripgrep(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """ripgrep符号搜索实现 - 高性能符号搜索"""
        cmd = ["rg", "--json", "--line-number", "-w"]  # -w为词边界匹配
        if not query.case_sensitive:
            cmd.append("--ignore-case")
        if query.limit:
            cmd.extend(["--max-count", str(query.limit)])

        cmd.extend([query.pattern, self.index.base_path])

        output = self._run_ripgrep_command(cmd)
        if output:
            return self._parse_rg_symbol_output(output, query.pattern)
        else:
            # Fallback到原实现
            return self._search_symbol_fallback(query)

    def _search_symbol_fallback(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """符号搜索fallback实现"""
        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []
        for symbol_name, symbol_info in self.index.symbols.items():
            search_name = (
                symbol_name.lower() if not query.case_sensitive else symbol_name
            )
            if pattern in search_name:
                matches.append(
                    {
                        "symbol": symbol_name,
                        "type": symbol_info.type,
                        "file": symbol_info.file,
                        "line": symbol_info.line,
                    }
                )
                if query.limit and len(matches) >= query.limit:
                    break
        return matches

    def _parse_rg_symbol_output(
        self, output: str, pattern: str
    ) -> List[Dict[str, Any]]:
        """解析ripgrep符号搜索输出"""
        matches = []
        for line in output.strip().split("\n"):
            if line:
                try:
                    data = json.loads(line)
                    if data.get("type") == "match":
                        file_path = data["data"]["path"]["text"]
                        line_content = data["data"]["lines"]["text"].strip()

                        # 尝试检测符号类型
                        symbol_type = self._detect_symbol_type(line_content, pattern)

                        matches.append(
                            {
                                "symbol": pattern,
                                "type": symbol_type,
                                "file": file_path,
                                "line": data["data"]["line_number"],
                                "content": line_content,
                                "language": self._detect_language(file_path),
                            }
                        )
                except json.JSONDecodeError:
                    continue
        return matches

    def _detect_symbol_type(self, line_content: str, symbol_name: str) -> str:
        """检测符号类型"""
        line_lower = line_content.lower()

        # 简单的符号类型检测
        if any(keyword in line_lower for keyword in ["def ", "function "]):
            return "function"
        elif any(keyword in line_lower for keyword in ["class "]):
            return "class"
        elif any(
            keyword in line_lower for keyword in ["const ", "let ", "var ", "final "]
        ):
            return "variable"
        elif any(keyword in line_lower for keyword in ["import ", "from "]):
            return "import"
        else:
            return "unknown"
