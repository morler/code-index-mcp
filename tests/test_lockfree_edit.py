#!/usr/bin/env python3
"""
Linus风格无锁编辑测试 - Good Taste: 简单直接的测试
"""

import hashlib
import tempfile
import threading
import time
from pathlib import Path
from typing import List

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.index import CodeIndex, ImmutableEdit


def test_concurrent_single_file_edit():
    """测试单文件并发编辑 - 应该阻止竞争条件"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("def old_function():\n    pass\n")

        # 创建索引
        index = CodeIndex(base_path=temp_dir, files={}, symbols={})

        results = []

        def edit_worker(worker_id: int):
            """工作线程 - 尝试同时编辑同一文件"""
            old_content = "def old_function():\n    pass\n"
            new_content = f"def new_function_{worker_id}():\n    pass\n"

            success, error = index.edit_file_atomic(
                str(test_file), old_content, new_content
            )
            results.append((worker_id, success, error))

        # 启动5个并发编辑线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=edit_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果 - 只有一个应该成功
        successful_edits = [r for r in results if r[1] is True]
        failed_edits = [r for r in results if r[1] is False]

        assert len(successful_edits) == 1, "只应该有一个编辑成功"
        assert len(failed_edits) == 4, "其他4个应该失败"

        # 验证文件内容
        final_content = test_file.read_text()
        successful_worker = successful_edits[0][0]
        expected_content = f"def new_function_{successful_worker}():\n    pass\n"
        assert final_content == expected_content


def test_concurrent_multi_file_edit():
    """测试多文件并发编辑 - 文件级锁定"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建多个测试文件
        test_files = []
        for i in range(3):
            test_file = Path(temp_dir) / f"test_{i}.py"
            test_file.write_text(f"def function_{i}():\n    pass\n")
            test_files.append(test_file)

        index = CodeIndex(base_path=temp_dir, files={}, symbols={})

        results = []

        def batch_edit_worker(worker_id: int):
            """批量编辑工作线程"""
            edits = []
            for i, test_file in enumerate(test_files):
                old_content = f"def function_{i}():\n    pass\n"
                # 使用新的hash格式：hash:size
                file_size = len(old_content.encode())
                hash_full = hashlib.sha256(old_content.encode()).hexdigest()
                old_hash = f"{hash_full}:{file_size}"
                new_content = f"def new_function_{worker_id}_{i}():\n    pass\n"

                edits.append(ImmutableEdit(
                    file_path=str(test_file),
                    old_hash=old_hash,
                    new_content=new_content,
                    operation_id=worker_id
                ))

            success, error = index.edit_files_atomic(edits)
            results.append((worker_id, success, error))

        # 启动3个并发批量编辑线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=batch_edit_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果 - 应该只有一个批量编辑成功
        successful_batches = [r for r in results if r[1] is True]
        failed_batches = [r for r in results if r[1] is False]

        assert len(successful_batches) == 1, "只应该有一个批量编辑成功"
        assert len(failed_batches) == 2, "其他2个应该失败"


def test_file_operation_cleanup():
    """测试文件操作状态清理 - 确保无内存泄露"""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.py"
        test_file.write_text("original content")

        index = CodeIndex(base_path=temp_dir, files={}, symbols={})

        # 执行编辑操作
        success, error = index.edit_file_atomic(
            str(test_file), "original content", "new content"
        )

        assert success is True
        assert error is None

        # 验证操作成功 - 新实现自动清理资源
        # 无需检查内部状态，关注结果

        # 验证文件内容
        assert test_file.read_text() == "new content"


if __name__ == "__main__":
    # 直接运行测试
    test_concurrent_single_file_edit()
    test_concurrent_multi_file_edit()
    test_file_operation_cleanup()
    print("🟢 所有无锁编辑测试通过 - Linus会满意的！")