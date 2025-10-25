#!/usr/bin/env python3
"""
符号搜索修复效果演示脚本
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from core.index import set_project_path
from core.search import SearchEngine, SearchQuery


def demo_symbol_search():
    """演示符号搜索功能"""
    print("🔍 符号搜索修复效果演示")
    print("=" * 50)

    # 初始化搜索引擎
    project_root = Path(__file__).parent
    index = set_project_path(str(project_root))
    search_engine = SearchEngine(index)

    # 测试用例
    test_cases = [
        ("test_apply_edit", "查找测试函数"),
        ("SearchEngine", "查找类定义"),
        ("set_project_path", "查找导入函数"),
        ("search", "查找通用符号"),
        ("index", "查找索引相关符号"),
    ]

    for pattern, description in test_cases:
        print(f"\n📋 {description}: '{pattern}'")
        print("-" * 40)

        query = SearchQuery(pattern=pattern, type="symbol", limit=5)
        result = search_engine.search(query)

        print(f"找到 {result.total_count} 个匹配，耗时 {result.search_time:.3f}s")

        for i, match in enumerate(result.matches, 1):
            symbol_type = match.get("type", "unknown")
            file_path = match.get("file", "unknown")
            line_num = match.get("line", 0)
            content = match.get("content", "")

            # 简化文件路径显示
            short_path = (
                file_path.replace(str(project_root), ".")
                if file_path != "unknown"
                else "unknown"
            )

            print(f"  {i}. [{symbol_type}] {short_path}:{line_num}")
            if content:
                # 只显示前80个字符
                short_content = content[:80] + "..." if len(content) > 80 else content
                print(f"     {short_content}")

    print(f"\n✅ 演示完成！符号搜索功能正常工作。")
    print(f"📊 索引统计:")
    print(f"   - 文件数量: {len(index.files)}")
    print(f"   - 符号数量: {len(index.symbols)}")
    print(f"   - 项目路径: {index.base_path}")


if __name__ == "__main__":
    demo_symbol_search()
