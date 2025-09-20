"""
Utility modules for the Code Index MCP server.

This package contains shared utilities:
- error_handler: Decorator-based error handling for MCP entry points
- response_formatter: Response formatting utilities
- file utilities: File filtering and walking
"""

from .error_handler import handle_mcp_errors, handle_mcp_resource_errors, handle_mcp_tool_errors
from .response_formatter import ResponseFormatter
from .file_filter import FileFilter
from .file_walker import FileWalker, create_file_walker

__all__ = [
    'handle_mcp_errors',
    'handle_mcp_resource_errors',
    'handle_mcp_tool_errors',
    'ResponseFormatter',
    'FileFilter',
    'FileWalker',
    'create_file_walker'
]