"""
Linus-style index builder - 直接数据操作
"""

import os
import ast
from pathlib import Path
from typing import Dict, List, Set
from .index import CodeIndex, FileInfo, SymbolInfo


class IndexBuilder:
    """极简索引构建器 - 零抽象层"""

    def __init__(self, index: CodeIndex):
        self.index = index

    def build_index(self, root_path: str = None) -> None:
        """构建索引 - 直接扫描和解析"""
        if root_path:
            self.index.base_path = root_path

        for file_path in self._scan_files():
            self._index_file(file_path)

    def _scan_files(self) -> List[str]:
        """扫描Python文件"""
        files = []
        base = Path(self.index.base_path)

        if not base.exists():
            return files

        for py_file in base.rglob("*.py"):
            if not any(skip in str(py_file) for skip in ['.venv', '__pycache__', '.git']):
                files.append(str(py_file))
        return files

    def _index_file(self, file_path: str) -> None:
        """索引单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析Python AST
            tree = ast.parse(content, filename=file_path)

            # 提取文件信息
            symbols = {}
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbols.setdefault('functions', []).append(node.name)
                elif isinstance(node, ast.ClassDef):
                    symbols.setdefault('classes', []).append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # 创建文件信息
            file_info = FileInfo(
                language="python",
                line_count=len(content.splitlines()),
                symbols=symbols,
                imports=imports
            )

            self.index.add_file(file_path, file_info)

        except Exception:
            # 忽略解析错误的文件
            pass