"""
Search Engine - Linus风格重构版本

Phase 3并行搜索引擎 - 符合200行限制
"""

import json
import logging
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from .index import CodeIndex, SearchQuery, SearchResult
from .search_cache import SearchCacheMixin
from .search_parallel import ParallelSearchMixin

# 设置日志记录
logger = logging.getLogger(__name__)


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
        """符号搜索 - 优先使用索引搜索，改进fallback机制"""
        logger.debug(
            f"Starting symbol search for pattern: {query.pattern}, type: {query.type}"
        )

        try:
            # 1. 优先使用索引搜索（最可靠）
            index_matches = self._search_symbol_index(query)
            if index_matches:
                logger.debug(f"Found {len(index_matches)} matches via index search")
                return index_matches[: query.limit] if query.limit else index_matches

            logger.debug("Index search returned no results, trying ripgrep fallback")

            # 2. fallback 到简单 ripgrep 搜索
            if shutil.which("rg"):
                rg_matches = self._search_symbol_simple_rg(query)
                if rg_matches:
                    logger.debug(
                        f"Found {len(rg_matches)} matches via ripgrep fallback"
                    )
                    return rg_matches[: query.limit] if query.limit else rg_matches
                else:
                    logger.debug("Ripgrep fallback returned no results")
            else:
                logger.debug("Ripgrep not available, no fallback possible")

        except Exception as e:
            logger.error(
                f"Error during symbol search for pattern '{query.pattern}': {e}"
            )

        logger.debug(f"No matches found for pattern: {query.pattern}")
        return []

    def _search_symbol_index(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """索引符号搜索 - 支持精确、前缀、子串匹配"""
        logger.debug(f"Starting index symbol search for pattern: {query.pattern}")

        pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
        matches = []

        try:
            total_symbols = len(self.index.symbols)
            logger.debug(f"Searching through {total_symbols} indexed symbols")

            for symbol_name, symbol_info in self.index.symbols.items():
                search_name = (
                    symbol_name.lower() if not query.case_sensitive else symbol_name
                )

                # 支持多种匹配策略
                is_match = False
                if query.case_sensitive:
                    # 精确匹配
                    if symbol_name == pattern:
                        is_match = True
                    # 前缀匹配
                    elif symbol_name.startswith(pattern):
                        is_match = True
                    # 子串匹配
                    elif pattern in symbol_name:
                        is_match = True
                else:
                    # 大小写不敏感匹配
                    if search_name == pattern:
                        is_match = True
                    elif search_name.startswith(pattern):
                        is_match = True
                    elif pattern in search_name:
                        is_match = True

                if is_match:
                    matches.append(
                        {
                            "symbol": symbol_name,
                            "type": symbol_info.type,
                            "file": symbol_info.file,
                            "line": symbol_info.line,
                        }
                    )

            logger.debug(f"Index search found {len(matches)} potential matches")

            # 按匹配质量排序：精确匹配 > 前缀匹配 > 子串匹配
            if query.case_sensitive:
                matches.sort(
                    key=lambda m: (
                        0
                        if str(m["symbol"]) == pattern
                        else 1
                        if str(m["symbol"]).startswith(pattern)
                        else 2
                    )
                )
            else:
                matches.sort(
                    key=lambda m: (
                        0
                        if str(m["symbol"]).lower() == pattern
                        else 1
                        if str(m["symbol"]).lower().startswith(pattern)
                        else 2
                    )
                )

            return matches

        except Exception as e:
            logger.error(f"Error during index symbol search: {e}")
            return []

    def _search_symbol_simple_rg(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """简化的ripgrep符号搜索 - 使用更简单的模式"""
        # 使用简单的词边界搜索
        cmd = ["rg", "--json", "--line-number", "-w"]
        if not query.case_sensitive:
            cmd.append("--ignore-case")
        if query.limit:
            cmd.extend(["--max-count", str(query.limit)])

        cmd.extend([query.pattern, self.index.base_path])

        output = self._run_ripgrep_command(cmd)
        if output:
            return self._parse_rg_symbol_output(output, query.pattern)
        else:
            return []

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
        """简化的ripgrep符号搜索实现 - 使用简单模式"""
        # 直接使用简单词边界搜索
        return self._search_symbol_simple_rg(query)

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
                        language = self._detect_language(file_path)
                        symbol_type = self._detect_symbol_type(
                            line_content, pattern, language
                        )

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

    def _detect_symbol_type(
        self, line_content: str, symbol_name: str, language: str = "unknown"
    ) -> str:
        """检测符号类型 - 增强版本，支持语言特定检测"""
        line = line_content.strip()
        line_lower = line.lower()

        # 语言特定的检测策略
        if language in ["python", "py"]:
            return self._detect_python_symbol_type(line, symbol_name)
        elif language in ["javascript", "js", "typescript", "ts"]:
            return self._detect_javascript_symbol_type(line, symbol_name)
        elif language in ["java"]:
            return self._detect_java_symbol_type(line, symbol_name)
        elif language in ["c", "cpp", "c++", "cc"]:
            return self._detect_c_symbol_type(line, symbol_name)
        elif language in ["rust", "rs"]:
            return self._detect_rust_symbol_type(line, symbol_name)
        elif language in ["go"]:
            return self._detect_go_symbol_type(line, symbol_name)
        else:
            # 通用检测
            return self._detect_generic_symbol_type(line, symbol_name)

    def _detect_python_symbol_type(self, line: str, symbol_name: str) -> str:
        """Python符号类型检测"""
        # 函数检测
        if re.match(r"^(async\s+)?def\s+" + re.escape(symbol_name) + r"\s*\(", line):
            return "function"
        elif re.match(r"^(async\s+)?def\s+\w+\s*\(", line):
            return "function"

        # 类检测
        elif re.match(r"^class\s+" + re.escape(symbol_name) + r"\b", line):
            return "class"
        elif re.match(r"^class\s+\w+", line):
            return "class"

        # 变量检测
        elif re.match(r"^" + re.escape(symbol_name) + r"\s*=", line):
            return "variable"
        elif re.match(r"^\w+\s*=", line):
            return "variable"

        # 导入检测
        elif re.match(r"^import\s+.*" + re.escape(symbol_name), line):
            return "import"
        elif re.match(r"^from\s+.*\s+import\s+.*" + re.escape(symbol_name), line):
            return "import"

        return "unknown"

    def _detect_javascript_symbol_type(self, line: str, symbol_name: str) -> str:
        """JavaScript/TypeScript符号类型检测"""
        # 函数检测
        if re.match(r"^function\s+" + re.escape(symbol_name) + r"\s*\(", line):
            return "function"
        elif re.match(
            r"^const\s+" + re.escape(symbol_name) + r"\s*=\s*(async\s+)?\(", line
        ):
            return "function"
        elif re.match(
            r"^let\s+" + re.escape(symbol_name) + r"\s*=\s*(async\s+)?\(", line
        ):
            return "function"
        elif re.match(
            r"^var\s+" + re.escape(symbol_name) + r"\s*=\s*(async\s+)?\(", line
        ):
            return "function"
        elif re.match(r"^function\s+\w+\s*\(", line):
            return "function"

        # 类检测
        elif re.match(r"^class\s+" + re.escape(symbol_name) + r"\b", line):
            return "class"
        elif re.match(r"^class\s+\w+", line):
            return "class"

        # 变量检测
        elif re.match(r"^(const|let|var)\s+" + re.escape(symbol_name) + r"\s*=", line):
            return "variable"
        elif re.match(r"^(const|let|var)\s+\w+\s*=", line):
            return "variable"

        # 导入检测
        elif re.match(r"^import\s+.*" + re.escape(symbol_name), line):
            return "import"
        elif re.match(r"^require\s*\([\"'].*" + re.escape(symbol_name), line):
            return "import"

        return "unknown"

    def _detect_java_symbol_type(self, line: str, symbol_name: str) -> str:
        """Java符号类型检测"""
        # 方法检测
        if re.match(
            r"^(public|private|protected|static)?\s*(\w+\s+)*"
            + re.escape(symbol_name)
            + r"\s*\(",
            line,
        ):
            return "method"
        elif re.match(r"^(public|private|protected|static)?\s*(\w+\s+)*\w+\s*\(", line):
            return "method"

        # 类检测
        elif re.match(r"^(public\s+)?class\s+" + re.escape(symbol_name) + r"\b", line):
            return "class"
        elif re.match(r"^(public\s+)?(abstract\s+)?class\s+\w+", line):
            return "class"

        # 接口检测
        elif re.match(
            r"^(public\s+)?interface\s+" + re.escape(symbol_name) + r"\b", line
        ):
            return "interface"
        elif re.match(r"^(public\s+)?interface\s+\w+", line):
            return "interface"

        # 枚举检测
        elif re.match(r"^(public\s+)?enum\s+" + re.escape(symbol_name) + r"\b", line):
            return "enum"
        elif re.match(r"^(public\s+)?enum\s+\w+", line):
            return "enum"

        # 变量检测
        elif re.match(
            r"^(public|private|protected|static)?\s*(final\s+)?\w+\s+"
            + re.escape(symbol_name)
            + r"\s*[=;]",
            line,
        ):
            return "variable"
        elif re.match(
            r"^(public|private|protected|static)?\s*(final\s+)?\w+\s+\w+\s*[=;]", line
        ):
            return "variable"

        # 导入检测
        elif re.match(r"^import\s+.*" + re.escape(symbol_name), line):
            return "import"

        return "unknown"

    def _detect_c_symbol_type(self, line: str, symbol_name: str) -> str:
        """C/C++符号类型检测"""
        # 函数检测
        if re.match(
            r"^(extern\s+)?(static\s+)?(inline\s+)?\w+\s+"
            + re.escape(symbol_name)
            + r"\s*\(",
            line,
        ):
            return "function"
        elif re.match(r"^(extern\s+)?(static\s+)?(inline\s+)?\w+\s+\w+\s*\(", line):
            return "function"

        # 结构体检测
        elif re.match(r"^struct\s+" + re.escape(symbol_name) + r"\b", line):
            return "struct"
        elif re.match(r"^struct\s+\w+", line):
            return "struct"

        # 联合体检测
        elif re.match(r"^union\s+" + re.escape(symbol_name) + r"\b", line):
            return "union"
        elif re.match(r"^union\s+\w+", line):
            return "union"

        # 枚举检测
        elif re.match(r"^enum\s+" + re.escape(symbol_name) + r"\b", line):
            return "enum"
        elif re.match(r"^enum\s+\w+", line):
            return "enum"

        # 变量检测
        elif re.match(
            r"^(extern\s+)?(static\s+)?\w+\s+" + re.escape(symbol_name) + r"\s*[=;]",
            line,
        ):
            return "variable"
        elif re.match(r"^(extern\s+)?(static\s+)?\w+\s+\w+\s*[=;]", line):
            return "variable"

        # 宏定义检测
        elif re.match(r"#define\s+" + re.escape(symbol_name) + r"\b", line):
            return "macro"
        elif re.match(r"#define\s+\w+", line):
            return "macro"

        # 包含检测
        elif re.match(r'^#include\s+[<"]', line):
            return "include"

        return "unknown"

    def _detect_rust_symbol_type(self, line: str, symbol_name: str) -> str:
        """Rust符号类型检测"""
        # 函数检测
        if re.match(
            r"^(pub\s+)?(async\s+)?(unsafe\s+)?fn\s+"
            + re.escape(symbol_name)
            + r"\s*\(",
            line,
        ):
            return "function"
        elif re.match(r"^(pub\s+)?(async\s+)?(unsafe\s+)?fn\s+\w+\s*\(", line):
            return "function"

        # 结构体检测
        elif re.match(r"^struct\s+" + re.escape(symbol_name) + r"\b", line):
            return "struct"
        elif re.match(r"^struct\s+\w+", line):
            return "struct"

        # 枚举检测
        elif re.match(r"^enum\s+" + re.escape(symbol_name) + r"\b", line):
            return "enum"
        elif re.match(r"^enum\s+\w+", line):
            return "enum"

        # 特征检测
        elif re.match(r"^trait\s+" + re.escape(symbol_name) + r"\b", line):
            return "trait"
        elif re.match(r"^trait\s+\w+", line):
            return "trait"

        # 变量检测
        elif re.match(r"^(pub\s+)?(const\s+)?(static\s+)?\w+\s*:\s*\w+", line):
            return "variable"

        # 模块检测
        elif re.match(r"^mod\s+" + re.escape(symbol_name) + r"\b", line):
            return "module"
        elif re.match(r"^mod\s+\w+", line):
            return "module"

        # 使用检测
        elif re.match(r"^use\s+.*" + re.escape(symbol_name), line):
            return "import"
        elif re.match(r"^use\s+", line):
            return "import"

        return "unknown"

    def _detect_go_symbol_type(self, line: str, symbol_name: str) -> str:
        """Go符号类型检测"""
        # 函数检测
        if re.match(r"^func\s+" + re.escape(symbol_name) + r"\s*\(", line):
            return "function"
        elif re.match(r"^func\s+\w+\s*\(", line):
            return "function"

        # 结构体检测
        elif re.match(r"^type\s+" + re.escape(symbol_name) + r"\s+struct\b", line):
            return "struct"
        elif re.match(r"^type\s+\w+\s+struct\b", line):
            return "struct"

        # 接口检测
        elif re.match(r"^type\s+" + re.escape(symbol_name) + r"\s+interface\b", line):
            return "interface"
        elif re.match(r"^type\s+\w+\s+interface\b", line):
            return "interface"

        # 变量检测
        elif re.match(r"^var\s+" + re.escape(symbol_name) + r"\s+", line):
            return "variable"
        elif re.match(r"^var\s+\w+\s+", line):
            return "variable"

        # 常量检测
        elif re.match(r"^const\s+" + re.escape(symbol_name) + r"\s+", line):
            return "constant"
        elif re.match(r"^const\s+\w+\s+", line):
            return "constant"

        # 导入检测
        elif re.match(r"^import\s+.*" + re.escape(symbol_name), line):
            return "import"
        elif re.match(r"^import\s+", line):
            return "import"

        return "unknown"

    def _detect_generic_symbol_type(self, line: str, symbol_name: str) -> str:
        """通用符号类型检测 - 回退方案"""
        # 函数检测 - 更精确的模式
        function_patterns = [
            r"^def\s+\w+\s*\(",  # Python: def name(
            r"^function\s+\w+\s*\(",  # JavaScript: function name(
            r"^\w+\s*\([^)]*\)\s*[{:]",  # C/Java: name(...) { or :
            r"^\w+\s+operator\s*\(",  # C++: operator
            r"^async\s+def\s+\w+\s*\(",  # Python async
            r"^public\s+.*\s+\w+\s*\(",  # Java public method
            r"^private\s+.*\s+\w+\s*\(",  # Java private method
            r"^protected\s+.*\s+\w+\s*\(",  # Java protected method
            r"^static\s+.*\s+\w+\s*\(",  # Java/C# static method
        ]

        for pattern in function_patterns:
            if re.search(pattern, line):
                return "function"

        # 类检测
        class_patterns = [
            r"^class\s+\w+",  # Python/JavaScript: class Name
            r"^public\s+class\s+\w+",  # Java: public class Name
            r"^private\s+class\s+\w+",  # Java: private class Name
            r"^struct\s+\w+",  # C/C++: struct Name
            r"^interface\s+\w+",  # Java/C#: interface Name
            r"^enum\s+\w+",  # Java/C/C++: enum Name
        ]

        for pattern in class_patterns:
            if re.search(pattern, line):
                return "class"

        # 变量检测
        variable_patterns = [
            r"^const\s+\w+",  # JavaScript/TypeScript: const name
            r"^let\s+\w+",  # JavaScript/TypeScript: let name
            r"^var\s+\w+",  # JavaScript: var name
            r"^final\s+\w+",  # Java: final name
            r"^private\s+.*\s+\w+\s*[=;]",  # Java private field
            r"^public\s+.*\s+\w+\s*[=;]",  # Java public field
            r"^static\s+.*\s+\w+\s*[=;]",  # Java/C# static field
            r"^\w+\s+\w+\s*[=;]",  # General: type name = or ;
        ]

        for pattern in variable_patterns:
            if re.search(pattern, line):
                return "variable"

        # 导入检测
        import_patterns = [
            r"^import\s+",  # Python/Java/TypeScript: import
            r"^from\s+.*\s+import",  # Python: from ... import
            r'^#include\s+[<"]',  # C/C++: #include
            r"^require\s*\(",  # Node.js: require(
            r"^using\s+",  # C#: using
        ]

        for pattern in import_patterns:
            if re.search(pattern, line):
                return "import"

        # 方法检测（类中的函数）
        if symbol_name in line and any(
            keyword in line for keyword in ["def ", "function ", "operator "]
        ):
            return "method"

        return "unknown"
