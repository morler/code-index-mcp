"""Linus-style MCP server."""
import sys
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator
from mcp.server.fastmcp import FastMCP
from core.index import CodeIndex
from .utils import handle_mcp_resource_errors

@dataclass
class CodeIndexerContext:
    base_path: str
    index: CodeIndex

@asynccontextmanager
async def indexer_lifespan(_server: FastMCP) -> AsyncIterator[CodeIndexerContext]:
    context = CodeIndexerContext(
        base_path="",
        index=CodeIndex(base_path="", files={}, symbols={})
    )
    try:
        yield context
    finally:
        pass

mcp = FastMCP("CodeIndexer", lifespan=indexer_lifespan, dependencies=["pathlib"])
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

@mcp.resource("config://code-indexer")
@handle_mcp_resource_errors
def get_config() -> str:
    return "Code Index MCP Server Configuration"

@mcp.resource("files://{file_path}")
@handle_mcp_resource_errors
def get_file_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@mcp.resource("structure://project")
@handle_mcp_resource_errors
def get_project_structure() -> str:
    ctx = mcp.get_context()
    if ctx.base_path:
        return f"Project: {ctx.base_path}"
    return "No project configured"


@mcp.tool()
@handle_mcp_resource_errors
def set_project_path(path: str) -> str:
    """Set the base project path for indexing."""
    try:
        from core.index import set_project_path as core_set_project_path
        index = core_set_project_path(path)
        ctx = mcp.get_context()
        ctx.base_path = path
        return f"Project path set to: {path}"
    except Exception as e:
        return f"Error setting project path: {str(e)}"

@mcp.tool()
@handle_mcp_resource_errors
def search_code(pattern: str, search_type: str = "text") -> dict:
    """Search for code patterns using the unified index."""
    try:
        from core.index import get_index, SearchQuery
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
@handle_mcp_resource_errors
def find_files(pattern: str) -> list:
    """Find files matching a pattern using the index."""
    try:
        from core.index import get_index
        index = get_index()
        return index.find_files_by_pattern(pattern)
    except Exception as e:
        return []

@mcp.tool()
@handle_mcp_resource_errors
def get_file_summary(file_path: str) -> dict:
    """Get basic file information from the index."""
    try:
        from core.index import get_index
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

def main():
    mcp.run()

if __name__ == '__main__':
    main()