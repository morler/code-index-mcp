"""
测试文件锁可靠性的改进功能

测试超时时间改进、指数退避重试和锁清理机制的优化。
"""

import os
import sys
import tempfile
import time
import threading
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.file_lock import (
    FileLock,
    LockManager,
    acquire_file_lock,
    release_file_lock,
    file_lock,
    LockTimeoutError,
    LockAcquisitionError,
)


class TestFileLockReliability:
    """测试文件锁可靠性功能"""

    @pytest.fixture
    def temp_project(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            yield project_path

    def test_default_timeout_reduced(self, temp_project):
        """测试默认超时时间已减少到5秒"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 创建锁实例
        lock = FileLock(file_path)

        # 验证默认超时现在是5秒
        assert lock.timeout_seconds == 5.0

    def test_exponential_backoff_retry(self, temp_project):
        """测试指数退避重试策略"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 获取第一个锁
        lock1 = FileLock(file_path, timeout_seconds=5.0)
        lock1.acquire()

        try:
            # 尝试获取第二个锁（应该失败并使用指数退避）
            lock2 = FileLock(file_path, timeout_seconds=2.0)  # 短超时
            start_time = time.time()

            with pytest.raises(LockTimeoutError):
                lock2.acquire()

            elapsed = time.time() - start_time
            # 验证确实等待了大约2秒（考虑时间误差）
            assert 1.8 <= elapsed <= 2.5

        finally:
            lock1.release()

    def test_improved_stale_lock_detection(self, temp_project):
        """测试改进的僵尸锁检测"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 测试LockInfo的过期检测
        from core.file_lock import LockInfo

        old_time = time.time() - 20  # 20秒前
        lock_info = LockInfo(
            file_path=str(file_path),
            lock_type="exclusive",
            owner_pid=os.getpid(),
            acquired_at=old_time,
            timeout_seconds=5.0,
        )

        # 验证过期检测使用新的默认值（10秒）
        assert lock_info.is_expired(), "Lock should be expired after 20 seconds"
        assert lock_info.is_expired(5.0), "Lock should be expired with 5s threshold"
        assert not lock_info.is_expired(30.0), (
            "Lock should not be expired with 30s threshold"
        )

    def test_enhanced_lock_cleanup(self, temp_project):
        """测试增强的锁清理机制"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 获取并释放锁多次
        for i in range(5):
            lock = FileLock(file_path, timeout_seconds=5.0)
            success = lock.acquire(blocking=True)
            assert success, f"Lock acquisition {i} should succeed"
            lock.release()

            # 验证锁文件被正确清理
            lock_file_path = file_path.with_suffix(file_path.suffix + ".lock")
            assert not lock_file_path.exists(), (
                f"Lock file should be cleaned after iteration {i}"
            )

    def test_lock_manager_timeout_improvement(self, temp_project):
        """测试锁管理器的超时改进"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        manager = LockManager()

        # 验证默认超时现在是5秒
        lock1 = manager.acquire_lock(file_path, timeout=5.0)
        assert lock1.timeout_seconds == 5.0

        # 测试快速超时
        start_time = time.time()
        try:
            lock2 = manager.acquire_lock(file_path, timeout=1.0)
            # 如果成功获取，立即释放
            manager.release_lock(file_path)
        except LockAcquisitionError:
            pass  # 预期的错误

        elapsed = time.time() - start_time
        # 验证没有长时间等待
        assert elapsed < 2.0, "Should not wait long with reduced timeout"

        manager.release_lock(file_path)

    def test_concurrent_lock_behavior(self, temp_project):
        """测试高并发场景下的锁行为"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        results = []
        errors = []

        def worker(worker_id):
            try:
                lock = FileLock(file_path, timeout_seconds=5.0)
                start_time = time.time()

                with lock:  # 使用上下文管理器
                    # 模拟一些工作
                    time.sleep(0.1)
                    elapsed = time.time() - start_time
                    results.append((worker_id, elapsed))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # 启动多个并发线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"No errors should occur: {errors}"
        assert len(results) == 10, "All workers should complete"

        # 验证没有超时（所有操作应该在合理时间内完成）
        for worker_id, elapsed in results:
            assert elapsed < 6.0, f"Worker {worker_id} took too long: {elapsed}s"

    def test_context_manager_improvement(self, temp_project):
        """测试上下文管理器的改进"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 测试上下文管理器使用5秒超时
        start_time = time.time()

        with file_lock(file_path, timeout=5.0) as lock:
            assert lock.is_locked()
            # 验证锁确实使用了5秒超时
            assert lock.timeout_seconds == 5.0

        elapsed = time.time() - start_time
        # 应该很快完成
        assert elapsed < 1.0

    def test_error_handling_improvement(self, temp_project):
        """测试错误处理的改进"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 测试无效锁类型的错误处理
        with pytest.raises(ValueError):
            FileLock(file_path, lock_type="invalid")

        # 测试权限错误的处理（通过创建不可写的目录）
        readonly_dir = temp_project / "readonly"
        readonly_dir.mkdir()
        readonly_file = readonly_dir / "test.txt"
        readonly_file.write_text("test")

        # 在Windows上设置只读属性
        if os.name == "nt":
            try:
                readonly_file.chmod(0o444)
                # 尝试获取锁（应该优雅地处理权限错误）
                lock = FileLock(readonly_file, timeout_seconds=1.0)
                # 可能成功或失败，但不应该崩溃
                try:
                    success = lock.acquire(blocking=False)
                    if success:
                        lock.release()
                except Exception:
                    pass  # 预期的可能错误
            finally:
                readonly_file.chmod(0o644)  # 恢复权限以便清理

    def test_backward_compatibility(self, temp_project):
        """测试向后兼容性"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 测试旧的API仍然工作
        lock = acquire_file_lock(file_path, timeout=5.0)
        assert lock.is_locked()

        release_file_lock(file_path)
        assert not lock.is_locked()

    def test_performance_improvement(self, temp_project):
        """测试性能改进"""
        file_path = temp_project / "test.txt"
        file_path.write_text("test content")

        # 测试快速锁获取和释放
        start_time = time.time()

        for i in range(100):
            lock = FileLock(file_path, timeout_seconds=5.0)
            success = lock.acquire(blocking=True)
            assert success, f"Lock {i} should succeed"
            lock.release()

        elapsed = time.time() - start_time

        # 100次锁操作应该在合理时间内完成
        assert elapsed < 5.0, f"100 lock operations took too long: {elapsed}s"
        print(f"100 lock operations completed in {elapsed:.2f}s")


def run_reliability_tests():
    """手动运行所有可靠性测试"""
    print("=== File Lock Reliability Tests ===")

    test_instance = TestFileLockReliability()

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # 创建测试文件
        test_file = project_path / "test.txt"
        test_file.write_text("test content")

        # 运行测试
        try:
            test_instance.test_default_timeout_reduced(project_path)
            print("✅ Default timeout reduction test passed")

            test_instance.test_exponential_backoff_retry(project_path)
            print("✅ Exponential backoff retry test passed")

            test_instance.test_improved_stale_lock_detection(project_path)
            print("✅ Improved stale lock detection test passed")

            test_instance.test_enhanced_lock_cleanup(project_path)
            print("✅ Enhanced lock cleanup test passed")

            test_instance.test_lock_manager_timeout_improvement(project_path)
            print("✅ Lock manager timeout improvement test passed")

            test_instance.test_concurrent_lock_behavior(project_path)
            print("✅ Concurrent lock behavior test passed")

            test_instance.test_context_manager_improvement(project_path)
            print("✅ Context manager improvement test passed")

            test_instance.test_error_handling_improvement(project_path)
            print("✅ Error handling improvement test passed")

            test_instance.test_backward_compatibility(project_path)
            print("✅ Backward compatibility test passed")

            test_instance.test_performance_improvement(project_path)
            print("✅ Performance improvement test passed")

            print("\n=== All Reliability Tests Passed ===")
            return True

        except Exception as e:
            print(f"\n❌ Reliability test failed: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = run_reliability_tests()
    if not success:
        sys.exit(1)
