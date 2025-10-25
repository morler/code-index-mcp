"""
测试编辑内容验证的改进功能

测试空白字符处理、部分匹配和错误信息的改进。
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.edit_operations import (
    MemoryEditOperations,
    normalize_whitespace,
    find_content_match,
    validate_content_safely,
    calculate_line_position,
    MAX_CONTENT_SIZE,
)


class TestEditContentValidation:
    """测试编辑内容验证功能"""

    @pytest.fixture
    def temp_project(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # 创建测试文件
            files = {
                "test.py": "def hello():\n    return 'Hello World'\n",
                "mixed_whitespace.py": "def func():\n\treturn 'tab'\n    return 'space'\n",
                "multiline.py": "def multi():\n    line1\n    line2\n    line3\n",
            }

            for filename, content in files.items():
                (project_path / filename).write_text(content)

            yield project_path

    def test_normalize_whitespace(self):
        """测试空白字符标准化"""
        # 测试换行符标准化
        content_windows = "line1\r\nline2\r\nline3"
        expected = "line1\nline2\nline3"
        assert normalize_whitespace(content_windows) == expected

        # 测试制表符转换
        content_tabs = "line1\tline2\n\tline3"
        expected = "line1    line2\n    line3"
        assert normalize_whitespace(content_tabs) == expected

        # 测试行尾空白处理
        content_trailing = "line1   \nline2\t\nline3   \t"
        expected = "line1\nline2\nline3"
        assert normalize_whitespace(content_trailing) == expected

    def test_find_content_match_exact(self):
        """测试精确内容匹配"""
        content = "def hello():\n    return 'Hello World'\n"
        search = "def hello():"

        found, error, pos = find_content_match(content, search)
        assert found
        assert error is None
        assert pos == 0

    def test_find_content_match_whitespace_flexible(self):
        """测试灵活的空白字符匹配"""
        content = "def hello():\n    return 'Hello World'\n"
        search_tab = "def hello():\n\treturn 'Hello World'"
        search_space = "def hello():\n    return 'Hello World'"

        # 应该都能匹配
        found_tab, error_tab, pos_tab = find_content_match(content, search_tab)
        found_space, error_space, pos_space = find_content_match(content, search_space)

        assert found_tab
        assert error_tab is None
        assert found_space
        assert error_space is None

    def test_find_content_match_multiline(self):
        """测试多行内容匹配"""
        content = "def multi():\n    line1\n    line2\n    line3\n"
        search = "    line1\n    line2"

        found, error, pos = find_content_match(content, search)
        assert found
        assert error is None
        assert pos is not None

    def test_find_content_match_not_found(self):
        """测试内容未找到的情况"""
        content = "def hello():\n    return 'Hello World'\n"
        search = "def goodbye():"

        found, error, pos = find_content_match(content, search)
        assert not found
        assert error is not None
        assert "Content mismatch:" in error
        assert pos is None

    def test_edit_with_whitespace_tolerance(self, temp_project):
        """测试具有空白字符容忍度的编辑"""
        file_path = temp_project / "mixed_whitespace.py"
        old_content = "def func():\n\treturn 'tab'\n    return 'space'\n"
        new_content = "def func():\n    return 'space'\n"

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        assert success, f"Edit should succeed with whitespace tolerance: {error}"
        assert file_path.read_text() == new_content

    def test_edit_deletion_precision(self, temp_project):
        """测试删除操作的精确性"""
        file_path = temp_project / "multiline.py"
        old_content = "    line1\n    line2"
        new_content = ""  # 删除操作

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        if not success:
            print(f"Deletion failed with error: {repr(error)}")
            print(f"File content before: {repr(file_path.read_text())}")
            print(f"Old content: {repr(old_content)}")
            print(f"New content: {repr(new_content)}")
        assert success, f"Deletion should succeed: {error}"

        # 验证只有指定的行被删除
        result = file_path.read_text()
        assert "def multi():" in result
        assert "line3" in result
        assert "line1" not in result
        assert "line2" not in result

    def test_edit_replacement_precision(self, temp_project):
        """测试替换操作的精确性"""
        file_path = temp_project / "test.py"
        old_content = "return 'Hello World'"
        new_content = "return 'Hello Universe'"

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        assert success, f"Replacement should succeed: {error}"

        result = file_path.read_text()
        assert "Hello Universe" in result
        assert "Hello World" not in result
        assert "def hello():" in result  # 其他内容应该保持不变

    def test_edit_error_details(self, temp_project):
        """测试详细的错误信息"""
        file_path = temp_project / "test.py"
        wrong_content = "def wrong_function():"
        new_content = "def new_function():"

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(
            str(file_path), wrong_content, new_content
        )

        assert not success
        assert "Content validation failed" in error
        assert "Content mismatch:" in error
        assert "Expected:" in error
        assert "Actual:" in error

    def test_edit_empty_old_content(self, temp_project):
        """测试空旧内容的情况"""
        file_path = temp_project / "test_empty.py"
        file_path.write_text("def hello():\n    return 'Hello World'\n")
        new_content = "# New comment\n" + file_path.read_text()

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), "", new_content)

        assert success, f"Edit with empty old content should succeed: {error}"
        assert file_path.read_text() == new_content

    def test_edit_partial_line_match(self, temp_project):
        """测试部分行匹配"""
        file_path = temp_project / "test_partial.py"
        file_path.write_text("def hello():\n    return 'Hello World'\n")
        old_content = "return 'Hello World'"
        new_content = "return 'Hello World!'"  # 只是添加感叹号

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        assert success, f"Partial line match should succeed: {error}"
        result = file_path.read_text()
        assert "Hello World!" in result

    def test_edit_multiline_replacement(self, temp_project):
        """测试多行替换"""
        file_path = temp_project / "test_multiline.py"
        file_path.write_text("def multi():\n    line1\n    line2\n    line3\n")
        old_content = "    line1\n    line2"
        new_content = "    new_line1\n    new_line2"

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        assert success, f"Multiline replacement should succeed: {error}"
        result = file_path.read_text()
        assert "new_line1" in result
        assert "new_line2" in result
        assert "    line1\n" not in result  # 确保整行被替换
        assert "    line2\n" not in result  # 确保整行被替换
        assert "line3" in result  # 未被替换的行应该保持

    def test_validate_content_safely_large_file(self):
        """测试大文件的安全验证"""
        # 创建超过限制的内容
        large_content = "x" * (MAX_CONTENT_SIZE + 1)
        search_content = "test"

        is_safe, error = validate_content_safely(large_content, search_content)

        assert not is_safe
        assert "too large" in error

    def test_calculate_line_position(self):
        """测试行位置计算"""
        lines = ["line1", "line2", "line3"]

        # 第一行位置应该是0
        pos0 = calculate_line_position(lines, 0)
        assert pos0 == 0

        # 第二行位置应该是第一行长度 + 换行符
        pos1 = calculate_line_position(lines, 1)
        assert pos1 == len("line1") + 1

        # 第三行位置应该是前两行长度 + 两个换行符
        pos2 = calculate_line_position(lines, 2)
        assert pos2 == len("line1") + 1 + len("line2") + 1

    def test_unicode_content_handling(self, temp_project):
        """测试Unicode内容处理"""
        file_path = temp_project / "test_unicode.py"
        unicode_content = "def 测试函数():\n    返回 '测试内容'\n"
        file_path.write_text(unicode_content, encoding="utf-8")

        old_content = "返回 '测试内容'"
        new_content = "返回 '修改后的测试内容'"

        ops = MemoryEditOperations()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)

        assert success, f"Unicode edit should succeed: {error}"
        result = file_path.read_text(encoding="utf-8")
        assert "修改后的测试内容" in result

    def test_performance_with_large_content(self, temp_project):
        """测试大内容的性能"""
        import time

        file_path = temp_project / "test_performance.py"

        # 创建一个较大的文件（但不超过限制）
        lines = ["def func():"]
        for i in range(1000):
            lines.append(f"    line_{i}: return {i}")
        large_content = "\n".join(lines) + "\n"
        file_path.write_text(large_content)

        # 测试匹配性能
        old_content = "    line_500: return 500"
        new_content = "    line_500: return 999"

        ops = MemoryEditOperations()

        start_time = time.time()
        success, error = ops.edit_file_atomic(str(file_path), old_content, new_content)
        end_time = time.time()

        assert success, f"Large content edit should succeed: {error}"

        # 性能检查：应该在合理时间内完成（比如1秒）
        duration = end_time - start_time
        assert duration < 1.0, f"Edit took too long: {duration:.2f}s"

        result = file_path.read_text()
        assert "line_500: return 999" in result


def run_validation_tests():
    """手动运行所有验证测试"""
    print("=== Edit Content Validation Tests ===")

    test_instance = TestEditContentValidation()

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # 创建测试文件
        files = {
            "test.py": "def hello():\n    return 'Hello World'\n",
            "mixed_whitespace.py": "def func():\n\treturn 'tab'\n    return 'space'\n",
            "multiline.py": "def multi():\n    line1\n    line2\n    line3\n",
        }

        for filename, content in files.items():
            (project_path / filename).write_text(content)

        # 运行测试
        try:
            test_instance.test_normalize_whitespace()
            print("✅ Whitespace normalization test passed")

            test_instance.test_find_content_match_exact()
            print("✅ Exact content match test passed")

            test_instance.test_find_content_match_whitespace_flexible()
            print("✅ Whitespace flexible match test passed")

            test_instance.test_find_content_match_multiline()
            print("✅ Multiline content match test passed")

            test_instance.test_find_content_match_not_found()
            print("✅ Content not found test passed")

            test_instance.test_edit_with_whitespace_tolerance(project_path)
            print("✅ Whitespace tolerance edit test passed")

            test_instance.test_edit_deletion_precision(project_path)
            print("✅ Deletion precision test passed")

            test_instance.test_edit_replacement_precision(project_path)
            print("✅ Replacement precision test passed")

            test_instance.test_edit_error_details(project_path)
            print("✅ Error details test passed")

            test_instance.test_edit_empty_old_content(project_path)
            print("✅ Empty old content test passed")

            test_instance.test_edit_partial_line_match(project_path)
            print("✅ Partial line match test passed")

            test_instance.test_edit_multiline_replacement(project_path)
            print("✅ Multiline replacement test passed")

            test_instance.test_validate_content_safely_large_file()
            print("✅ Large file validation test passed")

            test_instance.test_calculate_line_position()
            print("✅ Line position calculation test passed")

            test_instance.test_unicode_content_handling(project_path)
            print("✅ Unicode content handling test passed")

            test_instance.test_performance_with_large_content(project_path)
            print("✅ Performance with large content test passed")

            print("\n=== All Validation Tests Passed ===")
            return True

        except Exception as e:
            print(f"\n❌ Validation test failed: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = run_validation_tests()
    if not success:
        sys.exit(1)
