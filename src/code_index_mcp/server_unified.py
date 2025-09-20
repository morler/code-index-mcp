"""
Code Index MCP Server - Linus式极简实现

完全重写：30行代码替代118行+1600行tools
直接数据操作，零抽象层
"""

import sys
import logging
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from core.mcp_tools import execute_tool

# 极简服务器 - 只有工具注册
mcp = FastMCP("CodeIndexer", dependencies=["pathlib"])
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)


@mcp.tool()
def unified_tool(operation: str, **params) -> Dict[str, Any]:
    """
    统一工具入口 - 消除所有特殊情况

    替代30+个专门工具函数
    """
    return execute_tool(operation, **params)


# 向后兼容的具体工具 - 最小化数量
@mcp.tool()
def set_project_path(path: str) -> Dict[str, Any]:
    return execute_tool("set_project_path", path=path)


@mcp.tool()
def search_code(pattern: str, search_type: str = "text") -> Dict[str, Any]:
    return execute_tool("search_code", pattern=pattern, search_type=search_type)


@mcp.tool()
def find_files(pattern: str) -> Dict[str, Any]:
    return execute_tool("find_files", pattern=pattern)


def main():
    mcp.run()


if __name__ == '__main__':
    main()