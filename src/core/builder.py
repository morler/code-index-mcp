"""
Linus-style index builder - 直接数据操作
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set
from .index import CodeIndex, FileInfo, SymbolInfo


class IndexBuilder:
    """极简索引构建器 - 零抽象层"""

    def __init__(self, index: CodeIndex):
        self.index = index
        # Linus原则: 消除特殊情况 - 统一解析器注册表
        self._parsers = {
            '.py': self._parse_python,
            '.v': self._parse_vlang,
        }

    def build_index(self, root_path: str = None) -> None:
        """构建索引 - 直接扫描和解析"""
        if root_path:
            self.index.base_path = root_path

        for file_path in self._scan_files():
            self._index_file(file_path)

    def _scan_files(self) -> List[str]:
        """扫描支持的代码文件"""
        files = []
        base = Path(self.index.base_path)

        if not base.exists():
            return files

        # 扫描所有支持的文件类型
        for pattern in ['*.py', '*.v']:
            for file_path in base.rglob(pattern):
                if not any(skip in str(file_path) for skip in ['.venv', '__pycache__', '.git']):
                    files.append(str(file_path))
        return files

    def _index_file(self, file_path: str) -> None:
        """索引单个文件 - Linus原则: 消除特殊情况"""
        ext = Path(file_path).suffix
        if parser := self._parsers.get(ext):
            parser(file_path)

    def _parse_python(self, file_path: str) -> None:
        """Python AST解析器"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)
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

            file_info = FileInfo(
                language="python",
                line_count=len(content.splitlines()),
                symbols=symbols,
                imports=imports
            )

            self.index.add_file(file_path, file_info)

        except Exception:
            pass

    def _parse_vlang(self, file_path: str) -> None:
        """V语言正则表达式解析器 - 极简实现"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            symbols = {}
            imports = []

            # 提取函数: fn function_name 或 fn (receiver) method_name
            for match in re.finditer(r'fn\s+(?:\([^)]*\)\s+)?(\w+)', content):
                symbols.setdefault('functions', []).append(match.group(1))

            # 提取结构体: struct StructName
            for match in re.finditer(r'struct\s+(\w+)', content):
                symbols.setdefault('structs', []).append(match.group(1))

            # 提取接口: interface InterfaceName
            for match in re.finditer(r'interface\s+(\w+)', content):
                symbols.setdefault('interfaces', []).append(match.group(1))

            # 提取枚举: enum EnumName
            for match in re.finditer(r'enum\s+(\w+)', content):
                symbols.setdefault('enums', []).append(match.group(1))

            # 提取类型别名: type TypeName =
            for match in re.finditer(r'type\s+(\w+)\s*=', content):
                symbols.setdefault('types', []).append(match.group(1))

            # 提取导入: import module_name
            for match in re.finditer(r'import\s+(\w+(?:\.\w+)*)', content):
                imports.append(match.group(1))

            file_info = FileInfo(
                language="vlang",
                line_count=len(content.splitlines()),
                symbols=symbols,
                imports=imports
            )

            self.index.add_file(file_path, file_info)

        except Exception:
            pass