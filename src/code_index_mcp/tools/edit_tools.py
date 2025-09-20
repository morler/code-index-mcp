"""
Edit Tools - Semantic code editing and refactoring functionality

This module contains all MCP tools related to semantic code editing,
refactoring, and code transformation operations.
"""

from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from mcp import mcp

from ..services.semantic_edit_service import SemanticEditService
from ..utils import handle_mcp_tool_errors


# ----- SEMANTIC EDITING TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def rename_symbol(
    ctx: Context,
    old_name: str,
    new_name: str,
    scope: str = "project"
) -> Dict[str, Any]:
    """
    Safely rename a symbol across the project.

    This tool performs a semantic rename operation that updates all references
    to a symbol while maintaining code correctness and consistency.

    Args:
        old_name: Current name of the symbol to rename
        new_name: New name for the symbol
        scope: Scope of rename operation (default: "project")

    Returns:
        Dictionary containing operation results, modified files, and rollback info
    """
    return SemanticEditService(ctx).rename_symbol(old_name, new_name, scope)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def add_import(
    ctx: Context,
    file_path: str,
    module_name: str,
    symbol_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Intelligently add an import statement to a file.

    This tool adds import statements in the appropriate location within the file,
    following Python import conventions and avoiding duplicates.

    Args:
        file_path: Path to the file where import should be added
        module_name: Name of the module to import
        symbol_name: Specific symbol to import (for 'from X import Y' style)

    Returns:
        Dictionary containing operation results and preview of changes
    """
    return SemanticEditService(ctx).add_import(file_path, module_name, symbol_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def remove_unused_imports(ctx: Context, file_path: str) -> Dict[str, Any]:
    """
    Remove unused import statements from a file.

    This tool analyzes a file to identify import statements that are not used
    and safely removes them to clean up the code.

    Args:
        file_path: Path to the file to clean up

    Returns:
        Dictionary containing operation results and list of removed imports
    """
    return SemanticEditService(ctx).remove_unused_imports(file_path)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def organize_imports(ctx: Context, file_path: str) -> Dict[str, Any]:
    """
    Organize and sort import statements in a file.

    This tool reorganizes imports by grouping them into standard library,
    third-party, and local imports, then sorts each group alphabetically.

    Args:
        file_path: Path to the file to organize

    Returns:
        Dictionary containing operation results and preview of changes
    """
    return SemanticEditService(ctx).organize_imports(file_path)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def rollback_edit_operation(ctx: Context, rollback_info: str) -> Dict[str, Any]:
    """
    Rollback a previous semantic editing operation.

    This tool restores files to their state before a semantic editing operation
    using the backup information from the original operation.

    Args:
        rollback_info: Backup directory path from a previous editing operation

    Returns:
        Dictionary containing rollback results and list of restored files
    """
    return SemanticEditService(ctx).rollback_operation(rollback_info)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def extract_function(
    ctx: Context,
    file_path: str,
    start_line: int,
    end_line: int,
    function_name: str,
    target_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract code into a new function.

    This tool extracts a block of code from a file and creates a new function,
    replacing the original code with a function call.

    Args:
        file_path: Path to the file containing the code to extract
        start_line: Starting line number of the code block
        end_line: Ending line number of the code block
        function_name: Name for the new function
        target_file: Optional file path where to place the new function (defaults to same file)

    Returns:
        Dictionary containing operation results and rollback info
    """
    return SemanticEditService(ctx).extract_function(file_path, start_line, end_line, function_name, target_file)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def extract_variable(
    ctx: Context,
    file_path: str,
    line_number: int,
    expression: str,
    variable_name: str
) -> Dict[str, Any]:
    """
    Extract an expression into a new variable.

    This tool extracts a complex expression and creates a new variable,
    replacing the original expression with the variable reference.

    Args:
        file_path: Path to the file containing the expression
        line_number: Line number where the expression is located
        expression: The expression to extract
        variable_name: Name for the new variable

    Returns:
        Dictionary containing operation results and rollback info
    """
    return SemanticEditService(ctx).extract_variable(file_path, line_number, expression, variable_name)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def inline_function(ctx: Context, function_name: str, scope: str = "project") -> Dict[str, Any]:
    """
    Inline a function by replacing all calls with the function body.

    This tool replaces all calls to a function with the actual function body,
    effectively removing the function definition and inlining its code.

    Args:
        function_name: Name of the function to inline
        scope: Scope of inlining operation (default: "project")

    Returns:
        Dictionary containing operation results and rollback info
    """
    return SemanticEditService(ctx).inline_function(function_name, scope)