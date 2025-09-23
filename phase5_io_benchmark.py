#!/usr/bin/env python3
"""
Phase 5 I/O Performance Benchmark - Async File Operations Optimization

Linus风格I/O性能测试 - 验证异步文件操作和内存映射优化效果
"""

import sys
import time
import json
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from core.io_optimizer import (
        AsyncFileReader, OptimizedDirectoryScanner,
        read_file_optimized, read_file_lines_optimized,
        get_async_file_reader, get_directory_scanner
    )
    from core.index import CodeIndex
    from core.builder import IndexBuilder
    _OPTIMIZER_AVAILABLE = True
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class Phase5IOBenchmark:
    """Phase 5 I/O优化性能基准测试"""

    def __init__(self, test_project_path: str):
        self.test_path = Path(test_project_path)
        if not self.test_path.exists():
            raise ValueError(f"测试项目路径不存在: {test_project_path}")

        self.results = {}

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有Phase 5 I/O基准测试"""
        print("🚀 Phase 5 I/O Optimization Performance Benchmark")
        print("=" * 60)

        # 测试顺序: 文件读取 -> 目录扫描 -> 批量操作 -> 内存映射
        benchmarks = [
            ("file_read_performance", "文件读取性能对比"),
            ("directory_scan_performance", "目录扫描性能对比"),
            ("batch_file_operations", "批量文件操作性能"),
            ("memory_mapping_performance", "内存映射大文件性能"),
            ("async_vs_sync_comparison", "异步vs同步性能对比"),
        ]

        for method_name, description in benchmarks:
            print(f"\n📊 {description}...")
            start_time = time.time()
            try:
                result = getattr(self, method_name)()
                self.results[method_name] = result
                print(f"  ✅ 完成 ({time.time() - start_time:.3f}s)")
            except Exception as e:
                print(f"  ❌ 失败: {e}")
                self.results[method_name] = {"error": str(e)}

        self._print_summary()
        return self.results

    def file_read_performance(self) -> Dict[str, Any]:
        """文件读取性能对比测试"""
        # 找到一些测试文件
        test_files = []
        for ext in ['.py', '.js', '.ts', '.go', '.rs']:
            files = list(self.test_path.rglob(f'*{ext}'))[:5]  # 每种类型5个文件
            test_files.extend(files)

        if not test_files:
            return {"error": "没有找到测试文件"}

        results = {
            "total_files": len(test_files),
            "traditional_read_time": 0,
            "optimized_read_time": 0,
            "improvement_factor": 0
        }

        # 传统读取方式
        start_time = time.time()
        traditional_content = []
        for file_path in test_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                traditional_content.append(len(content))
            except Exception:
                continue
        results["traditional_read_time"] = time.time() - start_time

        # 优化读取方式
        start_time = time.time()
        optimized_content = []
        for file_path in test_files:
            try:
                content = read_file_optimized(file_path, encoding='utf-8')
                optimized_content.append(len(content))
            except Exception:
                continue
        results["optimized_read_time"] = time.time() - start_time

        # 计算改进倍数
        if results["optimized_read_time"] > 0:
            results["improvement_factor"] = results["traditional_read_time"] / results["optimized_read_time"]

        return results

    def directory_scan_performance(self) -> Dict[str, Any]:
        """目录扫描性能对比测试"""
        results = {
            "traditional_scan_time": 0,
            "optimized_scan_time": 0,
            "improvement_factor": 0,
            "files_found": 0
        }

        # 支持的扩展名
        supported_extensions = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.cpp', '.c', '.h'}
        skip_dirs = {'.venv', '__pycache__', '.git', 'node_modules', 'target', 'build'}

        # 传统扫描方式 (同步递归)
        def traditional_scan(base_path: Path) -> List[str]:
            files = []
            try:
                for item in base_path.rglob('*'):
                    if item.is_file() and item.suffix.lower() in supported_extensions:
                        # 检查是否在排除目录中
                        if not any(skip_dir in item.parts for skip_dir in skip_dirs):
                            files.append(str(item))
            except Exception:
                pass
            return files

        start_time = time.time()
        traditional_files = traditional_scan(self.test_path)
        results["traditional_scan_time"] = time.time() - start_time
        results["files_found"] = len(traditional_files)

        # 优化扫描方式 (异步并行)
        async def optimized_scan():
            scanner = get_directory_scanner()
            return await scanner.scan_directory_async(
                self.test_path, supported_extensions, skip_dirs
            )

        start_time = time.time()
        try:
            optimized_files = asyncio.run(optimized_scan())
            results["optimized_scan_time"] = time.time() - start_time

            # 计算改进倍数
            if results["optimized_scan_time"] > 0:
                results["improvement_factor"] = results["traditional_scan_time"] / results["optimized_scan_time"]
        except Exception as e:
            results["optimized_scan_error"] = str(e)

        return results

    def batch_file_operations(self) -> Dict[str, Any]:
        """批量文件操作性能测试"""
        # 获取测试文件列表
        test_files = list(self.test_path.rglob('*.py'))[:10]  # 取10个Python文件

        if len(test_files) < 3:
            return {"error": "测试文件数量不足"}

        results = {
            "file_count": len(test_files),
            "sequential_read_time": 0,
            "batch_read_time": 0,
            "improvement_factor": 0
        }

        # 顺序读取
        start_time = time.time()
        sequential_results = []
        for file_path in test_files:
            try:
                content = read_file_optimized(file_path)
                sequential_results.append(len(content))
            except Exception:
                continue
        results["sequential_read_time"] = time.time() - start_time

        # 批量异步读取
        async def batch_read():
            reader = get_async_file_reader()
            return await reader.batch_read_files(test_files)

        start_time = time.time()
        try:
            batch_results = asyncio.run(batch_read())
            results["batch_read_time"] = time.time() - start_time

            # 计算改进倍数
            if results["batch_read_time"] > 0:
                results["improvement_factor"] = results["sequential_read_time"] / results["batch_read_time"]
        except Exception as e:
            results["batch_read_error"] = str(e)

        return results

    def memory_mapping_performance(self) -> Dict[str, Any]:
        """内存映射大文件性能测试"""
        results = {
            "large_file_created": False,
            "traditional_read_time": 0,
            "mmap_read_time": 0,
            "improvement_factor": 0,
            "file_size_mb": 0
        }

        # 创建大文件用于测试 (5MB)
        test_content = "x" * 1024 * 1024 * 5  # 5MB的内容

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            large_file_path = Path(f.name)

        try:
            results["large_file_created"] = True
            results["file_size_mb"] = large_file_path.stat().st_size / (1024 * 1024)

            # 传统读取
            start_time = time.time()
            traditional_content = large_file_path.read_text(encoding='utf-8')
            results["traditional_read_time"] = time.time() - start_time

            # 优化读取 (会自动使用内存映射)
            start_time = time.time()
            optimized_content = read_file_optimized(large_file_path)
            results["mmap_read_time"] = time.time() - start_time

            # 验证内容一致性
            if len(traditional_content) == len(optimized_content):
                results["content_match"] = True

            # 计算改进倍数
            if results["mmap_read_time"] > 0:
                results["improvement_factor"] = results["traditional_read_time"] / results["mmap_read_time"]

        finally:
            # 清理测试文件
            try:
                large_file_path.unlink()
            except Exception:
                pass

        return results

    def async_vs_sync_comparison(self) -> Dict[str, Any]:
        """异步vs同步性能全面对比"""
        # 获取一组测试文件
        test_files = list(self.test_path.rglob('*.py'))[:20]

        if len(test_files) < 5:
            return {"error": "测试文件数量不足"}

        results = {
            "file_count": len(test_files),
            "sync_total_time": 0,
            "async_total_time": 0,
            "improvement_factor": 0
        }

        # 同步方式
        start_time = time.time()
        sync_contents = []
        for file_path in test_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                sync_contents.append(len(content))
            except Exception:
                continue
        results["sync_total_time"] = time.time() - start_time

        # 异步方式
        async def async_read_all():
            reader = get_async_file_reader()
            tasks = []
            for file_path in test_files:
                task = reader.read_file_async(file_path)
                tasks.append(task)

            contents = await asyncio.gather(*tasks, return_exceptions=True)
            return [len(c) for c in contents if isinstance(c, str)]

        start_time = time.time()
        try:
            async_contents = asyncio.run(async_read_all())
            results["async_total_time"] = time.time() - start_time

            # 计算改进倍数
            if results["async_total_time"] > 0:
                results["improvement_factor"] = results["sync_total_time"] / results["async_total_time"]
        except Exception as e:
            results["async_error"] = str(e)

        return results

    def _print_summary(self):
        """打印性能测试总结"""
        print("\n" + "=" * 60)
        print("📈 Phase 5 I/O Optimization Performance Report")
        print("=" * 60)

        print("\n🚀 核心I/O性能指标:")

        # 文件读取性能
        if "file_read_performance" in self.results:
            result = self.results["file_read_performance"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                status = "✅" if factor > 1.0 else "❌"
                print(f"   文件读取优化: {factor:.2f}x {status}")

        # 目录扫描性能
        if "directory_scan_performance" in self.results:
            result = self.results["directory_scan_performance"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                status = "✅" if factor > 1.0 else "❌"
                print(f"   目录扫描优化: {factor:.2f}x {status}")

        # 批量操作性能
        if "batch_file_operations" in self.results:
            result = self.results["batch_file_operations"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                status = "✅" if factor > 1.0 else "❌"
                print(f"   批量操作优化: {factor:.2f}x {status}")

        # 内存映射性能
        if "memory_mapping_performance" in self.results:
            result = self.results["memory_mapping_performance"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                status = "✅" if factor > 1.0 else "❌"
                print(f"   大文件读取优化: {factor:.2f}x {status}")

        # 异步vs同步
        if "async_vs_sync_comparison" in self.results:
            result = self.results["async_vs_sync_comparison"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                status = "✅" if factor > 1.0 else "❌"
                print(f"   异步并发优化: {factor:.2f}x {status}")

        # 保存详细报告
        report_file = "phase5_io_performance_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        print("\n🎯 Phase 5 Success Criteria Evaluation:")
        print("----------------------------------------")

        # 根据plans.md中的目标评估
        overall_success = True

        # 文件操作 < 0.1ms for cached files
        if "file_read_performance" in self.results:
            result = self.results["file_read_performance"]
            if "optimized_read_time" in result and "total_files" in result:
                avg_time_per_file = (result["optimized_read_time"] / result["total_files"]) * 1000
                if avg_time_per_file < 0.1:
                    print(f"   文件操作 < 0.1ms: ✅ 通过 ({avg_time_per_file:.3f}ms)")
                else:
                    print(f"   文件操作 < 0.1ms: ❌ 未达标 ({avg_time_per_file:.3f}ms)")
                    overall_success = False

        # 目录扫描 2x faster
        if "directory_scan_performance" in self.results:
            result = self.results["directory_scan_performance"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                if factor >= 2.0:
                    print(f"   目录扫描2x加速: ✅ 通过 ({factor:.2f}x)")
                else:
                    print(f"   目录扫描2x加速: ❌ 未达标 ({factor:.2f}x)")
                    overall_success = False

        # 无I/O阻塞
        if "async_vs_sync_comparison" in self.results:
            result = self.results["async_vs_sync_comparison"]
            if "improvement_factor" in result:
                factor = result["improvement_factor"]
                if factor > 1.0:
                    print(f"   异步非阻塞I/O: ✅ 通过 ({factor:.2f}x)")
                else:
                    print(f"   异步非阻塞I/O: ❌ 未达标 ({factor:.2f}x)")
                    overall_success = False

        if overall_success:
            print("\n✅ Phase 5 所有目标达成!")
        else:
            print("\n⚠️  Phase 5 部分目标未达成")

        print("\n✅ Phase 5 I/O优化基准测试完成!")


def main():
    """主函数"""
    import sys

    # 使用当前项目作为测试目标
    test_project = str(Path(__file__).parent)

    try:
        benchmark = Phase5IOBenchmark(test_project)
        benchmark.run_all_benchmarks()
    except Exception as e:
        print(f"❌ 基准测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()