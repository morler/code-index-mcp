"""
Tool Registry - 工具注册表

从mcp_tools.py拆分，保持文件<200行原则
"""

from typing import Dict, Any, Callable


# 导入所有工具函数
def _import_tools():
    """延迟导入避免循环依赖"""
    from .mcp_tools import (
        tool_set_project_path,
        tool_search_code,
        tool_find_files,
        tool_get_file_summary,
        tool_get_index_stats,
        tool_semantic_search,
        tool_find_references,
        tool_find_definition,
        tool_find_callers,
        tool_find_implementations,
        tool_find_hierarchy,
        tool_organize_imports,
        tool_refresh_index,
        tool_check_file_exists,
    )

    return {
        "set_project_path": tool_set_project_path,
        "search_code": tool_search_code,
        "find_files": tool_find_files,
        "get_file_summary": tool_get_file_summary,
        "get_index_stats": tool_get_index_stats,
        "semantic_search": tool_semantic_search,
        "find_references": tool_find_references,
        "find_definition": tool_find_definition,
        "find_callers": tool_find_callers,
        "find_implementations": tool_find_implementations,
        "find_hierarchy": tool_find_hierarchy,
        "organize_imports": tool_organize_imports,
        "refresh_index": tool_refresh_index,
        "check_file_exists": tool_check_file_exists,
    }


def get_tool_registry() -> Dict[str, Callable]:
    """获取工具注册表 - 懒加载"""
    return _import_tools()


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    统一工具执行器 - 替代所有if/else分支

    单一入口点，消除特殊情况
    """
    tools = get_tool_registry()
    tool_func = tools.get(tool_name)

    if not tool_func:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    try:
        return tool_func(**kwargs)
    except Exception as e:
        return {"success": False, "error": f"Tool execution failed: {str(e)}"}