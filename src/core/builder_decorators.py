"""
Builder装饰器和工具函数 - Linus风格直接数据操作

包含所有装饰器、路径处理和语言检测等工具函数。
遵循Linus原则：消除特殊情况，统一接口，<200行文件。
"""

from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, cast

if TYPE_CHECKING:
    import tree_sitter


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
            return cast(Dict[str, Any], result)
        except Exception as e:
            # 统一错误响应格式
            return {"success": False, "error": str(e), "function": func.__name__}

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


def normalize_path(path: str, base_path: Optional[str] = None) -> str:
    """
    统一路径处理 - 消除所有特殊情况

    Linus原则: 一个函数解决所有路径问题
    """
    path_obj = Path(path)

    if path_obj.is_absolute():
        return str(path_obj).replace("\\", "/")

    if base_path:
        return str(Path(base_path) / path).replace("\\", "/")

    return str(path_obj).replace("\\", "/")


def get_file_extension(file_path: str) -> str:
    """获取标准化文件扩展名"""
    return Path(file_path).suffix.lower()


# Linus原则: Rust风格语言映射表 - 直接查表，零if/elif分支
LANGUAGE_MAP = {
    # Core programming languages
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".zig": "zig",
    ".odin": "odin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".v": "vlang",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".dart": "dart",
    ".lua": "lua",
    ".pl": "perl",
    ".sh": "bash",
    ".ps1": "powershell",
    ".r": "r",
    ".jl": "julia",
    ".m": "objective-c",
    ".mm": "objective-cpp",
    ".f90": "fortran",
    ".f95": "fortran",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".fs": "fsharp",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".clj": "clojure",
    ".lisp": "lisp",
    ".scm": "scheme",
}


def detect_language(file_path: str) -> str:
    """
    Rust风格语言检测 - 直接查表，零分支

    Linus原则: 消除if/elif链，用操作注册表
    """
    suffix = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(suffix, "unknown")