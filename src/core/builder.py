"""
Linus-style index builder - 重构后的统一入口

原本1010行的单文件已重构为3个<200行的文件：
- builder_decorators.py: 装饰器和工具函数
- builder_languages.py: 语言检测和解析器管理
- builder_core.py: 核心IndexBuilder类

Linus原则: 消除大文件，统一接口，直接数据操作
"""

# 重新导出所有公共接口，保持向后兼容
from .builder_core import IndexBuilder
from .builder_decorators import (
    detect_language,
    get_file_extension,
    handle_edit_errors,
    handle_mcp_errors,
    normalize_path,
    safe_file_operation,
)
from .builder_languages import (
    get_parser,
    get_supported_tree_sitter_languages,
    get_tree_sitter_languages,
)

# 保持原有的LANGUAGE_MAP导出
from .builder_decorators import LANGUAGE_MAP

# 为了向后兼容，保持原有的导入路径可用
__all__ = [
    "IndexBuilder",
    "detect_language",
    "get_file_extension",
    "handle_edit_errors",
    "handle_mcp_errors",
    "normalize_path",
    "safe_file_operation",
    "get_parser",
    "get_supported_tree_sitter_languages",
    "get_tree_sitter_languages",
    "LANGUAGE_MAP",
]