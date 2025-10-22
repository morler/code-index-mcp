#!/usr/bin/env python3
"""测试索引初始化和文件数量显示"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_index_initialization():
    """测试索引初始化"""
    try:
        print("=== 测试索引初始化 ===")

        # 导入模块
        from core.index import set_project_path

        print("✓ 成功导入 set_project_path")

        # 初始化索引
        print("正在初始化索引...")
        index = set_project_path(".")
        print("✓ 索引初始化完成")

        # 显示统计信息
        files_count = len(index.files)
        symbols_count = len(index.symbols)

        print(f"✓ 索引文件数量: {files_count}")
        print(f"✓ 索引符号数量: {symbols_count}")

        # 显示前几个文件
        if files_count > 0:
            print("\n前5个索引文件:")
            for i, file_path in enumerate(list(index.files.keys())[:5]):
                file_info = index.files[file_path]
                print(
                    f"  {i + 1}. {file_path} ({file_info.language}, {file_info.line_count} lines)"
                )

        return True

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_index_initialization()
    sys.exit(0 if success else 1)
