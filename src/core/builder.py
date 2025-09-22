"""
Linus-style index builder - 直接数据操作
"""

import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Callable
from .index import CodeIndex, FileInfo, SymbolInfo


from functools import wraps
from typing import Optional, Callable


def safe_file_operation(func: Callable) -> Callable:
    """
    统一错误处理装饰器 - 消除重复模式
    
    Linus原则: DRY (Don't Repeat Yourself)
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[bool]:
        try:
            func(*args, **kwargs)
            return True
        except Exception:
            # Linus原则: 静默失败，不中断整体流程
            return None
    return wrapper

def normalize_path(path: str, base_path: str = None) -> str:
    """
    统一路径处理 - 消除所有特殊情况
    
    Linus原则: 一个函数解决所有路径问题
    """
    path_obj = Path(path)
    
    if path_obj.is_absolute():
        return str(path_obj).replace('\\', '/')
    
    if base_path:
        return str(Path(base_path) / path).replace('\\', '/')
    
    return str(path_obj).replace('\\', '/')


def get_file_extension(file_path: str) -> str:
    """获取标准化文件扩展名"""
    return Path(file_path).suffix.lower()

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

    # Linus原则: AST操作注册表 - 消除所有if/elif分支
    def _process_ast_node(self, node, symbols: Dict, imports: List) -> None:
        """统一AST节点处理 - 零分支"""
        handler = self._get_ast_handler(type(node))
        if handler:
            handler(node, symbols, imports)

    def _get_ast_handler(self, node_type):
        """AST处理器注册表 - 直接查表"""
        return {
            ast.FunctionDef: self._extract_function,
            ast.ClassDef: self._extract_class,
            ast.Import: self._extract_import,
            ast.ImportFrom: self._extract_import_from
        }.get(node_type)

    def _extract_function(self, node, symbols: Dict, imports: List) -> None:
        """函数提取 - 专门化处理"""
        symbols.setdefault('functions', []).append(node.name)

    def _extract_class(self, node, symbols: Dict, imports: List) -> None:
        """类提取 - 专门化处理"""
        symbols.setdefault('classes', []).append(node.name)

    def _extract_import(self, node, symbols: Dict, imports: List) -> None:
        """导入提取 - 专门化处理"""
        for alias in node.names:
            imports.append(alias.name)

    def _extract_import_from(self, node, symbols: Dict, imports: List) -> None:
        """从导入提取 - 专门化处理"""
        if node.module:
            imports.append(node.module)

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
        ext = get_file_extension(file_path)
        if parser := self._parsers.get(ext):
            parser(file_path)

    @safe_file_operation
    def _parse_python(self, file_path: str) -> None:
        """Python AST解析器 - Linus风格零分支"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        symbols = {}
        imports = []

        # Linus原则: 操作注册表消除特殊情况
        for node in ast.walk(tree):
            self._process_ast_node(node, symbols, imports)

        file_info = FileInfo(
            language="python",
            line_count=len(content.splitlines()),
            symbols=symbols,
            imports=imports
        )

        self.index.add_file(file_path, file_info)

        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    @safe_file_operation
    def _parse_vlang(self, file_path: str) -> None:
        """V语言正则表达式解析器 - 极简实现"""
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

        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    @safe_file_operation
    def _parse_rust(self, file_path: str) -> None:
        """Rust tree-sitter解析器 - Linus式直接AST操作"""
        import tree_sitter_rust as ts_rust
        from tree_sitter import Language, Parser

        RUST_LANGUAGE = Language(ts_rust.language())
        parser = Parser(RUST_LANGUAGE)

        with open(file_path, 'rb') as f:
            content = f.read()

        tree = parser.parse(content)
        symbols = {}
        imports = []

        # Linus原则: Rust AST操作注册表 - 零分支
        rust_handlers = {
            'function_item': lambda n: self._extract_rust_name(n, content, 'functions'),
            'struct_item': lambda n: self._extract_rust_name(n, content, 'structs'),
            'enum_item': lambda n: self._extract_rust_name(n, content, 'enums'),
            'trait_item': lambda n: self._extract_rust_name(n, content, 'traits'),
            'impl_item': lambda n: self._extract_rust_impl(n, content),
            'use_declaration': lambda n: self._extract_rust_use(n, content)
        }

        def walk_tree(node):
            """统一Rust AST处理 - Good Taste实现"""
            handler = rust_handlers.get(node.type)
            if handler:
                result = handler(node)
                if result:
                    if node.type == 'use_declaration':
                        imports.append(result)
                    elif node.type == 'impl_item':
                        symbols.setdefault('impls', []).append(result)
                    else:
                        # 通用符号处理
                        symbol_type = {
                            'function_item': 'functions',
                            'struct_item': 'structs', 
                            'enum_item': 'enums',
                            'trait_item': 'traits'
                        }.get(node.type)
                        if symbol_type:
                            symbols.setdefault(symbol_type, []).append(result)

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

        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    def _register_symbols(self, symbols: Dict[str, List[str]], file_path: str) -> None:
        """将符号注册到全局索引 - Linus原则: 消除重复数据结构"""
        for symbol_type, symbol_list in symbols.items():
            for symbol_name in symbol_list:
                symbol_info = SymbolInfo(
                    type=symbol_type,
                    file=file_path,
                    line=1  # 简化版本，后续可以优化为真实行号
                )
                self.index.add_symbol(symbol_name, symbol_info)

    def _extract_rust_name(self, node, content: bytes, symbol_type: str = None) -> str:
        """提取Rust符号名称 - 统一接口"""
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