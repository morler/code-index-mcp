"""
Builder语言检测和解析器管理 - Linus风格统一接口

包含所有tree-sitter语言支持、解析器管理和语言检测功能。
遵循Linus原则：延迟初始化，缓存优化，零特殊情况。
"""

from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    import tree_sitter


# Linus原则: Tree-sitter统一语言支持架构 - 零特殊情况
def _get_tree_sitter_languages():
    """延迟初始化Tree-sitter语言映射 - 避免导入时错误"""
    languages = {}

    # 动态导入可用的tree-sitter语言
    language_modules = [
        ("python", "tree_sitter_python"),
        ("javascript", "tree_sitter_javascript"),
        ("typescript", "tree_sitter_typescript"),
        ("java", "tree_sitter_java"),
        ("go", "tree_sitter_go"),
        ("zig", "tree_sitter_zig"),
        ("rust", "tree_sitter_rust"),
        ("c", "tree_sitter_c"),
        ("cpp", "tree_sitter_cpp"),
        ("odin", "tree_sitter_odin"),
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


def get_parser(language: str) -> Optional["tree_sitter.Parser"]:
    """
    获取语言解析器 - 统一接口

    Linus原则: 直接数据操作，无特殊情况
    """
    try:
        from tree_sitter import Language, Parser
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
        if language == "typescript":
            # TypeScript模块有两个函数：language_typescript 和 language_tsx
            if hasattr(parser_module, "language_typescript"):
                language_func = parser_module.language_typescript
            elif hasattr(parser_module, "language"):
                language_func = parser_module.language
        else:
            # 其他语言使用标准的language函数
            if hasattr(parser_module, "language"):
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