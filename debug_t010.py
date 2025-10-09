#!/usr/bin/env python3
"""
Debug T010 API response
"""

import sys
sys.path.insert(0, '.')

from src.core.mcp_tools import tool_apply_edit

# Read test file
with open('test_subdir/test_file.txt', 'r') as f:
    content = f.read()

old_content = content.strip()
new_content = content.strip() + "\n# Debug test"

result = tool_apply_edit('test_subdir/test_file.txt', old_content, new_content)
print(f"Result keys: {list(result.keys())}")
print(f"Result: {result}")