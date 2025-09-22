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
from typing import Optional, Callable, Dict, Any


def safe_file_operation(func: Callable) -> Callable:
    """
    文件操作错误处理装饰器 - 静默失败
    
    Linus原则: 不中断整体流程
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


def handle_mcp_errors(func: Callable) -> Callable:
    """
    MCP工具统一错误处理装饰器 - 标准化返回格式
    
    Linus原则: 消除重复的try/except模式
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        try:
            result = func(*args, **kwargs)
            # 确保所有成功响应包含success标志
            if isinstance(result, dict) and "success" not in result:
                result["success"] = True
            return result
        except Exception as e:
            # 统一错误响应格式
            return {
                "success": False, 
                "error": str(e),
                "function": func.__name__
            }
    return wrapper


def handle_edit_errors(func: Callable) -> Callable:
    """
    编辑操作统一错误处理装饰器 - 返回EditResult格式
    
    Linus原则: 专门化错误处理，避免重复代码
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            from .edit import EditResult
            return EditResult(False, [], str(e))
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

# Linus原则: Rust风格语言映射表 - 直接查表，零if/elif分支
LANGUAGE_MAP = {
    # Core programming languages
    '.py': 'python',
    '.pyw': 'python', 
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.mjs': 'javascript',
    '.cjs': 'javascript',
    '.java': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.zig': 'zig',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.v': 'vlang',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.dart': 'dart',
    '.lua': 'lua',
    '.pl': 'perl',
    '.sh': 'bash',
    '.ps1': 'powershell',
    '.r': 'r',
    '.jl': 'julia',
    '.m': 'objective-c',
    '.mm': 'objective-cpp',
    '.f90': 'fortran',
    '.f95': 'fortran',
    '.hs': 'haskell',
    '.ml': 'ocaml',
    '.fs': 'fsharp',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.erl': 'erlang',
    '.clj': 'clojure',
    '.lisp': 'lisp',
    '.scm': 'scheme',
}


def detect_language(file_path: str) -> str:
    """
    Rust风格语言检测 - 直接查表，零分支
    
    Linus原则: 消除if/elif链，用操作注册表
    """
    suffix = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(suffix, 'unknown')

class IndexBuilder:
    """极简索引构建器 - 零抽象层"""

    def __init__(self, index: CodeIndex):
        self.index = index
        # Linus原则: 统一语言处理架构 - 零特殊情况
        self._language_processors = {
            '.py': self._process_python_ast,
            '.v': self._process_vlang_regex,
            '.rs': self._process_rust_tree_sitter,
        }

    # Linus原则: 统一AST操作架构 - 零特殊情况
    _AST_OPERATIONS = {
        # Python AST节点 -> 统一处理器映射
        ast.FunctionDef: ('functions', lambda node: node.name),
        ast.ClassDef: ('classes', lambda node: node.name),
        ast.Import: ('imports', lambda node: [alias.name for alias in node.names]),
        ast.ImportFrom: ('imports', lambda node: [node.module] if node.module else [])
    }

    def _process_ast_node(self, node, symbols: Dict, imports: List) -> None:
        """统一AST节点处理 - Good Taste架构"""
        operation = self._AST_OPERATIONS.get(type(node))
        if not operation:
            return
            
        symbol_type, extractor = operation
        result = extractor(node)
        
        # Linus原则: 统一数据流处理
        self._add_extracted_data(symbol_type, result, symbols, imports)

    def _add_extracted_data(self, symbol_type: str, result, symbols: Dict, imports: List) -> None:
        """统一符号数据添加 - Linus原则: 消除所有特殊情况"""
        if symbol_type == 'imports':
            if isinstance(result, list):
                imports.extend(result)
            else:
                imports.append(result)
        else:
            if isinstance(result, list):
                symbols.setdefault(symbol_type, []).extend(result)
            else:
                symbols.setdefault(symbol_type, []).append(result)

    def build_index(self, root_path: str = None) -> None:
        """构建索引 - 直接扫描和解析"""
        if root_path:
            self.index.base_path = root_path

        for file_path in self._scan_files():
            self._index_file(file_path)

    def _scan_files(self) -> List[str]:
        """扫描支持的代码文件 - Rust风格，基于语言映射表"""
        files = []
        base = Path(self.index.base_path)

        if not base.exists():
            return files

        # Linus原则: 基于语言映射表动态生成文件模式 - 零硬编码
        supported_extensions = list(LANGUAGE_MAP.keys())
        
        # 扫描所有已知的文件扩展名
        for ext in supported_extensions:
            pattern = f"*{ext}"
            for file_path in base.rglob(pattern):
                # 跳过常见的非源码目录
                if not any(skip in str(file_path) for skip in ['.venv', '__pycache__', '.git', 'node_modules', 'target', 'build']):
                    files.append(str(file_path))
        return files

    def _index_file(self, file_path: str) -> None:
        """统一文件索引 - Linus原则: 消除特殊情况"""
        ext = get_file_extension(file_path)
        processor = self._language_processors.get(ext)
        if processor:
            processor(file_path)

    @safe_file_operation
    def _process_python_ast(self, file_path: str) -> None:
        """Python AST解析器 - Linus风格零分支 + 优化缓存"""
        from .cache import get_file_cache
        
        # 使用缓存获取文件内容 - 避免重复I/O
        lines = get_file_cache().get_file_lines(file_path)
        content = "\n".join(lines)

        tree = ast.parse(content, filename=file_path)
        symbols = {}
        imports = []

        # Linus原则: 操作注册表消除特殊情况
        for node in ast.walk(tree):
            self._process_ast_node(node, symbols, imports)

        file_info = FileInfo(
            language=detect_language(file_path),
            line_count=len(content.splitlines()),
            symbols=symbols,
            imports=imports
        )

        self.index.add_file(file_path, file_info)

        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    @safe_file_operation
    def _process_vlang_regex(self, file_path: str) -> None:
        """V语言正则表达式解析器 - 极简实现 + 优化缓存"""
        from .cache import get_file_cache
        
        # 使用缓存获取文件内容
        lines = get_file_cache().get_file_lines(file_path)
        content = "\n".join(lines)

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
            language=detect_language(file_path),
            line_count=len(content.splitlines()),
            symbols=symbols,
            imports=imports
        )

        self.index.add_file(file_path, file_info)

        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    @safe_file_operation
    def _process_rust_tree_sitter(self, file_path: str) -> None:
        """Rust tree-sitter解析器 - Linus式直接AST操作 + 优化缓存"""
        import tree_sitter_rust as ts_rust
        from tree_sitter import Language, Parser
        from .cache import get_file_cache

        RUST_LANGUAGE = Language(ts_rust.language())
        parser = Parser(RUST_LANGUAGE)

        # 使用缓存获取文件内容，但tree-sitter需要bytes
        lines = get_file_cache().get_file_lines(file_path)
        content = "\n".join(lines).encode('utf-8')

        tree = parser.parse(content)
        symbols = {}
        imports = []

        # Linus原则: 统一Rust AST操作架构 - 零特殊情况
        _RUST_OPERATIONS = {
            'function_item': ('functions', lambda n: self._extract_rust_name(n, content)),
            'struct_item': ('structs', lambda n: self._extract_rust_name(n, content)),
            'enum_item': ('enums', lambda n: self._extract_rust_name(n, content)),
            'trait_item': ('traits', lambda n: self._extract_rust_name(n, content)),
            'impl_item': ('impls', lambda n: self._extract_rust_impl(n, content)),
            'use_declaration': ('imports', lambda n: self._extract_rust_use(n, content))
        }

        def process_rust_node(node):
            """统一Rust AST处理 - Good Taste架构"""
            operation = _RUST_OPERATIONS.get(node.type)
            if not operation:
                return
                
            symbol_type, extractor = operation
            result = extractor(node)
            if not result:
                return
                
            # Linus原则: 统一数据流处理
            self._add_extracted_data(symbol_type, result, symbols, imports)

        def walk_tree(node):
            """Rust AST遍历 - 递归处理"""
            process_rust_node(node)
            for child in node.children:
                walk_tree(child)

        walk_tree(tree.root_node)

        file_info = FileInfo(
            language=detect_language(file_path),
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

    def _extract_rust_name(self, node, content: bytes) -> str:
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