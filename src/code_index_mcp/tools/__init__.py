"""
Tools - Minimal MCP tool collection

Temporarily simplified for Phase 2 completion.
Only core tools that work with the new CodeIndex.
"""

# Import only basic working tools for now
from .simple_tools import *

__all__ = [
    'set_project_path',
    'search_code',
    'find_files',
    'get_file_summary'
]
