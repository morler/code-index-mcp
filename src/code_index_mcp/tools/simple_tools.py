"""
Simple Tools - Direct CodeIndex integration

Minimal MCP tools using core/index.py directly.
No services, no abstractions, pure Linus-style data manipulation.
"""

from typing import Dict, Any, List
from mcp.server.fastmcp import Context
from mcp import mcp

from core.index import get_index, set_project_path as core_set_project_path, SearchQuery
from ..utils import handle_mcp_tool_errors


@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def set_project_path(path: str, ctx: Context) -> str:
    """Set the base project path for indexing."""
    try:
        index = core_set_project_path(path)
        ctx.base_path = path
        return f"Project path set to: {path}"
    except Exception as e:
        return f"Error setting project path: {str(e)}"


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def search_code(pattern: str, ctx: Context, search_type: str = "text") -> Dict[str, Any]:
    """Search for code patterns using the unified index."""
    try:
        index = get_index()
        query = SearchQuery(pattern=pattern, type=search_type)
        result = index.search(query)
        return {
            "matches": result.matches,
            "total_count": result.total_count,
            "search_time": result.search_time
        }
    except Exception as e:
        return {"error": str(e), "matches": [], "total_count": 0}


@mcp.tool()
@handle_mcp_tool_errors(return_type='list')
def find_files(pattern: str, ctx: Context) -> List[str]:
    """Find files matching a pattern using the index."""
    try:
        index = get_index()
        return index.find_files_by_pattern(pattern)
    except Exception as e:
        return []


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def get_file_summary(file_path: str, ctx: Context) -> Dict[str, Any]:
    """Get basic file information from the index."""
    try:
        index = get_index()
        file_info = index.get_file(file_path)
        if file_info:
            return {
                "file_path": file_path,
                "language": file_info.language,
                "line_count": file_info.line_count,
                "symbols": file_info.symbols,
                "imports": file_info.imports,
                "exports": file_info.exports
            }
        else:
            return {"error": f"File not found in index: {file_path}"}
    except Exception as e:
        return {"error": str(e)}