#!/usr/bin/env python3
"""测试智能编辑功能 - Linus风格验证"""

import tempfile
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.index import CodeIndex


def test_smart_content_replace():
    """测试智能内容替换功能"""

    # 创建测试索引
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index = CodeIndex(base_path=str(test_dir), files={}, symbols={})

        # 创建测试文件
        test_file = test_dir / "test.py"
        original_content = """def hello():
    print("Hello")
    return True

def world():
    print("World")
    return False
"""
        test_file.write_text(original_content)

        print("=== 测试1: 部分内容替换 ===")
        # 测试部分替换
        success, error = index.edit_file_atomic(
            str(test_file),
            'print("Hello")',
            'print("Hello, Linus!")'
        )

        if success:
            new_content = test_file.read_text()
            print("✅ 部分替换成功")
            print(f"新内容:\n{new_content}")
            assert 'print("Hello, Linus!")' in new_content
        else:
            print(f"❌ 部分替换失败: {error}")
            assert False, f"部分替换应该成功: {error}"

        print("\n=== 测试2: 行删除 ===")
        # 测试行删除
        success, error = index.edit_file_atomic(
            str(test_file),
            'return True',
            ''
        )

        if success:
            new_content = test_file.read_text()
            print("✅ 行删除成功")
            print(f"新内容:\n{new_content}")
            assert 'return True' not in new_content
        else:
            print(f"❌ 行删除失败: {error}")
            assert False, f"行删除应该成功: {error}"

        print("\n=== 测试3: 整个函数替换 ===")
        # 测试整个函数替换
        success, error = index.edit_file_atomic(
            str(test_file),
            """def world():
    print("World")
    return False""",
            """def world():
    print("Beautiful World!")
    return True"""
        )

        if success:
            new_content = test_file.read_text()
            print("✅ 函数替换成功")
            print(f"最终内容:\n{new_content}")
            assert 'print("Beautiful World!")' in new_content
            assert 'print("World")' not in new_content
        else:
            print(f"❌ 函数替换失败: {error}")
            assert False, f"函数替换应该成功: {error}"

        print("\n=== 测试4: 不匹配的内容 ===")
        # 测试不存在的内容
        success, error = index.edit_file_atomic(
            str(test_file),
            'nonexistent_content',
            'replacement'
        )

        if not success:
            print(f"✅ 正确拒绝不匹配的内容: {error}")
            assert 'Cannot find old_content' in error
        else:
            print("❌ 应该拒绝不匹配的内容")
            assert False, "应该拒绝不匹配的内容"


def test_edge_cases():
    """测试边缘情况"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        index = CodeIndex(base_path=str(test_dir), files={}, symbols={})

        # 创建测试文件
        test_file = test_dir / "edge_test.py"
        original_content = "# Comment\nprint('test')\n"
        test_file.write_text(original_content)

        print("\n=== 边缘测试1: 空old_content（追加） ===")
        success, error = index.edit_file_atomic(
            str(test_file),
            '',
            '\nprint("appended")'
        )

        if success:
            new_content = test_file.read_text()
            print("✅ 追加成功")
            print(f"内容:\n{new_content}")
            assert 'print("appended")' in new_content
        else:
            print(f"❌ 追加失败: {error}")

        print("\n=== 边缘测试2: 精确匹配整个文件 ===")
        current_content = test_file.read_text()
        success, error = index.edit_file_atomic(
            str(test_file),
            current_content,  # 精确匹配，不使用strip
            'completely_new_content'
        )

        if success:
            new_content = test_file.read_text()
            print("✅ 整个文件替换成功")
            print(f"内容:\n{new_content}")
            assert new_content == 'completely_new_content'
        else:
            print(f"❌ 整个文件替换失败: {error}")


if __name__ == "__main__":
    test_smart_content_replace()
    test_edge_cases()
    print("\n🟢 所有智能编辑测试通过 - Good Taste!")