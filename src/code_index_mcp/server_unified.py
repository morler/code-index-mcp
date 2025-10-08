"""
Code Index MCP Server - Linus式极简实现

完全重写：30行代码替代118行+1600行tools
直接数据操作，零抽象层
"""

import logging
import sys
from typing import Any, Dict, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

from core.mcp_tools import execute_tool

# 极简服务器 - 只有工具注册
if FastMCP is not None:
    mcp = FastMCP("CodeIndexer", dependencies=["pathlib"])
    logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

    @mcp.tool()
    def unified_tool(operation: str, **params) -> Dict[str, Any]:
        """
        统一工具入口 - 消除所有特殊情况

        替代30+个专门工具函数
        """
        return execute_tool(operation, **params)


    # ----- 核心工具组 - 保留最常用的 -----


    @mcp.tool()
    def set_project_path(path: str) -> Dict[str, Any]:
        """项目初始化 - 必需工具"""
        return execute_tool("set_project_path", path=path)


    @mcp.tool()
    def search_code(pattern: str, search_type: str = "text") -> Dict[str, Any]:
        """统一搜索 - 合并所有搜索功能"""
        return execute_tool("search_code", pattern=pattern, search_type=search_type)


    @mcp.tool()
    def find_files(pattern: str) -> Dict[str, Any]:
        """文件查找 - 高频使用"""
        return execute_tool("find_files", pattern=pattern)


    # ----- 文件操作组 - 合并读取和编辑 -----


    @mcp.tool()
    def get_file_content(
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        show_line_numbers: bool = False,
    ) -> Dict[str, Any]:
        """获取文件内容 - 支持全文件和特定行范围，可选显示行号"""
        return execute_tool(
            "get_file_content",
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            show_line_numbers=show_line_numbers,
        )


    @mcp.tool()
    def get_symbol_body(
        symbol_name: str,
        file_path: Optional[str] = None,
        language: str = "auto",
        show_line_numbers: bool = False,
    ) -> Dict[str, Any]:
        """获取符号完整语法体 - 自动检测边界，支持多语言，可选显示行号"""
        return execute_tool(
            "get_symbol_body",
            symbol_name=symbol_name,
            file_path=file_path,
            language=language,
            show_line_numbers=show_line_numbers,
        )


    # ----- 语义编辑组 - 合并编辑操作 -----


    @mcp.tool()
    def rename_symbol(old_name: str, new_name: str) -> Dict[str, Any]:
        """重命名符号 - 跨文件安全重命名"""
        return execute_tool("rename_symbol", old_name=old_name, new_name=new_name)


    @mcp.tool()
    def add_import(file_path: str, import_statement: str) -> Dict[str, Any]:
        """添加导入语句 - 智能插入位置"""
        return execute_tool(
            "add_import", file_path=file_path, import_statement=import_statement
        )


    @mcp.tool()
    def apply_edit(file_path: str, old_content: str, new_content: str) -> Dict[str, Any]:
        """应用编辑操作 - 原子操作和备份"""
        return execute_tool(
            "apply_edit",
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
        )


    # 注意：其他17个工具通过unified_tool(operation, params)访问
    # 例如：unified_tool("find_references", '{"symbol_name": "function_name"}')


    def main():
        mcp.run()


# 向后兼容：当MCP不可用时提供空实现
else:
    def unified_tool(operation: str, **params) -> Dict[str, Any]:
        """统一工具入口 - 空实现"""
        return {"success": False, "error": "MCP not available"}

    def set_project_path(path: str) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def search_code(pattern: str, search_type: str = "text") -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def find_files(pattern: str) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def get_file_content(
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        show_line_numbers: bool = False,
    ) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def get_symbol_body(
        symbol_name: str,
        file_path: Optional[str] = None,
        language: str = "auto",
        show_line_numbers: bool = False,
    ) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def rename_symbol(old_name: str, new_name: str) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def add_import(file_path: str, import_statement: str) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def apply_edit(file_path: str, old_content: str, new_content: str) -> Dict[str, Any]:
        return {"success": False, "error": "MCP not available"}

    def main():
        print("MCP not available - server cannot start")


if __name__ == "__main__":
    main()