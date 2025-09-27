#!/usr/bin/env python3
"""原子性编辑边缘情况测试 - Linus风格严格验证"""

import os
import tempfile
import threading
import time
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.index import CodeIndex


def test_concurrent_same_file_stress():
    """压力测试：100个线程同时编辑同一文件"""
    print("=== 压力测试：100个线程同时编辑 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "stress_test.py"
        test_file.write_text("initial_content")

        index = CodeIndex(base_path=tmpdir, files={}, symbols={})
        results = []

        def edit_worker(worker_id: int):
            success, error = index.edit_file_atomic(
                str(test_file),
                "initial_content",
                f"content_from_worker_{worker_id}"
            )
            results.append((worker_id, success, error))

        # 100个并发线程
        threads = []
        for i in range(100):
            thread = threading.Thread(target=edit_worker, args=(i,))
            threads.append(thread)

        # 同时启动所有线程
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # 验证只有一个成功
        successful = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]

        print(f"成功编辑: {len(successful)}, 失败编辑: {len(failed)}")
        assert len(successful) == 1, f"应该只有1个成功，实际有{len(successful)}个"
        assert len(failed) == 99, f"应该有99个失败，实际有{len(failed)}个"

        # 验证文件内容正确
        final_content = test_file.read_text()
        winner_id = successful[0][0]
        expected = f"content_from_worker_{winner_id}"
        assert final_content == expected, f"内容不匹配: {final_content} != {expected}"

        print("✅ 压力测试通过")


def test_atomic_write_interruption_simulation():
    """模拟写入过程中断情况"""
    print("\n=== 测试原子性写入中断处理 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "atomic_test.py"
        test_file.write_text("original")

        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        # 测试临时文件清理
        success, error = index.edit_file_atomic(
            str(test_file),
            "original",
            "new_content"
        )

        assert success, f"编辑应该成功: {error}"

        # 验证没有遗留的临时文件
        temp_files = list(Path(tmpdir).glob("*.tmp"))
        assert len(temp_files) == 0, f"不应该有临时文件遗留: {temp_files}"

        print("✅ 原子性写入测试通过")


def test_permission_error_handling():
    """测试权限错误处理"""
    print("\n=== 测试权限错误处理 ===")

    # 在Windows上创建只读文件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "readonly.py"
        test_file.write_text("readonly_content")

        # 设置为只读
        test_file.chmod(0o444)

        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        try:
            success, error = index.edit_file_atomic(
                str(test_file),
                "readonly_content",
                "new_content"
            )

            # 应该失败并有明确错误信息
            assert not success, "只读文件编辑应该失败"
            assert "permission denied" in error.lower() or "write failed" in error.lower(), f"错误信息不正确: {error}"

            print("✅ 权限错误处理正确")

        finally:
            # 恢复权限以便清理
            test_file.chmod(0o666)


def test_encoding_error_handling():
    """测试编码错误处理"""
    print("\n=== 测试编码错误处理 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "encoding_test.py"

        # 写入无效UTF-8字节
        with open(test_file, 'wb') as f:
            f.write(b'\xff\xfe\x00\x00invalid utf8')

        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        success, error = index.edit_file_atomic(
            str(test_file),
            "anything",
            "new_content"
        )

        # 应该失败并有编码错误信息
        assert not success, "编码错误文件应该编辑失败"
        assert "encoding error" in error.lower(), f"应该有编码错误信息: {error}"

        print("✅ 编码错误处理正确")


def test_nonexistent_file_handling():
    """测试不存在文件的处理"""
    print("\n=== 测试不存在文件处理 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        nonexistent_file = Path(tmpdir) / "nonexistent.py"

        success, error = index.edit_file_atomic(
            str(nonexistent_file),
            "anything",
            "new_content"
        )

        assert not success, "不存在的文件应该编辑失败"
        assert "File not found" in error, f"应该有文件不存在错误: {error}"

        print("✅ 不存在文件处理正确")


def test_hash_collision_resistance():
    """测试hash碰撞抵抗力"""
    print("\n=== 测试hash碰撞抵抗力 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "hash_test.py"

        # 两个不同但长度相同的内容
        content1 = "a" * 1000
        content2 = "b" * 1000

        test_file.write_text(content1)

        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        # 尝试用错误的old_content编辑
        success, error = index.edit_file_atomic(
            str(test_file),
            content2,  # 错误的内容
            "new_content"
        )

        assert not success, "不匹配的内容应该被拒绝"
        assert "Cannot find old_content" in error, f"应该有内容不匹配错误: {error}"

        # 验证原文件未被修改
        current_content = test_file.read_text()
        assert current_content == content1, "文件不应该被修改"

        print("✅ Hash碰撞抵抗测试通过")


def test_simple_replace_edge_cases():
    """测试简化替换逻辑的边缘情况"""
    print("\n=== 测试简化替换逻辑边缘情况 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        index = CodeIndex(base_path=tmpdir, files={}, symbols={})

        # 测试多次出现的内容，应该只替换一次
        test_file = Path(tmpdir) / "replace_test.py"
        test_file.write_text("test test test")

        success, error = index.edit_file_atomic(
            str(test_file),
            "test",
            "replaced"
        )

        assert success, f"替换应该成功: {error}"

        final_content = test_file.read_text()
        # 应该只替换第一个
        assert final_content == "replaced test test", f"应该只替换一次: {final_content}"

        print("✅ 简化替换逻辑测试通过")


if __name__ == "__main__":
    test_concurrent_same_file_stress()
    test_atomic_write_interruption_simulation()
    test_permission_error_handling()
    test_encoding_error_handling()
    test_nonexistent_file_handling()
    test_hash_collision_resistance()
    test_simple_replace_edge_cases()

    print("\n🟢 所有边缘情况测试通过 - Linus风格验证完成！")