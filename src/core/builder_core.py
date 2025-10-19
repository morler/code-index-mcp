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
from .index import CodeIndex


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
        files = []
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

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            symbols = {"functions": [], "classes": [], "imports": []}

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbols["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    symbols["classes"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    symbols["imports"].append(node.module)

            self._register_symbols(symbols, file_path)

        except Exception:
            # Linus原则: 静默失败，不中断整体流程
            pass

    def _process_vlang_regex(self, file_path: str) -> None:
        """V语言正则处理 - 简单模式匹配"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            symbols = {"functions": [], "classes": [], "imports": []}

            # 简单的正则匹配
            functions = re.findall(r'fn\s+(\w+)\s*\(', content)
            symbols["functions"] = functions

            imports = re.findall(r'import\s+([^\s]+)', content)
            symbols["imports"] = imports

            self._register_symbols(symbols, file_path)

        except Exception:
            pass

    def _process_tree_sitter(self, file_path: str) -> None:
        """Tree-sitter统一处理 - 支持多种语言"""
        try:
            from .builder_decorators import detect_language

            language = detect_language(file_path)
            parser = get_parser(language)

            if not parser:
                return

            with open(file_path, 'rb') as f:
                content = f.read()

            tree = parser.parse(content)
            symbols = {"functions": [], "classes": [], "imports": []}

            # 简单的节点遍历
            def walk_tree(node):
                if hasattr(node, 'type'):
                    node_type = node.type

                    # 函数定义
                    if 'function' in node_type.lower() or 'method' in node_type.lower():
                        name = self._extract_name(node, content)
                        if name:
                            symbols["functions"].append(name)

                    # 类定义
                    elif 'class' in node_type.lower():
                        name = self._extract_name(node, content)
                        if name:
                            symbols["classes"].append(name)

                    # 导入语句
                    elif 'import' in node_type.lower():
                        imp = self._extract_import(node, content)
                        if imp:
                            symbols["imports"].append(imp)

                for child in node.children:
                    walk_tree(child)

            walk_tree(tree.root_node)
            self._register_symbols(symbols, file_path)

        except Exception:
            pass

    def _extract_name(self, node, content: bytes) -> Optional[str]:
        """提取节点名称 - 简单实现"""
        try:
            for child in node.children:
                if hasattr(child, 'type') and 'identifier' in child.type:
                    start = child.start_byte
                    end = child.end_byte
                    return content[start:end].decode('utf-8')
        except Exception:
            pass
        return None

    def _extract_import(self, node, content: bytes) -> Optional[str]:
        """提取导入语句 - 简单实现"""
        try:
            start = node.start_byte
            end = node.end_byte
            return content[start:end].decode('utf-8').strip()
        except Exception:
            pass
        return None

    def _register_symbols(self, symbols: Dict[str, List[str]], file_path: str) -> None:
        """注册符号到索引 - 直接数据操作"""
        for symbol_type, symbol_list in symbols.items():
            for symbol in symbol_list:
                if symbol:  # 确保非空
                    self.index.add_symbol(symbol, {
                        "type": symbol_type.rstrip('s'),  # 去掉复数形式
                        "file": file_path,
                        "line": 1  # 简化处理
                    })