#!/usr/bin/env python3
"""调试文件索引过程"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def debug_file_indexing():
    """调试文件索引过程"""
    try:
        print("=== 调试文件索引过程 ===")

        from pathlib import Path
        from core.builder_core import IndexBuilder
        from core.index import CodeIndex, FileInfo

        # 创建索引和构建器
        index = CodeIndex(base_path=".", files={}, symbols={})
        builder = IndexBuilder(index)

        print(f"索引前文件数量: {len(index.files)}")

        # 扫描文件
        files = builder._scan_files()
        print(f"扫描到文件数量: {len(files)}")

        # 手动索引前几个文件
        test_files = files[:5]
        print(f"\n测试索引前 {len(test_files)} 个文件:")

        for i, file_path in enumerate(test_files):
            print(f"\n{i + 1}. 索引文件: {file_path}")

            # 获取文件扩展名
            ext = Path(file_path).suffix.lower()
            print(f"   扩展名: {ext}")

            # 检查是否有处理器
            processor = builder._language_processors.get(ext)
            print(f"   处理器: {processor is not None}")

            if processor:
                try:
                    # 手动调用处理器
                    processor(file_path)
                    print(f"   ✓ 处理成功")
                except Exception as e:
                    print(f"   ✗ 处理失败: {e}")

        print(f"\n索引后文件数量: {len(index.files)}")
        print(f"索引后符号数量: {len(index.symbols)}")

        # 显示索引的文件
        if len(index.files) > 0:
            print("\n已索引的文件:")
            for file_path, file_info in list(index.files.items())[:5]:
                print(f"  - {file_path}: {file_info.language}")
        else:
            print("\n⚠️ 没有文件被添加到索引！")

        return len(index.files) > 0

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_file_indexing()
    sys.exit(0 if success else 1)
