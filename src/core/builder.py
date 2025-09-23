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
    
    Linus原则: 不中断整体流程，但保留返回值
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # Linus原则: 静默失败，不中断整体流程
            return False  # 默认返回False表示操作失败
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

# Linus原则: Tree-sitter统一语言支持架构 - 零特殊情况
def _get_tree_sitter_languages():
    """延迟初始化Tree-sitter语言映射 - 避免导入时错误"""
    languages = {}
    
    # 动态导入可用的tree-sitter语言
    language_modules = [
        ('python', 'tree_sitter_python'),
        ('javascript', 'tree_sitter_javascript'),
        ('typescript', 'tree_sitter_typescript'),
        ('java', 'tree_sitter_java'),
        ('go', 'tree_sitter_go'),
        ('zig', 'tree_sitter_zig'),
        ('rust', 'tree_sitter_rust'),
        ('c', 'tree_sitter_c'),
        ('cpp', 'tree_sitter_cpp'),
    ]
    
    for lang_name, module_name in language_modules:
        try:
            import importlib
            module = importlib.import_module(module_name)
            languages[lang_name] = module
        except ImportError:
            # 模块不可用时跳过
            pass
    
    return languages

# 全局缓存的语言映射
_CACHED_LANGUAGES = None

def get_tree_sitter_languages():
    """获取Tree-sitter语言映射 - 缓存优化"""
    global _CACHED_LANGUAGES
    if _CACHED_LANGUAGES is None:
        _CACHED_LANGUAGES = _get_tree_sitter_languages()
    return _CACHED_LANGUAGES


def get_parser(language: str) -> Optional['Parser']:
    """
    获取语言解析器 - 统一接口
    
    Linus原则: 直接数据操作，无特殊情况
    """
    try:
        from tree_sitter import Parser, Language
    except ImportError:
        return None
    
    # 获取语言模块
    tree_sitter_languages = get_tree_sitter_languages()
    parser_module = tree_sitter_languages.get(language)
    if not parser_module:
        return None
    
    try:
        # 处理语言特定的函数名
        language_func = None
        if language == 'typescript':
            # TypeScript模块有两个函数：language_typescript 和 language_tsx
            if hasattr(parser_module, 'language_typescript'):
                language_func = parser_module.language_typescript
            elif hasattr(parser_module, 'language'):
                language_func = parser_module.language
        else:
            # 其他语言使用标准的language函数
            if hasattr(parser_module, 'language'):
                language_func = parser_module.language
        
        if not language_func:
            return None
        
        language_capsule = language_func()
        language_obj = Language(language_capsule)
        parser = Parser(language_obj)
        return parser
    except Exception:
        # 语言包不可用时静默返回None
        return None


def get_supported_tree_sitter_languages() -> List[str]:
    """获取支持的tree-sitter语言列表"""
    tree_sitter_languages = get_tree_sitter_languages()
    supported = []
    for language in tree_sitter_languages.keys():
        if get_parser(language) is not None:
            supported.append(language)
    return supported

class IndexBuilder:
    """极简索引构建器 - 零抽象层"""

    def __init__(self, index: CodeIndex):
        self.index = index
        # Linus原则: 统一语言处理架构 - 零特殊情况
        self._language_processors = {
            '.py': self._process_python_ast,
            '.v': self._process_vlang_regex,
            '.rs': self._process_tree_sitter,
            '.js': self._process_tree_sitter,
            '.jsx': self._process_tree_sitter,
            '.ts': self._process_tree_sitter,
            '.tsx': self._process_tree_sitter,
            '.java': self._process_tree_sitter,
            '.go': self._process_tree_sitter,
            '.zig': self._process_tree_sitter,
            '.c': self._process_tree_sitter,
            '.h': self._process_tree_sitter,
            '.cpp': self._process_tree_sitter,
            '.hpp': self._process_tree_sitter,
            '.cc': self._process_tree_sitter,
            '.cxx': self._process_tree_sitter,
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

    def _scan_files_ultra_fast(self) -> List[str]:
        """Phase2优化: 超快速文件扫描 - os.scandir + 早期退出"""
        import os
        from concurrent.futures import ThreadPoolExecutor
        
        files = []
        base = Path(self.index.base_path)

        if not base.exists():
            return files

        # 支持的扩展名集合 - O(1)查找
        supported_extensions = set(LANGUAGE_MAP.keys())
        skip_dirs = {'.venv', '__pycache__', '.git', 'node_modules', 'target', 'build', '.pytest_cache'}
        
        def scan_directory(dir_path: str) -> List[str]:
            """使用os.scandir快速扫描单个目录"""
            local_files = []
            try:
                with os.scandir(dir_path) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            # 快速扩展名检查
                            name = entry.name
                            if '.' in name:
                                ext = '.' + name.split('.')[-1].lower()
                                if ext in supported_extensions:
                                    local_files.append(entry.path)
                        elif entry.is_dir(follow_symlinks=False):
                            # 跳过排除目录 + 早期退出
                            if entry.name not in skip_dirs:
                                local_files.extend(scan_directory(entry.path))
            except (OSError, PermissionError):
                # 访问受限目录时静默跳过
                pass
            return local_files
        
        # 对大项目使用并行扫描
        root_dirs = []
        try:
            with os.scandir(str(base)) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False) and entry.name not in skip_dirs:
                        root_dirs.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        name = entry.name
                        if '.' in name:
                            ext = '.' + name.split('.')[-1].lower()
                            if ext in supported_extensions:
                                files.append(entry.path)
        except (OSError, PermissionError):
            return files
        
        # 并行处理子目录 - 最多4个线程
        if len(root_dirs) > 2:
            with ThreadPoolExecutor(max_workers=min(4, len(root_dirs))) as executor:
                results = executor.map(scan_directory, root_dirs)
                for result in results:
                    files.extend(result)
        else:
            # 小项目直接顺序处理
            for dir_path in root_dirs:
                files.extend(scan_directory(dir_path))
        
        return files

    def _scan_files(self) -> List[str]:
        """向后兼容的文件扫描 - 使用超快速实现"""
        return self._scan_files_ultra_fast()

    def _index_file(self, file_path: str) -> None:
        """统一文件索引 - Linus原则: 消除特殊情况"""
        ext = get_file_extension(file_path)
        processor = self._language_processors.get(ext)
        if processor:
            processor(file_path)

    @safe_file_operation
    def _process_python_ast(self, file_path: str) -> None:
        """Python AST解析器 - Linus风格零分支 + 优化缓存"""
        # 使用缓存获取文件内容 - 避免重复I/O (如果可用)
        try:
            from .cache import get_file_cache
            lines = get_file_cache().get_file_lines(file_path)
            content = "\n".join(lines)
        except ImportError:
            # 缓存不可用时直接读取文件
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')

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
        # 使用缓存获取文件内容(如果可用)
        try:
            from .cache import get_file_cache
            lines = get_file_cache().get_file_lines(file_path)
            content = "\n".join(lines)
        except ImportError:
            # 缓存不可用时直接读取文件
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore')

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
        try:
            import tree_sitter_rust as ts_rust
            from tree_sitter import Language, Parser
        except ImportError:
            # tree-sitter不可用时跳过
            return

        RUST_LANGUAGE = Language(ts_rust.language())
        parser = Parser(RUST_LANGUAGE)

        # 使用缓存获取文件内容，但tree-sitter需要bytes
        try:
            from .cache import get_file_cache
            lines = get_file_cache().get_file_lines(file_path)
            content = "\n".join(lines).encode('utf-8')
        except ImportError:
            # 缓存不可用时直接读取文件
            content = Path(file_path).read_text(encoding='utf-8', errors='ignore').encode('utf-8')

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

    @safe_file_operation
    def _process_tree_sitter(self, file_path: str) -> None:
        """
        统一tree-sitter解析器 - Linus风格直接AST操作
        
        Linus原则: 一个函数处理所有tree-sitter语言，消除特殊情况
        """
        language = detect_language(file_path)
        parser = get_parser(language)
        
        if not parser:
            # 语言不支持tree-sitter时静默跳过
            return

        # 获取文件内容
        try:
            from .cache import get_file_cache
            lines = get_file_cache().get_file_lines(file_path)
            content = "\n".join(lines).encode('utf-8')
        except ImportError:
            # 缓存不可用时直接读取文件
            try:
                content = Path(file_path).read_text(encoding='utf-8', errors='ignore').encode('utf-8')
            except Exception:
                return

        # 解析AST
        try:
            tree = parser.parse(content)
        except Exception:
            return

        symbols = {}
        imports = []

        # Linus原则: 语言特定的AST操作映射 - 零if/elif分支
        language_operations = self._get_language_operations(language)
        
        def process_node(node):
            """统一AST节点处理 - Good Taste架构"""
            operation = language_operations.get(node.type)
            if not operation:
                return
                
            symbol_type, extractor = operation
            try:
                result = extractor(node, content)
                if result:
                    self._add_extracted_data(symbol_type, result, symbols, imports)
            except Exception:
                # 提取失败时继续处理其他节点
                pass

        def walk_tree(node):
            """AST遍历 - 递归处理"""
            process_node(node)
            for child in node.children:
                walk_tree(child)

        walk_tree(tree.root_node)

        file_info = FileInfo(
            language=language,
            line_count=len(content.decode('utf-8', errors='ignore').splitlines()),
            symbols=symbols,
            imports=imports
        )

        self.index.add_file(file_path, file_info)
        
        # Linus原则: 一次性完成所有相关操作 - 添加符号到全局索引
        self._register_symbols(symbols, file_path)

    def _get_language_operations(self, language: str) -> Dict[str, tuple]:
        """
        获取语言特定的AST操作映射
        
        Linus原则: 操作注册表模式，消除条件分支
        """
        # 通用节点名称映射 - 大多数C风格语言通用
        common_operations = {
            # 函数定义
            'function_declaration': ('functions', self._extract_tree_sitter_name),
            'function_definition': ('functions', self._extract_tree_sitter_name),
            'method_declaration': ('functions', self._extract_tree_sitter_name),
            'method_definition': ('functions', self._extract_tree_sitter_name),
            
            # 类/结构体定义
            'class_declaration': ('classes', self._extract_tree_sitter_name),
            'class_definition': ('classes', self._extract_tree_sitter_name),
            'struct_declaration': ('structs', self._extract_tree_sitter_name),
            'struct_definition': ('structs', self._extract_tree_sitter_name),
            
            # 接口/特质定义
            'interface_declaration': ('interfaces', self._extract_tree_sitter_name),
            'interface_definition': ('interfaces', self._extract_tree_sitter_name),
            'trait_declaration': ('traits', self._extract_tree_sitter_name),
            'trait_definition': ('traits', self._extract_tree_sitter_name),
            
            # 导入语句
            'import_declaration': ('imports', self._extract_tree_sitter_import),
            'import_statement': ('imports', self._extract_tree_sitter_import),
            'use_declaration': ('imports', self._extract_tree_sitter_import),
        }
        
        # 语言特定的扩展
        language_specific = {
            'rust': {
                'function_item': ('functions', self._extract_rust_name),
                'struct_item': ('structs', self._extract_rust_name),
                'enum_item': ('enums', self._extract_rust_name),
                'trait_item': ('traits', self._extract_rust_name),
                'impl_item': ('impls', self._extract_rust_impl),
                'use_declaration': ('imports', self._extract_rust_use),
            },
            'java': {
                'class_declaration': ('classes', self._extract_tree_sitter_name),
                'interface_declaration': ('interfaces', self._extract_tree_sitter_name),
                'method_declaration': ('functions', self._extract_tree_sitter_name),
                'import_declaration': ('imports', self._extract_tree_sitter_import),
            },
            'javascript': {
                'function_declaration': ('functions', self._extract_tree_sitter_name),
                'class_declaration': ('classes', self._extract_tree_sitter_name),
                'import_statement': ('imports', self._extract_tree_sitter_import),
                'export_statement': ('exports', self._extract_tree_sitter_name),
            },
            'typescript': {
                'function_declaration': ('functions', self._extract_tree_sitter_name),
                'class_declaration': ('classes', self._extract_tree_sitter_name),
                'interface_declaration': ('interfaces', self._extract_tree_sitter_name),
                'import_statement': ('imports', self._extract_tree_sitter_import),
                'export_statement': ('exports', self._extract_tree_sitter_name),
            },
            'c': {
                'function_definition': ('functions', self._extract_tree_sitter_name),
                'struct_specifier': ('structs', self._extract_tree_sitter_name),
                'preproc_include': ('imports', self._extract_tree_sitter_include),
            },
            'cpp': {
                'function_definition': ('functions', self._extract_tree_sitter_name),
                'class_specifier': ('classes', self._extract_tree_sitter_name),
                'struct_specifier': ('structs', self._extract_tree_sitter_name),
                'preproc_include': ('imports', self._extract_tree_sitter_include),
            },
            'go': {
                'function_declaration': ('functions', self._extract_tree_sitter_name),
                'type_declaration': ('types', self._extract_tree_sitter_name),
                'import_declaration': ('imports', self._extract_tree_sitter_import),
            },
            'zig': {
                'function_declaration': ('functions', self._extract_tree_sitter_name),
                'struct_declaration': ('structs', self._extract_tree_sitter_name),
            }
        }
        
        # 合并通用操作和语言特定操作
        operations = common_operations.copy()
        if language in language_specific:
            operations.update(language_specific[language])
        
        return operations

    def _extract_tree_sitter_name(self, node, content: bytes) -> Optional[str]:
        """从tree-sitter节点提取名称"""
        try:
            # 查找identifier子节点
            for child in node.children:
                if child.type == 'identifier':
                    start_byte = child.start_byte
                    end_byte = child.end_byte
                    name = content[start_byte:end_byte].decode('utf-8', errors='ignore')
                    return name.strip() if name else None
            return None
        except Exception:
            return None

    def _extract_tree_sitter_import(self, node, content: bytes) -> Optional[str]:
        """从tree-sitter节点提取导入信息"""
        try:
            # 提取导入语句的文本
            start_byte = node.start_byte
            end_byte = node.end_byte
            import_text = content[start_byte:end_byte].decode('utf-8', errors='ignore')
            return import_text.strip() if import_text else None
        except Exception:
            return None

    def _extract_tree_sitter_include(self, node, content: bytes) -> Optional[str]:
        """从tree-sitter节点提取C/C++包含信息"""
        try:
            # 查找string_literal或system_lib_string子节点
            for child in node.children:
                if child.type in ['string_literal', 'system_lib_string']:
                    start_byte = child.start_byte
                    end_byte = child.end_byte
                    include_path = content[start_byte:end_byte].decode('utf-8', errors='ignore')
                    return include_path.strip() if include_path else None
            return None
        except Exception:
            return None

    def _register_symbols(self, symbols: Dict[str, List[str]], file_path: str) -> None:
        """将符号注册到全局索引 - Linus原则: 消除重复数据结构"""
        language = detect_language(file_path)
        
        # 准备SCIP符号数据
        scip_symbols_data = []
        
        for symbol_type, symbol_list in symbols.items():
            for symbol_name in symbol_list:
                # 注册到传统索引
                symbol_info = SymbolInfo(
                    type=symbol_type,
                    file=file_path,
                    line=1  # 简化版本，后续可以优化为真实行号
                )
                self.index.add_symbol(symbol_name, symbol_info)
                
                # 准备SCIP数据
                scip_symbols_data.append({
                    "name": symbol_name,
                    "type": symbol_type,
                    "line": 1,
                    "column": 0,
                    "signature": None
                })
        
        # 自动填充SCIP数据 - Linus风格：一次性完成所有相关操作
        if self.index.scip_manager and scip_symbols_data:
            try:
                self.index.scip_manager.process_file_symbols(file_path, language, scip_symbols_data)
            except Exception:
                # SCIP处理失败时不影响主索引构建
                pass

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