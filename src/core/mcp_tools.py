"""
MCP Tools - Linus式统一工具实现

替代tools/目录下的所有Java风格抽象
直接操作数据，无包装器，无特殊情况
"""

from typing import Dict, Any, List, Optional
import time
import os
from pathlib import Path

from .index import get_index, set_project_path as core_set_project_path, SearchQuery

# 向后兼容 - 导出execute_tool
from .tool_registry import execute_tool


# ----- 核心工具 - 直接数据操作 -----

def tool_set_project_path(path: str) -> Dict[str, Any]:
    """设置项目路径 - 直接操作"""
    try:
        index = core_set_project_path(path)
        return {
            "success": True,
            "path": path,
            "files_indexed": len(index.files),
            "symbols_indexed": len(index.symbols)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_search_code(pattern: str, search_type: str = "text",
                    file_pattern: Optional[str] = None,
                    case_sensitive: bool = True) -> Dict[str, Any]:
    """统一搜索 - 消除特殊情况"""
    try:
        index = get_index()
        query = SearchQuery(
            pattern=pattern,
            type=search_type,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive
        )
        result = index.search(query)
        return {
            "success": True,
            "matches": result.matches,
            "total_count": result.total_count,
            "search_time": result.search_time,
            "query_type": search_type
        }
    except Exception as e:
        return {"success": False, "error": str(e), "matches": [], "total_count": 0}


def tool_find_files(pattern: str) -> Dict[str, Any]:
    """文件查找 - 直接操作"""
    try:
        index = get_index()
        files = index.find_files_by_pattern(pattern)
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        return {"success": False, "error": str(e), "files": []}


def tool_get_file_summary(file_path: str) -> Dict[str, Any]:
    """文件信息 - 直接访问"""
    try:
        index = get_index()
        file_info = index.get_file(file_path)
        if not file_info:
            return {"success": False, "error": f"File not found: {file_path}"}

        return {
            "success": True,
            "file_path": file_path,
            "language": file_info.language,
            "line_count": file_info.line_count,
            "symbol_count": sum(len(symbols) for symbols in file_info.symbols.values()),
            "imports": file_info.imports,
            "exports": file_info.exports
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_index_stats() -> Dict[str, Any]:
    """索引统计 - 直接数据"""
    try:
        index = get_index()
        stats = index.get_stats()
        return {"success": True, **stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- 语义搜索 - 数据驱动 -----

def tool_semantic_search(query: str, search_type: str) -> Dict[str, Any]:
    """统一语义搜索 - 替代所有专门函数"""
    return tool_search_code(query, search_type)


def tool_find_references(symbol_name: str) -> Dict[str, Any]:
    """查找引用 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "references")


def tool_find_definition(symbol_name: str) -> Dict[str, Any]:
    """查找定义 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "definition")


def tool_find_callers(function_name: str) -> Dict[str, Any]:
    """查找调用者 - 委托给统一接口"""
    return tool_semantic_search(function_name, "callers")


def tool_find_implementations(interface_name: str) -> Dict[str, Any]:
    """查找实现 - 委托给统一接口"""
    return tool_semantic_search(interface_name, "implementations")


def tool_find_hierarchy(symbol_name: str) -> Dict[str, Any]:
    """查找层次结构 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "hierarchy")


def tool_organize_imports(file_path: str) -> Dict[str, Any]:
    """整理导入 - 简单实现"""
    try:
        index = get_index()
        file_info = index.get_file(file_path)
        if not file_info:
            return {"success": False, "error": f"File not found: {file_path}"}

        # 简单的导入整理逻辑
        organized_imports = sorted(set(file_info.imports))
        return {
            "success": True,
            "original_count": len(file_info.imports),
            "organized_count": len(organized_imports),
            "organized_imports": organized_imports
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ----- 系统操作 - 最简实现 -----

def tool_refresh_index() -> Dict[str, Any]:
    """刷新索引 - 重建数据"""
    try:
        index = get_index()
        if not index.base_path:
            return {"success": False, "error": "No project path set"}

        # 简单重建 - 重新设置路径
        new_index = core_set_project_path(index.base_path)
        return {
            "success": True,
            "files_indexed": len(new_index.files),
            "symbols_indexed": len(new_index.symbols)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_check_file_exists(file_path: str) -> Dict[str, Any]:
    """文件存在检查 - 直接系统调用"""
    try:
        index = get_index()
        full_path = Path(index.base_path) / file_path
        exists = full_path.exists()
        return {
            "success": True,
            "exists": exists,
            "full_path": str(full_path),
            "in_index": file_path in index.files
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# 工具注册表已移至tool_registry.py以保持文件<200行原则