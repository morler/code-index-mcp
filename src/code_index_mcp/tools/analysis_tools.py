"""
Analysis Tools - Code analysis and intelligence functionality

This module contains all MCP tools related to code analysis, file inspection,
and code intelligence operations.
"""

from typing import Dict, Any
from mcp.server.fastmcp import Context
from mcp import mcp

from ..services.code_intelligence_service import CodeIntelligenceService
from ..services.semantic_edit_service import SemanticEditService
from ..utils import handle_mcp_tool_errors


# ----- CODE ANALYSIS TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def get_file_summary(file_path: str, ctx: Context) -> Dict[str, Any]:
    """
    Get a summary of a specific file, including:
    - Line count
    - Function/class definitions (for supported languages)
    - Import statements
    - Basic complexity metrics
    """
    return CodeIntelligenceService(ctx).analyze_file(file_path)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def detect_circular_dependencies(ctx: Context, scope: str = "project") -> Dict[str, Any]:
    """
    Detect circular dependencies in the project.

    This tool analyzes the project's dependency graph to identify circular dependencies
    that can cause issues in code organization and compilation.

    Args:
        scope: Scope of analysis (default: "project")

    Returns:
        Dictionary containing circular dependency results and analysis
    """
    return SemanticEditService(ctx).detect_circular_dependencies(scope)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def detect_unused_code(ctx: Context, scope: str = "project") -> Dict[str, Any]:
    """
    Detect potentially unused code in the project.

    This tool analyzes the project to find symbols (functions, classes, variables)
    that are defined but never referenced, helping to identify dead code.

    Args:
        scope: Scope of analysis (default: "project")

    Returns:
        Dictionary containing unused code analysis results
    """
    return SemanticEditService(ctx).detect_unused_code(scope)


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def analyze_impact_scope(ctx: Context, symbol_name: str) -> Dict[str, Any]:
    """
    Analyze the impact scope of changing or removing a symbol.

    This tool performs impact analysis to understand how changes to a specific symbol
    would affect the rest of the codebase, helping with safe refactoring decisions.

    Args:
        symbol_name: Name of the symbol to analyze

    Returns:
        Dictionary containing impact analysis results
    """
    return SemanticEditService(ctx).analyze_impact_scope(symbol_name)