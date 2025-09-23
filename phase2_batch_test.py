#!/usr/bin/env python3
"""
Phase2批量检测优化验证 - 专门测试批量检测性能改进

重点测试场景：
1. 小批量文件(避免线程开销)
2. 大批量文件(并行优势)
3. 有变更文件的场景(真实使用情况)
"""

import time
import os
import tempfile
import sys
from pathlib import Path
from typing import List

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.incremental import FileChangeTracker

class BatchTestSuite:
    """批量检测性能测试套件"""

    def create_test_files_with_changes(self, total_files: int, changed_ratio: float = 0.2) -> tuple:
        """创建测试文件，包含一定比例的变更文件"""
        temp_dir = tempfile.mkdtemp(prefix="batch_test_")
        files = []

        # 创建文件
        for i in range(total_files):
            file_path = os.path.join(temp_dir, f"test_{i}.py")
            content = f"# Test file {i}\ndef func_{i}():\n    pass\n"

            with open(file_path, 'w') as f:
                f.write(content)
            files.append(file_path)

        # 模拟文件跟踪
        tracker = FileChangeTracker()
        for file_path in files:
            tracker.update_file_tracking(file_path)

        # 修改部分文件
        changed_count = int(total_files * changed_ratio)
        changed_files = files[:changed_count]

        time.sleep(0.1)  # 确保mtime不同

        for file_path in changed_files:
            content = f"# Modified file\ndef modified_func():\n    return 'changed'\n"
            with open(file_path, 'w') as f:
                f.write(content)

        return files, changed_files, temp_dir, tracker

    def test_small_batch_performance(self):
        """测试小批量(100文件)性能 - 应该使用顺序处理"""
        print("🔬 小批量性能测试 (100文件, 20%变更)")

        files, changed_files, temp_dir, tracker = self.create_test_files_with_changes(100, 0.2)

        try:
            # 批量检测
            start_time = time.time()
            batch_result = tracker.batch_check_changes(files)
            batch_time = time.time() - start_time

            # 逐个检测
            start_time = time.time()
            individual_result = []
            for file_path in files:
                if tracker.is_file_changed(file_path):
                    individual_result.append(file_path)
            individual_time = time.time() - start_time

            # 结果验证
            batch_found = len(batch_result)
            individual_found = len(individual_result)
            expected_changes = len(changed_files)

            print(f"   • 批量检测: {batch_time:.3f}s, 发现变更: {batch_found}")
            print(f"   • 逐个检测: {individual_time:.3f}s, 发现变更: {individual_found}")
            print(f"   • 预期变更: {expected_changes}")

            if batch_time > 0:
                speedup = individual_time / batch_time
                print(f"   • 加速比: {speedup:.2f}x")
                return speedup

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        return 0

    def test_large_batch_performance(self):
        """测试大批量(500文件)性能 - 应该使用并行处理"""
        print("\n🚀 大批量性能测试 (500文件, 10%变更)")

        files, changed_files, temp_dir, tracker = self.create_test_files_with_changes(500, 0.1)

        try:
            # 批量检测
            start_time = time.time()
            batch_result = tracker.batch_check_changes(files)
            batch_time = time.time() - start_time

            # 逐个检测
            start_time = time.time()
            individual_result = []
            for file_path in files:
                if tracker.is_file_changed(file_path):
                    individual_result.append(file_path)
            individual_time = time.time() - start_time

            # 结果验证
            batch_found = len(batch_result)
            individual_found = len(individual_result)
            expected_changes = len(changed_files)

            print(f"   • 批量检测: {batch_time:.3f}s, 发现变更: {batch_found}")
            print(f"   • 逐个检测: {individual_time:.3f}s, 发现变更: {individual_found}")
            print(f"   • 预期变更: {expected_changes}")

            if batch_time > 0:
                speedup = individual_time / batch_time
                print(f"   • 加速比: {speedup:.2f}x")
                return speedup

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        return 0

    def test_no_changes_scenario(self):
        """测试无变更场景 - 应该快速跳过"""
        print("\n⚡ 无变更场景测试 (200文件, 0%变更)")

        files, _, temp_dir, tracker = self.create_test_files_with_changes(200, 0.0)

        try:
            # 批量检测
            start_time = time.time()
            batch_result = tracker.batch_check_changes(files)
            batch_time = time.time() - start_time

            # 逐个检测
            start_time = time.time()
            individual_result = []
            for file_path in files:
                if tracker.is_file_changed(file_path):
                    individual_result.append(file_path)
            individual_time = time.time() - start_time

            print(f"   • 批量检测: {batch_time:.3f}s, 发现变更: {len(batch_result)}")
            print(f"   • 逐个检测: {individual_time:.3f}s, 发现变更: {len(individual_result)}")

            if batch_time > 0:
                speedup = individual_time / batch_time
                print(f"   • 加速比: {speedup:.2f}x")
                return speedup

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        return 0

    def run_comprehensive_test(self):
        """运行综合批量检测性能测试"""
        print("🧪 Phase2批量检测优化验证")
        print("=" * 50)

        speedups = []

        # 测试小批量
        small_speedup = self.test_small_batch_performance()
        if small_speedup > 0:
            speedups.append(small_speedup)

        # 测试大批量
        large_speedup = self.test_large_batch_performance()
        if large_speedup > 0:
            speedups.append(large_speedup)

        # 测试无变更
        no_change_speedup = self.test_no_changes_scenario()
        if no_change_speedup > 0:
            speedups.append(no_change_speedup)

        # 汇总结果
        print("\n" + "=" * 50)
        print("📊 批量检测优化结果汇总")
        print("=" * 50)

        if speedups:
            avg_speedup = sum(speedups) / len(speedups)
            max_speedup = max(speedups)

            print(f"✅ 平均加速比: {avg_speedup:.2f}x")
            print(f"🚀 最大加速比: {max_speedup:.2f}x")

            if avg_speedup >= 2.0:
                print(f"🎉 目标达成! 批量检测平均加速 {avg_speedup:.1f}x >= 2.0x")
            elif avg_speedup >= 1.5:
                print(f"✅ 性能良好! 批量检测平均加速 {avg_speedup:.1f}x >= 1.5x")
            else:
                print(f"⚠️  需要优化: 批量检测平均加速 {avg_speedup:.1f}x < 1.5x")
        else:
            print("❌ 测试失败，无法获得有效的性能数据")

if __name__ == "__main__":
    test_suite = BatchTestSuite()
    test_suite.run_comprehensive_test()