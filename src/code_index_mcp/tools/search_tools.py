"""
Search Tools - Code search and discovery functionality

This module contains all MCP tools related to code search operations,
following Linus-style direct data manipulation principles.
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from mcp import mcp

from ..services import SearchService
from ..services.semantic_search_service import SemanticSearchService
from ..utils import handle_mcp_tool_errors


# ----- BASIC SEARCH TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def search_code_advanced(
    pattern: str,
    ctx: Context,
    case_sensitive: bool = True,
    context_lines: int = 0,
    file_pattern: Optional[str] = None,
    max_line_length: Optional[int] = None,
    fuzzy: bool = False,
    regex: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Search for a code pattern in the project using an advanced, fast tool.

    This tool automatically selects the best available command-line search tool
    (like ugrep, ripgrep, ag, or grep) for maximum performance.

    Args:
        pattern: The search pattern. Can be literal text or regex (see regex parameter).
        case_sensitive: Whether the search should be case-sensitive.
        context_lines: Number of lines to show before and after the match.
        file_pattern: A glob pattern to filter files to search in
                     (e.g., "*.py", "*.js", "test_*.py").
        max_line_length: Optional. Default None (no limit). Limits the length of lines when context_lines is used.
                     All search tools now handle glob patterns consistently:
                     - ugrep: Uses glob patterns (*.py, *.{js,ts})
                     - ripgrep: Uses glob patterns (*.py, *.{js,ts})
                     - ag (Silver Searcher): Automatically converts globs to regex patterns
                     - grep: Basic glob pattern matching
                     All common glob patterns like "*.py", "test_*.js", "src/*.ts" are supported.
        fuzzy: If True, enables fuzzy/partial matching behavior varies by search tool:
               - ugrep: Native fuzzy search with --fuzzy flag (true edit-distance fuzzy search)
               - ripgrep, ag, grep, basic: Word boundary pattern matching (not true fuzzy search)
               IMPORTANT: Only ugrep provides true fuzzy search. Other tools use word boundary
               matching which allows partial matches at word boundaries.
               For exact literal matches, set fuzzy=False (default and recommended).
        regex: Controls regex pattern matching behavior:
               - If True, enables regex pattern matching
               - If False, forces literal string search
               - If None (default), automatically detects regex patterns and enables regex for patterns like "ERROR|WARN"
               The pattern will always be validated for safety to prevent ReDoS attacks.

    Returns:
        A dictionary containing the search results or an error message.
    """
    return SearchService(ctx).search_code_advanced(
        pattern=pattern,
        case_sensitive=case_sensitive,
        context_lines=context_lines,
        file_pattern=file_pattern,
        max_line_length=max_line_length,
        fuzzy=fuzzy,
        regex=regex
    )


@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def refresh_search_tools(ctx: Context) -> str:
    """
    Manually re-detect the available command-line search tools on the system.
    This is useful if you have installed a new tool (like ripgrep) after starting the server.
    """
    return SearchService(ctx).refresh_search_tools()


# ----- SEMANTIC SEARCH TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def find_references(symbol_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Find all references to a symbol across the project.

    This tool searches for all locations where a symbol (function, class, variable)
    is referenced or called in the codebase.

    Args:
        symbol_name: Name of the symbol to find references for

    Returns:
        Dictionary containing reference locations and metadata
    """
    return SemanticSearchService(ctx).find_references(symbol_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def find_definition(symbol_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Find the definition of a symbol.

    This tool locates where a symbol (function, class, variable) is defined
    in the codebase.

    Args:
        symbol_name: Name of the symbol to find definition for

    Returns:
        Dictionary containing definition location and metadata
    """
    return SemanticSearchService(ctx).find_definition(symbol_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def find_callers(function_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Find all symbols that call a specific function.

    This tool identifies all locations in the codebase where a specific
    function or method is called.

    Args:
        function_name: Name of the function to find callers for

    Returns:
        Dictionary containing caller locations and metadata
    """
    return SemanticSearchService(ctx).find_callers(function_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def find_implementations(interface_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Find all implementations of an interface or base class.

    This tool searches for classes that implement a specific interface
    or extend a base class (primarily useful for TypeScript and Java).

    Args:
        interface_name: Name of the interface/base class

    Returns:
        Dictionary containing implementation locations and metadata
    """
    return SemanticSearchService(ctx).find_implementations(interface_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def find_symbol_hierarchy(class_name: str, ctx: Context) -> Dict[str, Any]:
    """
    Find the inheritance hierarchy of a class.

    This tool analyzes the inheritance relationships of a class,
    showing parent classes, child classes, and related symbols.

    Args:
        class_name: Name of the class to analyze

    Returns:
        Dictionary containing hierarchical structure
    """
    return SemanticSearchService(ctx).find_symbol_hierarchy(class_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def semantic_search(query: str, search_type: str, ctx: Context) -> Dict[str, Any]:
    """
    Unified semantic search interface.

    This tool provides a single entry point for various semantic search operations,
    automatically routing to the appropriate specialized search method.

    Args:
        query: The search query (symbol name, function name, etc.)
        search_type: Type of search - one of: references, definition, callers, implementations, hierarchy

    Returns:
        Dictionary containing search results
    """
    return SemanticSearchService(ctx).semantic_search(query, search_type)