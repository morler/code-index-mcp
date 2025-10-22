#!/usr/bin/env python3
"""调试文件扫描问题"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def debug_file_scanning():
    """调试文件扫描过程"""
    try:
        print("=== 调试文件扫描 ===")

        from pathlib import Path
        from core.builder_core import IndexBuilder
        from core.index import CodeIndex

        # 创建索引和构建器
        index = CodeIndex(base_path=".", files={}, symbols={})
        builder = IndexBuilder(index)

        print(f"基础路径: {index.base_path}")
        print(f"路径存在: {Path(index.base_path).exists()}")

        # 检查语言处理器
        print(f"支持的语言扩展名: {list(builder._language_processors.keys())}")

        # 手动扫描文件
        print("\n开始扫描文件...")
        files = builder._scan_files()
        print(f"扫描到的文件数量: {len(files)}")

        if len(files) > 0:
            print("前10个文件:")
            for i, file_path in enumerate(files[:10]):
                print(f"  {i + 1}. {file_path}")
        else:
            print("没有扫描到任何文件！")

            # 手动检查目录
            print("\n手动检查目录内容:")
            base_path = Path(".")
            for root, dirs, filenames in os.walk(base_path):
                if len([f for f in filenames if f.endswith(".py")]) > 0:
                    py_files = [f for f in filenames if f.endswith(".py")]
                    print(f"目录 {root}: {len(py_files)} 个Python文件")
                    for f in py_files[:3]:  # 只显示前3个
                        full_path = Path(root) / f
                        print(f"  - {full_path}")

        return len(files) > 0

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_file_scanning()
    sys.exit(0 if success else 1)
