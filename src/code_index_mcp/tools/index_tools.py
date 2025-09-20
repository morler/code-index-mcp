"""
Index Tools - Project indexing and management functionality

This module contains all MCP tools related to project indexing, file discovery,
and index management operations.
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import Context
from mcp import mcp

from ..services.project_management_service import ProjectManagementService
from ..services.file_discovery_service import FileDiscoveryService
from ..services.index_management_service import IndexManagementService
from ..services.settings_service import SettingsService, manage_temp_directory
from ..services.system_management_service import SystemManagementService
from ..utils import handle_mcp_tool_errors


# ----- PROJECT MANAGEMENT TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def set_project_path(path: str, ctx: Context) -> str:
    """Set the base project path for indexing."""
    return ProjectManagementService(ctx).initialize_project(path)


# ----- FILE DISCOVERY TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='list')
def find_files(pattern: str, ctx: Context) -> List[str]:
    """
    Find files matching a glob pattern using pre-built file index.

    Use when:
    - Looking for files by pattern (e.g., "*.py", "test_*.js")
    - Searching by filename only (e.g., "README.md" finds all README files)
    - Checking if specific files exist in the project
    - Getting file lists for further analysis

    Pattern matching:
    - Supports both full path and filename-only matching
    - Uses standard glob patterns (*, ?, [])
    - Fast lookup using in-memory file index
    - Uses forward slashes consistently across all platforms

    Args:
        pattern: Glob pattern to match files (e.g., "*.py", "test_*.js", "README.md")

    Returns:
        List of file paths matching the pattern
    """
    return FileDiscoveryService(ctx).find_files(pattern)


# ----- INDEX MANAGEMENT TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def refresh_index(ctx: Context) -> str:
    """
    Manually refresh the project index when files have been added/removed/moved.

    Use when:
    - File watcher is disabled or unavailable
    - After large-scale operations (git checkout, merge, pull) that change many files
    - When you want immediate index rebuild without waiting for file watcher debounce
    - When find_files results seem incomplete or outdated
    - For troubleshooting suspected index synchronization issues

    Important notes for LLMs:
    - Always available as backup when file watcher is not working
    - Performs full project re-indexing for complete accuracy
    - Use when you suspect the index is stale after file system changes
    - **Call this after programmatic file modifications if file watcher seems unresponsive**
    - Complements the automatic file watcher system

    Returns:
        Success message with total file count
    """
    return IndexManagementService(ctx).rebuild_index()


# ----- SETTINGS MANAGEMENT TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def get_settings_info(ctx: Context) -> Dict[str, Any]:
    """Get information about the project settings."""
    return SettingsService(ctx).get_settings_info()


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def create_temp_directory() -> Dict[str, Any]:
    """Create the temporary directory used for storing index data."""
    return manage_temp_directory('create')


@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def check_temp_directory() -> Dict[str, Any]:
    """Check the temporary directory used for storing index data."""
    return manage_temp_directory('check')


@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def clear_settings(ctx: Context) -> str:
    """Clear all settings and cached data."""
    return SettingsService(ctx).clear_all_settings()


# ----- SYSTEM MANAGEMENT TOOLS -----

@mcp.tool()
@handle_mcp_tool_errors(return_type='dict')
def get_file_watcher_status(ctx: Context) -> Dict[str, Any]:
    """Get file watcher service status and statistics."""
    return SystemManagementService(ctx).get_file_watcher_status()


@mcp.tool()
@handle_mcp_tool_errors(return_type='str')
def configure_file_watcher(
    ctx: Context,
    enabled: Optional[bool] = None,
    debounce_seconds: Optional[float] = None,
    additional_exclude_patterns: Optional[List[str]] = None
) -> str:
    """Configure file watcher service settings."""
    return SystemManagementService(ctx).configure_file_watcher(
        enabled=enabled,
        debounce_seconds=debounce_seconds,
        additional_exclude_patterns=additional_exclude_patterns
    )