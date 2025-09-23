#!/usr/bin/env python3
"""
Phase 4 Performance Benchmark - Advanced Caching Layer

Linus风格性能测试 - 验证10x+重复操作性能提升目标
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from core.index import CodeIndex, SearchQuery
    from core.builder import IndexBuilder
    from core.search import SearchEngine
    from core.cache import get_file_cache, clear_global_cache
    from core.tree_sitter_cache import get_tree_cache, clear_global_tree_cache
    from core.symbol_cache import get_symbol_cache, clear_global_symbol_cache
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class Phase4Benchmark:
    """Phase 4缓存层性能基准测试"""

    def __init__(self, test_project_path: str):
        self.test_path = Path(test_project_path)
        if not self.test_path.exists():
            raise ValueError(f"测试项目路径不存在: {test_project_path}")

        self.results = {}

    def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有Phase 4基准测试"""
        print("🚀 Phase 4 Advanced Caching Layer Performance Benchmark")
        print("=" * 60)

        # 测试顺序: 冷启动 -> 热启动 -> 重复操作
        benchmarks = [
            ("cold_start_indexing", "冷启动索引构建"),
            ("warm_start_indexing", "热启动索引构建"),
            ("query_result_caching", "查询结果缓存测试"),
            ("repeated_operations", "重复操作性能测试"),
            ("cache_statistics", "缓存统计分析")
        ]

        for test_name, description in benchmarks:
            print(f"\n📊 {description}...")
            try:
                result = getattr(self, test_name)()
                self.results[test_name] = result
                self._print_test_result(test_name, result)
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                self.results[test_name] = {"error": str(e)}

        # 生成性能报告
        self._generate_performance_report()
        return self.results

    def cold_start_indexing(self) -> Dict[str, Any]:
        """冷启动索引构建测试"""
        # 清空所有缓存
        clear_global_cache()
        clear_global_tree_cache()
        clear_global_symbol_cache()

        index = CodeIndex(str(self.test_path), {}, {})
        builder = IndexBuilder(index)

        start_time = time.time()
        builder.build_index()
        indexing_time = time.time() - start_time

        return {
            "indexing_time": round(indexing_time, 3),
            "files_indexed": len(index.files),
            "symbols_count": len(index.symbols)
        }

    def warm_start_indexing(self) -> Dict[str, Any]:
        """热启动索引构建测试 - 验证缓存效果"""
        # 保留现有缓存，重新构建索引
        index = CodeIndex(str(self.test_path), {}, {})
        builder = IndexBuilder(index)

        start_time = time.time()
        builder.build_index()
        indexing_time = time.time() - start_time

        cold_start_time = self.results.get("cold_start_indexing", {}).get("indexing_time", 1)
        improvement_ratio = cold_start_time / indexing_time if indexing_time > 0 else 0

        return {
            "indexing_time": round(indexing_time, 3),
            "files_indexed": len(index.files),
            "symbols_count": len(index.symbols),
            "improvement_ratio": round(improvement_ratio, 2)
        }

    def query_result_caching(self) -> Dict[str, Any]:
        """查询结果缓存性能测试"""
        index = CodeIndex(str(self.test_path), {}, {})
        builder = IndexBuilder(index)
        builder.build_index()

        search_engine = SearchEngine(index)

        # 测试查询集合
        test_queries = [
            SearchQuery("function", "text"),
            SearchQuery("class", "text"),
            SearchQuery("import", "text"),
            SearchQuery("def", "text"),
            SearchQuery("async", "text")
        ]

        # 第一轮查询 - 缓存未命中
        first_round_times = []
        for query in test_queries:
            start_time = time.time()
            result = search_engine.search(query)
            query_time = time.time() - start_time
            first_round_times.append(query_time)

        # 第二轮查询 - 缓存命中
        second_round_times = []
        for query in test_queries:
            start_time = time.time()
            result = search_engine.search(query)
            query_time = time.time() - start_time
            second_round_times.append(query_time)

        # 计算改进比例
        avg_first = sum(first_round_times) / len(first_round_times)
        avg_second = sum(second_round_times) / len(second_round_times)
        speedup_ratio = avg_first / avg_second if avg_second > 0 else 0

        # 获取缓存统计
        try:
            cache_stats = search_engine.get_cache_stats()
            hit_ratio = cache_stats.get("hit_ratio", 0)
        except:
            hit_ratio = 0

        return {
            "first_round_avg_ms": round(avg_first * 1000, 2),
            "second_round_avg_ms": round(avg_second * 1000, 2),
            "speedup_ratio": round(speedup_ratio, 2),
            "cache_hit_ratio": hit_ratio,
            "queries_tested": len(test_queries)
        }

    def repeated_operations(self) -> Dict[str, Any]:
        """重复操作性能测试 - 验证10x+提升目标"""
        index = CodeIndex(str(self.test_path), {}, {})
        builder = IndexBuilder(index)
        builder.build_index()

        search_engine = SearchEngine(index)

        # 测试重复查询性能
        query = SearchQuery("function", "text")

        # 10次重复查询
        repeat_times = []
        for i in range(10):
            start_time = time.time()
            result = search_engine.search(query)
            query_time = time.time() - start_time
            repeat_times.append(query_time)

        first_query_time = repeat_times[0]
        subsequent_avg = sum(repeat_times[1:]) / len(repeat_times[1:]) if len(repeat_times) > 1 else first_query_time
        improvement_ratio = first_query_time / subsequent_avg if subsequent_avg > 0 else 0

        return {
            "first_query_ms": round(first_query_time * 1000, 2),
            "subsequent_avg_ms": round(subsequent_avg * 1000, 2),
            "improvement_ratio": round(improvement_ratio, 2),
            "target_achieved": improvement_ratio >= 10.0,  # Phase 4目标: 10x+提升
            "total_queries": len(repeat_times)
        }

    def cache_statistics(self) -> Dict[str, Any]:
        """缓存统计分析"""
        file_cache_stats = get_file_cache().get_cache_stats()
        tree_cache_stats = get_tree_cache().get_cache_stats()
        symbol_cache_stats = get_symbol_cache().get_cache_stats()

        return {
            "file_cache": file_cache_stats,
            "tree_cache": tree_cache_stats,
            "symbol_cache": symbol_cache_stats
        }

    def _print_test_result(self, test_name: str, result: Dict[str, Any]):
        """打印测试结果"""
        if "error" in result:
            print(f"  ❌ 错误: {result['error']}")
            return

        print(f"  ✅ 完成")

        # 根据测试类型显示关键指标
        if test_name == "cold_start_indexing":
            print(f"     索引时间: {result['indexing_time']}s")
            print(f"     文件数量: {result['files_indexed']}")

        elif test_name == "warm_start_indexing":
            print(f"     索引时间: {result['indexing_time']}s")
            print(f"     性能提升: {result['improvement_ratio']}x")

        elif test_name == "query_result_caching":
            print(f"     缓存前: {result['first_round_avg_ms']}ms")
            print(f"     缓存后: {result['second_round_avg_ms']}ms")
            print(f"     提升倍数: {result['speedup_ratio']}x")

        elif test_name == "repeated_operations":
            print(f"     首次查询: {result['first_query_ms']}ms")
            print(f"     后续平均: {result['subsequent_avg_ms']}ms")
            print(f"     提升倍数: {result['improvement_ratio']}x")
            print(f"     {'🎯' if result['target_achieved'] else '❌'} 10x目标: {'达成' if result['target_achieved'] else '未达成'}")

    def _generate_performance_report(self):
        """生成性能报告"""
        print("\n" + "="*60)
        print("📈 Phase 4 Performance Report")
        print("="*60)

        # 核心性能指标
        cold_start = self.results.get("cold_start_indexing", {})
        warm_start = self.results.get("warm_start_indexing", {})
        repeated_ops = self.results.get("repeated_operations", {})
        cache_stats = self.results.get("cache_statistics", {})

        print(f"\n🚀 核心性能指标:")
        if cold_start and warm_start:
            improvement = warm_start.get("improvement_ratio", 1)
            print(f"   索引构建加速: {improvement}x")

        if repeated_ops:
            repeat_improvement = repeated_ops.get("improvement_ratio", 1)
            target_achieved = repeated_ops.get("target_achieved", False)
            print(f"   重复操作加速: {repeat_improvement}x {'🎯' if target_achieved else '❌'}")

        print(f"\n💾 缓存效率:")
        if cache_stats:
            file_stats = cache_stats.get("file_cache", {})
            tree_stats = cache_stats.get("tree_cache", {})
            symbol_stats = cache_stats.get("symbol_cache", {})

            print(f"   文件缓存命中率: {file_stats.get('cache_hit_ratio', 0):.1%}")
            print(f"   Tree-sitter缓存命中率: {tree_stats.get('hit_ratio', 0):.1%}")
            print(f"   符号缓存命中率: {symbol_stats.get('hit_ratio', 0):.1%}")

        # 保存详细报告
        report_file = Path("phase4_performance_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        # Phase 4成功标准评估
        self._evaluate_phase4_success()

    def _evaluate_phase4_success(self):
        """评估Phase 4成功标准"""
        print(f"\n🎯 Phase 4 Success Criteria Evaluation:")
        print("-" * 40)

        success_criteria = [
            ("重复操作10x+性能提升", self._check_10x_improvement()),
            ("缓存命中率>70%", self._check_cache_hit_rates()),
            ("子秒级响应时间", self._check_response_times())
        ]

        all_passed = True
        for criterion, passed in success_criteria:
            status = "✅ 通过" if passed else "❌ 未达标"
            print(f"   {criterion}: {status}")
            if not passed:
                all_passed = False

        print(f"\n{'🎉 Phase 4 全面成功!' if all_passed else '⚠️  Phase 4 部分目标未达成'}")

    def _check_10x_improvement(self) -> bool:
        """检查10x性能改进目标"""
        repeated_ops = self.results.get("repeated_operations", {})
        return repeated_ops.get("target_achieved", False)

    def _check_cache_hit_rates(self) -> bool:
        """检查缓存命中率"""
        cache_stats = self.results.get("cache_statistics", {})
        file_stats = cache_stats.get("file_cache", {})
        tree_stats = cache_stats.get("tree_cache", {})
        symbol_stats = cache_stats.get("symbol_cache", {})

        file_hit_rate = file_stats.get("cache_hit_ratio", 0)
        tree_hit_rate = tree_stats.get("hit_ratio", 0)
        symbol_hit_rate = symbol_stats.get("hit_ratio", 0)

        # 至少一个缓存命中率>70%
        return max(file_hit_rate, tree_hit_rate, symbol_hit_rate) > 0.7

    def _check_response_times(self) -> bool:
        """检查响应时间"""
        repeated_ops = self.results.get("repeated_operations", {})
        subsequent_avg = repeated_ops.get("subsequent_avg_ms", 1000)
        return subsequent_avg < 1000  # <1秒


def main():
    """主函数"""
    # 使用当前项目作为测试对象
    test_project = Path(__file__).parent

    print("🔧 初始化Phase 4性能基准测试...")

    try:
        benchmark = Phase4Benchmark(str(test_project))
        results = benchmark.run_all_benchmarks()

        print("\n✅ Phase 4基准测试完成!")
        return 0

    except Exception as e:
        print(f"\n❌ 基准测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())