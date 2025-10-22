#!/usr/bin/env python3
"""测试MCP工具的索引初始化"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_mcp_tool():
    """测试MCP工具的索引初始化"""
    try:
        print("=== 测试MCP工具索引初始化 ===")

        # 导入MCP工具
        from core.mcp_tools import tool_set_project_path

        # 调用工具
        result = tool_set_project_path(".")
        print(f"工具返回结果: {result}")

        if result.get("success"):
            print(f"✓ 文件数量: {result.get('files_indexed', 0)}")
            print(f"✓ 符号数量: {result.get('symbols_indexed', 0)}")
        else:
            print(f"✗ 错误: {result.get('error')}")

        return result.get("success", False)

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mcp_tool()
    sys.exit(0 if success else 1)
