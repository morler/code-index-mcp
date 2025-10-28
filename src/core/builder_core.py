"""
Builder核心类 - Linus风格直接数据操作

包含IndexBuilder核心类，负责索引构建的主要逻辑。
遵循Linus原则：简单直接，<200行，零抽象层。
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from .builder_decorators import LANGUAGE_MAP, safe_file_operation
from .builder_languages import get_parser
from .index import CodeIndex, SymbolInfo


class IndexBuilder:
    """极简索引构建器 - 零抽象层"""

    def __init__(self, index: CodeIndex):
        self.index = index
        # Linus原则: 统一语言处理架构 - 零特殊情况
        self._language_processors = {
            ".py": self._process_python_ast,
            ".v": self._process_vlang_regex,
            ".rs": self._process_tree_sitter,
            ".js": self._process_tree_sitter,
            ".jsx": self._process_tree_sitter,
            ".ts": self._process_tree_sitter,
            ".tsx": self._process_tree_sitter,
            ".java": self._process_tree_sitter,
            ".go": self._process_tree_sitter,
            ".zig": self._process_tree_sitter,
            ".c": self._process_tree_sitter,
            ".h": self._process_tree_sitter,
            ".cpp": self._process_tree_sitter,
            ".hpp": self._process_tree_sitter,
            ".odin": self._process_tree_sitter,
        }

    def build_index(self, root_path: Optional[str] = None) -> None:
        """构建索引 - 直接扫描和解析"""
        if root_path:
            self.index.base_path = root_path

        for file_path in self._scan_files():
            self._index_file(file_path)

    @safe_file_operation
    def _scan_files(self) -> List[str]:
        """简单文件扫描 - Linus原则: 直接迭代"""
        files: List[str] = []
        base = Path(self.index.base_path)

        if not base.exists():
            return files

        # 支持的扩展名
        skip_dirs = {".venv", "__pycache__", ".git", "node_modules", "target", "build"}

        for root, dirs, filenames in os.walk(base):
            # 跳过不需要的目录
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for filename in filenames:
                if "." in filename:
                    ext = Path(filename).suffix.lower()
                    if ext in self._language_processors:
                        files.append(str(Path(root) / filename))

        return files

    @safe_file_operation
    def _index_file(self, file_path: str) -> None:
        """索引单个文件 - 统一分发"""
        ext = Path(file_path).suffix.lower()
        processor = self._language_processors.get(ext)

        if processor:
            processor(file_path)

    def _process_python_ast(self, file_path: str) -> None:
        """Python AST处理 - 直接符号提取"""
        try:
            import ast

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            symbols: Dict[str, List[str]] = {
                "functions": [],
                "classes": [],
                "imports": [],
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbols["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    symbols["classes"].append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            symbols["imports"].append(alias.name)
                    else:
                        module = node.module or ""
                        for alias in node.names:
                            symbols["imports"].append(f"{module}.{alias.name}")

            # 提取符号行号信息
            symbol_lines = self._extract_python_symbol_lines(content, symbols)

            # 注册符号到索引
            self._register_symbols_with_lines(symbols, symbol_lines, file_path)

        except Exception:
            # 静默失败，继续处理其他文件
            pass

    def _extract_python_symbol_lines(
        self, content: str, symbols: Dict[str, List[str]]
    ) -> Dict[str, int]:
        """提取Python符号的行号"""
        lines = content.split("\n")
        symbol_lines: Dict[str, int] = {}

        for symbol_name in symbols["functions"] + symbols["classes"]:
            for i, line in enumerate(lines, 1):
                if f"def {symbol_name}(" in line or f"class {symbol_name}:" in line:
                    symbol_lines[symbol_name] = i
                    break

        return symbol_lines

    def _process_vlang_regex(self, file_path: str) -> None:
        """V语言正则处理 - 简单有效"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            symbols: Dict[str, List[str]] = {
                "functions": [],
                "types": [],
                "imports": [],
            }

            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # 函数定义
                if re.match(r"^\w+\s*::.*\(", line):
                    func_name = re.split(r"\s*::", line)[0].strip()
                    symbols["functions"].append(func_name)

                # 类型定义
                elif re.match(r"^\w+\s*::.*struct", line):
                    type_name = re.split(r"\s*::", line)[0].strip()
                    symbols["types"].append(type_name)

                # 导入
                elif line.startswith("import "):
                    import_name = line.replace("import ", "").strip()
                    symbols["imports"].append(import_name)

            # 提取符号行号信息
            symbol_lines = self._extract_vlang_symbol_lines(content, symbols)

            # 注册符号到索引
            self._register_symbols_with_lines(symbols, symbol_lines, file_path)

        except Exception:
            pass

    def _extract_vlang_symbol_lines(
        self, content: str, symbols: Dict[str, List[str]]
    ) -> Dict[str, int]:
        """提取V语言符号的行号"""
        lines = content.split("\n")
        symbol_lines: Dict[str, int] = {}

        for symbol_name in symbols["functions"] + symbols["types"]:
            for i, line in enumerate(lines, 1):
                if f"{symbol_name} ::" in line:
                    symbol_lines[symbol_name] = i
                    break

        return symbol_lines

    def _process_tree_sitter(self, file_path: str) -> None:
        """Tree-sitter统一处理 - 支持多种语言"""
        try:
            parser = get_parser(Path(file_path).suffix.lower())
            if not parser:
                return

            with open(file_path, "rb") as f:
                content = f.read()

            tree = parser.parse(content)
            symbols: Dict[str, List[str]] = {
                "functions": [],
                "classes": [],
                "types": [],
                "imports": [],
            }

            def extract_symbols(node, depth=0):
                if depth > 20:  # 防止过深递归
                    return

                node_type = node.type

                # 根据语言类型判断符号类型
                if node_type in [
                    "function_definition",
                    "function_declaration",
                    "method_definition",
                ]:
                    if node.child_count > 0:
                        child = node.child_by_field_name("name") or node.child(0)
                        if child:
                            symbols["functions"].append(child.text.decode())

                elif node_type in [
                    "class_definition",
                    "class_declaration",
                    "struct_definition",
                ]:
                    if node.child_count > 0:
                        child = node.child_by_field_name("name") or node.child(0)
                        if child:
                            symbols["classes"].append(child.text.decode())

                elif node_type in ["type_definition", "type_alias_declaration"]:
                    if node.child_count > 0:
                        child = node.child_by_field_name("name") or node.child(0)
                        if child:
                            symbols["types"].append(child.text.decode())

                # 递归处理子节点
                for child in node.children:
                    extract_symbols(child, depth + 1)

            extract_symbols(tree.root_node)

            # 提取符号行号信息
            symbol_lines = self._extract_tree_sitter_symbol_lines(
                content, symbols, tree
            )

            # 注册符号到索引
            self._register_symbols_with_lines(symbols, symbol_lines, file_path)

        except Exception:
            pass

    def _extract_tree_sitter_symbol_lines(
        self, content: bytes, symbols: Dict[str, List[str]], tree
    ) -> Dict[str, int]:
        """从Tree-sitter解析树中提取符号行号"""
        symbol_lines: Dict[str, int] = {}
        content_str = content.decode("utf-8", errors="ignore")
        lines = content_str.split("\n")

        def find_symbol_nodes(node, target_symbols):
            """递归查找符号节点"""
            found_nodes = []

            node_type = node.type
            symbol_name = None
            symbol_type = None

            if node_type in [
                "function_definition",
                "function_declaration",
                "method_definition",
            ]:
                if node.child_count > 0:
                    child = node.child_by_field_name("name") or node.child(0)
                    if child:
                        symbol_name = child.text.decode()
                        symbol_type = "function"

            elif node_type in [
                "class_definition",
                "class_declaration",
                "struct_definition",
            ]:
                if node.child_count > 0:
                    child = node.child_by_field_name("name") or node.child(0)
                    if child:
                        symbol_name = child.text.decode()
                        symbol_type = "class"

            elif node_type in ["type_definition", "type_alias_declaration"]:
                if node.child_count > 0:
                    child = node.child_by_field_name("name") or node.child(0)
                    if child:
                        symbol_name = child.text.decode()
                        symbol_type = "type"

            if symbol_name and symbol_name in target_symbols:
                found_nodes.append((symbol_name, node.start_point.row + 1))

            for child in node.children:
                found_nodes.extend(find_symbol_nodes(child, target_symbols))

            return found_nodes

        # 查找所有符号的行号
        all_symbols = symbols["functions"] + symbols["classes"] + symbols["types"]
        found_symbols = find_symbol_nodes(tree.root_node, all_symbols)

        for symbol_name, line_num in found_symbols:
            symbol_lines[symbol_name] = line_num

        return symbol_lines

    def _register_symbols_with_lines(
        self,
        symbols: Dict[str, List[str]],
        symbol_lines: Dict[str, int],
        file_path: str,
    ) -> None:
        """注册符号到索引 - 使用正确的行号"""
        for symbol_type, symbol_list in symbols.items():
            for symbol in symbol_list:
                if symbol:  # 确保非空
                    # 正确的单数形式转换
                    if symbol_type == "functions":
                        type_name = "function"
                    elif symbol_type == "classes":
                        type_name = "class"
                    elif symbol_type == "imports":
                        type_name = "import"
                    elif symbol_type == "types":
                        type_name = "type"
                    else:
                        type_name = symbol_type.rstrip("s")

                    # 使用提取的实际行号，如果没有找到则使用1作为默认值
                    line_number = symbol_lines.get(symbol, 1)

                    symbol_info = SymbolInfo(
                        type=type_name,
                        file=file_path,
                        line=line_number,  # 使用实际行号
                    )
                    self.index.add_symbol(symbol, symbol_info)
