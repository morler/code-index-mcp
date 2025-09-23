#!/usr/bin/env python3
"""
Phase2性能基准测试 - 验证超快速文件变更检测效果

Linus原则: 先测量，再优化，后验证
"""

import time
import os
import tempfile
from pathlib import Path
from typing import List, Dict
import sys
import tracemalloc

# 添加src路径以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.incremental import FileChangeTracker
from core.builder import IndexBuilder
from core.index import CodeIndex

class Phase2Benchmark:
    """Phase2性能基准测试套件"""

    def __init__(self, project_path: str = None):
        self.project_path = project_path or "."
        self.results = {}

    def create_test_files(self, count: int) -> List[str]:
        """创建测试文件集合"""
        temp_dir = tempfile.mkdtemp(prefix="phase2_test_")
        files = []

        # 创建不同大小的测试文件
        for i in range(count):
            file_path = os.path.join(temp_dir, f"test_{i}.py")

            # 混合小文件(<10KB)和大文件(>10KB)
            if i % 3 == 0:
                # 大文件 - 15KB+
                content = "# Large test file\n" + "def func():\n    pass\n" * 1000
            else:
                # 小文件 - <10KB
                content = "# Small test file\n" + "def func():\n    pass\n" * 50

            with open(file_path, 'w') as f:
                f.write(content)
            files.append(file_path)

        return files, temp_dir

    def benchmark_file_hashing(self, files: List[str]) -> Dict:
        """基准测试: 文件哈希计算速度"""
        tracker = FileChangeTracker()

        print(f"🧪 测试文件哈希性能 ({len(files)} 文件)")

        # 测试单文件哈希
        start_time = time.time()
        for file_path in files:
            tracker.get_file_hash(file_path)
        single_time = time.time() - start_time

        print(f"   • 单文件哈希: {single_time:.3f}s ({single_time/len(files)*1000:.2f}ms/文件)")

        return {
            'total_time': single_time,
            'per_file_ms': single_time/len(files)*1000,
            'files_per_second': len(files)/single_time
        }

    def benchmark_change_detection(self, files: List[str]) -> Dict:
        """基准测试: 变更检测速度"""
        tracker = FileChangeTracker()

        print(f"🔍 测试变更检测性能 ({len(files)} 文件)")

        # 初始化跟踪
        for file_path in files:
            tracker.update_file_tracking(file_path)

        # 测试批量变更检测
        start_time = time.time()
        changed = tracker.batch_check_changes(files)
        batch_time = time.time() - start_time

        print(f"   • 批量变更检测: {batch_time:.3f}s ({batch_time/len(files)*1000:.2f}ms/文件)")
        print(f"   • 检测到变更: {len(changed)} 文件")

        # 测试单个文件检测
        start_time = time.time()
        individual_changed = 0
        for file_path in files:
            if tracker.is_file_changed(file_path):
                individual_changed += 1
        individual_time = time.time() - start_time

        print(f"   • 逐个变更检测: {individual_time:.3f}s ({individual_time/len(files)*1000:.2f}ms/文件)")

        improvement = individual_time / batch_time if batch_time > 0 else 0
        print(f"   • 批量检测加速: {improvement:.1f}x")

        return {
            'batch_time': batch_time,
            'individual_time': individual_time,
            'improvement_ratio': improvement,
            'changed_files': len(changed)
        }

    def benchmark_directory_scan(self) -> Dict:
        """基准测试: 目录扫描速度"""
        index = CodeIndex(base_path=self.project_path, files={}, symbols={})
        builder = IndexBuilder(index)

        print(f"📁 测试目录扫描性能 ({self.project_path})")

        # 测试新的超快速扫描
        start_time = time.time()
        fast_files = builder._scan_files_ultra_fast()
        fast_time = time.time() - start_time

        print(f"   • 超快速扫描: {fast_time:.3f}s")
        print(f"   • 发现文件: {len(fast_files)} 个")
        print(f"   • 扫描速度: {len(fast_files)/fast_time:.0f} 文件/秒")

        return {
            'scan_time': fast_time,
            'files_found': len(fast_files),
            'files_per_second': len(fast_files)/fast_time if fast_time > 0 else 0
        }

    def memory_usage_test(self, files: List[str]) -> Dict:
        """内存使用测试"""
        print(f"💾 测试内存使用 ({len(files)} 文件)")

        # 开始内存跟踪
        tracemalloc.start()

        # 创建跟踪器并处理文件
        tracker = FileChangeTracker()
        for file_path in files:
            tracker.update_file_tracking(file_path)

        # 获取内存统计
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_used_mb = current / 1024 / 1024
        peak_memory_mb = peak / 1024 / 1024

        print(f"   • 当前内存: {memory_used_mb:.1f} MB")
        print(f"   • 峰值内存: {peak_memory_mb:.1f} MB")
        print(f"   • 每文件内存: {memory_used_mb/len(files)*1000:.2f} KB/文件")

        return {
            'memory_before_mb': 0,
            'memory_after_mb': memory_used_mb,
            'memory_used_mb': memory_used_mb,
            'memory_per_file_kb': memory_used_mb/len(files)*1000
        }

    def run_full_benchmark(self):
        """运行完整的Phase2基准测试"""
        print("🚀 Phase2超快速文件变更检测 - 性能基准测试")
        print("=" * 60)

        # 创建测试文件
        print("\n📝 创建测试文件...")
        test_files, temp_dir = self.create_test_files(1000)
        print(f"   • 创建了 {len(test_files)} 个测试文件")

        try:
            # 1. 文件哈希性能测试
            print("\n" + "=" * 60)
            hash_results = self.benchmark_file_hashing(test_files)

            # 2. 变更检测性能测试
            print("\n" + "=" * 60)
            change_results = self.benchmark_change_detection(test_files)

            # 3. 目录扫描性能测试
            print("\n" + "=" * 60)
            scan_results = self.benchmark_directory_scan()

            # 4. 内存使用测试
            print("\n" + "=" * 60)
            memory_results = self.memory_usage_test(test_files)

            # 汇总结果
            print("\n" + "=" * 60)
            print("📊 Phase2性能测试结果汇总")
            print("=" * 60)

            print("\n✅ 成功指标 (targets from plans.md):")

            # Phase2目标: 文件变更检测 < 1ms per file
            per_file_ms = hash_results['per_file_ms']
            target_ms = 1.0
            if per_file_ms < target_ms:
                print(f"   ✅ 文件变更检测: {per_file_ms:.2f}ms < {target_ms}ms (目标达成)")
            else:
                print(f"   ❌ 文件变更检测: {per_file_ms:.2f}ms > {target_ms}ms (未达目标)")

            # 批量处理加速比
            improvement = change_results['improvement_ratio']
            if improvement > 2:
                print(f"   ✅ 批量检测加速: {improvement:.1f}x > 2x (目标达成)")
            else:
                print(f"   ❌ 批量检测加速: {improvement:.1f}x < 2x (未达目标)")

            # 扫描性能
            scan_speed = scan_results['files_per_second']
            if scan_speed > 1000:
                print(f"   ✅ 目录扫描速度: {scan_speed:.0f} 文件/秒 > 1000 (良好)")
            else:
                print(f"   ⚠️  目录扫描速度: {scan_speed:.0f} 文件/秒 < 1000 (可接受)")

            # 内存效率
            memory_per_file = memory_results['memory_per_file_kb']
            if memory_per_file < 1.0:
                print(f"   ✅ 内存效率: {memory_per_file:.2f} KB/文件 < 1KB (高效)")
            else:
                print(f"   ⚠️  内存效率: {memory_per_file:.2f} KB/文件 > 1KB (一般)")

        finally:
            # 清理测试文件
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"\n🧹 清理测试文件: {temp_dir}")

if __name__ == "__main__":
    benchmark = Phase2Benchmark()
    benchmark.run_full_benchmark()