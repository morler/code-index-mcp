"""
工具整合测试 - 验证Linus式简化后的功能完整性
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestToolConsolidation:
    """测试工具整合后的功能"""

    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "test.py"
        self.test_file.write_text("""
def hello_world():
    print("Hello World")

class TestClass:
    def method(self):
        return "test"
""")

    def test_core_tools_available(self):
        """测试核心工具可用性"""
        from core.tool_registry import get_tool_registry

        tools = get_tool_registry()

        # 核心工具应该存在
        assert "set_project_path" in tools
        assert "search_code" in tools
        assert "find_files" in tools
        assert "get_file_content" in tools
        assert "get_symbol_body" in tools

        # 编辑工具
        assert "rename_symbol" in tools
        assert "add_import" in tools
        assert "apply_edit" in tools

    def test_unified_tool_access(self):
        """测试统一工具入口"""
        from core.tool_registry import execute_tool

        # 设置项目路径
        result = execute_tool("set_project_path", path=str(self.test_dir))
        assert result["success"] is True

        # 搜索代码
        result = execute_tool("search_code", pattern="hello", search_type="text")
        assert result["success"] is True

        # 查找文件
        result = execute_tool("find_files", pattern="*.py")
        assert result["success"] is True
        assert len(result["files"]) > 0

    def test_specific_tool_functions(self):
        """测试具体工具函数"""
        from core.mcp_tools import (
            tool_set_project_path,
            tool_search_code,
            tool_find_files,
            tool_get_file_content
        )

        # 设置项目
        result = tool_set_project_path(str(self.test_dir))
        assert result["success"] is True

        # 搜索
        result = tool_search_code("hello", "text")
        assert result["success"] is True

        # 查找文件
        result = tool_find_files("*.py")
        assert result["success"] is True

        # 读取文件
        result = tool_get_file_content(str(self.test_file))
        assert result["success"] is True
        assert "hello_world" in result["content"]

    def test_mcp_server_tools(self):
        """测试MCP服务器工具注册"""
        # 验证MCP服务器可以正常导入
        from code_index_mcp.server_unified import (
            unified_tool,
            set_project_path,
            search_code,
            find_files,
            get_file_content,
            get_symbol_body,
            rename_symbol,
            add_import,
            apply_edit
        )

        # 基本功能测试
        result = set_project_path(str(self.test_dir))
        assert result["success"] is True

        result = search_code("hello", "text")
        assert result["success"] is True

    def test_tool_count_reduction(self):
        """验证工具数量确实减少了"""
        from code_index_mcp.server_unified import mcp

        # 获取注册的工具数量
        tools = mcp._tools

        # 应该只有9个直接注册的工具 + 1个统一工具
        assert len(tools) == 9, f"Expected 9 tools, got {len(tools)}: {list(tools.keys())}"

        # 统一工具必须存在
        assert "unified_tool" in tools

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])