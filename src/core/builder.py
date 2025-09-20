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
            '.rs': self._parse_rust,
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
        for pattern in ['*.py', '*.v', '*.rs']:
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

    def _parse_rust(self, file_path: str) -> None:
        """Rust tree-sitter解析器 - Linus式直接AST操作"""
        try:
            import tree_sitter_rust as ts_rust
            from tree_sitter import Language, Parser

            RUST_LANGUAGE = Language(ts_rust.language())
            parser = Parser(RUST_LANGUAGE)

            with open(file_path, 'rb') as f:
                content = f.read()

            tree = parser.parse(content)
            symbols = {}
            imports = []

            # 直接遍历AST - 零抽象层
            def walk_tree(node):
                if node.type == 'function_item':
                    func_name = self._extract_rust_name(node, content)
                    if func_name:
                        symbols.setdefault('functions', []).append(func_name)
                elif node.type == 'struct_item':
                    struct_name = self._extract_rust_name(node, content)
                    if struct_name:
                        symbols.setdefault('structs', []).append(struct_name)
                elif node.type == 'enum_item':
                    enum_name = self._extract_rust_name(node, content)
                    if enum_name:
                        symbols.setdefault('enums', []).append(enum_name)
                elif node.type == 'trait_item':
                    trait_name = self._extract_rust_name(node, content)
                    if trait_name:
                        symbols.setdefault('traits', []).append(trait_name)
                elif node.type == 'impl_item':
                    impl_name = self._extract_rust_impl(node, content)
                    if impl_name:
                        symbols.setdefault('impls', []).append(impl_name)
                elif node.type == 'use_declaration':
                    use_name = self._extract_rust_use(node, content)
                    if use_name:
                        imports.append(use_name)

                # 递归遍历子节点
                for child in node.children:
                    walk_tree(child)

            walk_tree(tree.root_node)

            file_info = FileInfo(
                language="rust",
                line_count=len(content.decode('utf-8', errors='ignore').splitlines()),
                symbols=symbols,
                imports=imports
            )

            self.index.add_file(file_path, file_info)

        except Exception:
            pass

    def _extract_rust_name(self, node, content: bytes) -> str:
        """提取Rust符号名称"""
        for child in node.children:
            if child.type == 'identifier':
                return content[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return ""

    def _extract_rust_impl(self, node, content: bytes) -> str:
        """提取impl块信息"""
        type_name = ""
        trait_name = ""

        for child in node.children:
            if child.type == 'type_identifier':
                type_name = content[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
            elif child.type == 'trait_bounds':
                # 处理 impl Trait for Type
                for subchild in child.children:
                    if subchild.type == 'type_identifier':
                        trait_name = content[subchild.start_byte:subchild.end_byte].decode('utf-8', errors='ignore')

        if trait_name and type_name:
            return f"{trait_name} for {type_name}"
        elif type_name:
            return type_name
        return ""

    def _extract_rust_use(self, node, content: bytes) -> str:
        """提取use声明"""
        for child in node.children:
            if child.type in ['use_list', 'scoped_identifier', 'identifier']:
                return content[child.start_byte:child.end_byte].decode('utf-8', errors='ignore')
        return ""