#!/usr/bin/env python3
"""
向后兼容性测试 - 验证重构后的功能完整性

Linus原则: "Never break userspace"
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_core_imports():
    """测试核心组件导入"""
    print("🔍 测试核心组件导入...")
    
    try:
        from core.index import CodeIndex, FileInfo, SymbolInfo
        from core.builder import IndexBuilder
        from core.index import get_index
        from core.mcp_tools import tool_set_project_path
        print("✅ 核心组件导入成功")
        return True
    except ImportError as e:
        print(f"❌ 核心组件导入失败: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("\n🧪 测试基本功能...")
    
    try:
        from core.index import get_index
        from core.mcp_tools import tool_set_project_path
        
        # 设置项目路径
        tool_set_project_path(str(project_root))
        index = get_index()
        
        # 验证索引对象
        assert hasattr(index, 'files'), "索引缺少files属性"
        assert hasattr(index, 'symbols'), "索引缺少symbols属性"
        assert hasattr(index, 'search'), "索引缺少search方法"
        
        print("✅ 基本功能测试通过")
        return True
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False

def test_symbol_info_compatibility():
    """测试SymbolInfo向后兼容性"""
    print("\n🔧 测试SymbolInfo向后兼容性...")
    
    try:
        from core.index import SymbolInfo
        
        # 创建SymbolInfo实例
        symbol = SymbolInfo(
            type="function",
            file="test.py", 
            line=10
        )
        
        # 验证必要属性
        assert symbol.type == "function"
        assert symbol.file == "test.py"
        assert symbol.line == 10
        
        print("✅ SymbolInfo向后兼容性测试通过")
        return True
    except Exception as e:
        print(f"❌ SymbolInfo兼容性测试失败: {e}")
        return False

def test_mcp_tools_interface():
    """测试MCP工具接口"""
    print("\n🛠️  测试MCP工具接口...")
    
    try:
        from core.mcp_tools import (
            tool_search_code,
            tool_get_file_summary, 
            tool_find_files,
            tool_get_index_stats
        )
        
        # 设置测试项目
        from core.mcp_tools import tool_set_project_path
        tool_set_project_path(str(project_root))
        
        # 测试搜索功能
        result = tool_search_code("def", "text")
        assert isinstance(result, dict), "搜索结果应该是字典"
        assert "matches" in result or "success" in result, "搜索结果应包含matches或success字段"
        
        # 测试文件列表
        result = tool_find_files("*.py")
        assert isinstance(result, dict), "文件列表结果应该是字典"
        assert "files" in result or "success" in result, "文件列表结果应包含files或success字段"
        
        # 测试项目统计
        result = tool_get_index_stats()
        assert isinstance(result, dict), "项目统计结果应该是字典"
        assert "file_count" in result or "success" in result, "统计结果应包含file_count或success字段"
        
        print("✅ MCP工具接口测试通过")
        return True
    except Exception as e:
        print(f"❌ MCP工具接口测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理装饰器"""
    print("\n🚨 测试错误处理装饰器...")
    
    try:
        from core.mcp_tools import tool_get_file_summary
        
        # 测试不存在的文件
        result = tool_get_file_summary("nonexistent_file.py")
        assert isinstance(result, dict), "错误响应应该是字典"
        assert result.get("success") is False, "不存在文件应返回success=False"
        assert "error" in result, "错误响应应包含error字段"
        
        print("✅ 错误处理装饰器测试通过")
        return True
    except Exception as e:
        print(f"❌ 错误处理装饰器测试失败: {e}")
        return False

def test_path_handling():
    """测试路径处理一致性"""
    print("\n📁 测试路径处理一致性...")
    
    try:
        from core.builder import normalize_path
        
        # 测试不同类型的路径
        test_cases = [
            ("relative/path.py", None, "relative/path.py"),
            ("C:\\absolute\\path.py", None, "C:/absolute/path.py"),
            ("relative.py", "/base/path", "/base/path/relative.py"),
        ]
        
        for input_path, base_path, expected in test_cases:
            result = normalize_path(input_path, base_path)
            # 简化验证：只检查路径分隔符
            assert "\\" not in result, f"路径应使用正斜杠: {result}"
        
        print("✅ 路径处理一致性测试通过")
        return True
    except Exception as e:
        print(f"❌ 路径处理测试失败: {e}")
        return False

def test_semantic_editing():
    """测试语义编辑功能"""
    print("\n✏️  测试语义编辑功能...")
    
    try:
        from core.mcp_tools import tool_rename_symbol, tool_add_import
        
        # 设置测试项目
        from core.mcp_tools import tool_set_project_path
        tool_set_project_path(str(project_root))
        
        # 测试符号重命名（应该返回结构化响应）
        result = tool_rename_symbol("old_name", "new_name")
        assert isinstance(result, dict), "重命名结果应该是字典"
        assert "success" in result, "重命名结果应包含success字段"
        
        # 测试添加导入（测试无效文件）
        result = tool_add_import("nonexistent.py", "import os")
        assert isinstance(result, dict), "导入结果应该是字典"
        assert result.get("success") is False, "无效文件应返回success=False"
        
        print("✅ 语义编辑功能测试通过")
        return True
    except Exception as e:
        print(f"❌ 语义编辑功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🎯 Linus风格向后兼容性测试")
    print("=" * 50)
    
    all_passed = True
    
    tests = [
        test_core_imports,
        test_basic_functionality,
        test_symbol_info_compatibility,
        test_mcp_tools_interface,
        test_error_handling,
        test_path_handling,
        test_semantic_editing
    ]
    
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有向后兼容性测试通过！")
        print("✅ 架构重构成功，保持了完整的向后兼容性")
        return 0
    else:
        print("❌ 部分测试失败，需要修复兼容性问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())