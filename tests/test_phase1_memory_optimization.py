#!/usr/bin/env python3
"""
Phase 1 内存管理优化验证测试 - Linus风格直接验证

验证内容：
1. 智能缓存大小 - 系统内存自适应
2. 改进的LRU驱逐策略 - 访问模式感知
3. 内存压力检测和紧急清理
4. 缓存统计监控功能

目标：
- 内存使用减少50% (1000文件 < 100MB)
- 缓存命中率 > 70%
- 无内存泄漏
"""

import time
import tempfile
import os
from pathlib import Path
from typing import List, Dict

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from src.core.cache import OptimizedFileCache, get_file_cache, clear_global_cache, _calculate_smart_cache_size


def create_large_project_files(base_dir: str, count: int = 1000) -> List[str]:
    """创建大型项目文件 - 模拟真实项目"""
    files = []
    base_path = Path(base_dir)

    # 创建不同类型的文件
    for i in range(count):
        # 随机文件大小 - 模拟真实项目
        if i % 10 == 0:
            # 10% 大文件 (>10KB)
            line_count = 500
            complexity = "large"
        elif i % 3 == 0:
            # 30% 中等文件 (1-10KB)
            line_count = 100
            complexity = "medium"
        else:
            # 60% 小文件 (<1KB)
            line_count = 20
            complexity = "small"

        file_path = base_path / f"src/module_{i//50}" / f"file_{i}_{complexity}.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        content = f'''"""
File {i} - {complexity} complexity
Generated for Phase 1 memory optimization testing
"""

import os
import sys
from typing import Dict, List, Optional

class TestClass{i}:
    """Test class {i} for complexity {complexity}"""

    def __init__(self, value: int = {i}):
        self.value = value
        self.data = [{j} for j in range({i % 10 + 1})]

    def process_data(self, input_data: List[int]) -> Dict[str, int]:
        """Process input data and return statistics"""
        result = {{
            "count": len(input_data),
            "sum": sum(input_data),
            "max": max(input_data) if input_data else 0,
            "min": min(input_data) if input_data else 0,
        }}
        return result

    def complex_operation(self):
        """Complex operation for testing"""
        operations = []
        for x in range(self.value % 100):
            operations.append(x * 2 + self.value)
        return operations

def utility_function_{i}(param1: str, param2: int = {i}) -> str:
    """Utility function {i}"""
    return f"{{param1}}_{{param2}}_{{complexity}}"

# Constants and configuration
CONFIG_{i} = {{
    "enabled": True,
    "value": {i},
    "complexity": "{complexity}",
    "data": list(range({i % 20}))
}}

'''

        # 根据复杂度添加更多内容
        for line_num in range(line_count - 40):  # 减去已有的40行
            content += f"# Additional line {line_num} for {complexity} file {i}\n"

        file_path.write_text(content, encoding='utf-8')
        files.append(str(file_path))

    return files


def test_smart_cache_sizing():
    """测试智能缓存大小计算"""
    print("🧠 测试智能缓存大小计算...")

    # 获取计算结果
    max_files, max_memory_mb = _calculate_smart_cache_size()

    # 获取系统内存信息进行验证
    memory = psutil.virtual_memory()
    total_memory_gb = memory.total / (1024 ** 3)

    print(f"   系统内存: {total_memory_gb:.1f}GB")
    print(f"   计算的缓存大小: {max_files} 文件")
    print(f"   计算的内存限制: {max_memory_mb}MB")

    # 验证计算逻辑
    expected_files = int(400 * total_memory_gb)
    expected_memory = int((memory.total * 0.2) / (1024 * 1024))

    # 考虑安全范围
    assert 100 <= max_files <= 5000, f"文件数量超出安全范围: {max_files}"
    assert 50 <= max_memory_mb <= 2048, f"内存限制超出安全范围: {max_memory_mb}MB"

    print("✅ 智能缓存大小计算测试通过!")
    return max_files, max_memory_mb


def test_memory_pressure_detection():
    """测试内存压力检测和紧急清理"""
    print("\n⚠️ 测试内存压力检测...")

    # 创建有限内存的缓存
    cache = OptimizedFileCache(max_size=100, max_memory_mb=5)

    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建足够多的文件来触发内存压力
        test_files = create_large_project_files(temp_dir, 150)

        # 记录初始状态
        initial_memory = psutil.virtual_memory().available

        # 模拟高内存使用
        print("   加载大量文件...")
        for i, file_path in enumerate(test_files):
            cache.get_file_lines(file_path)

            # 每20个文件检查一次
            if i % 20 == 0:
                stats = cache.get_cache_stats()
                print(f"   进度: {i+1}/150, 缓存文件: {stats['file_count']}, 内存: {stats['memory_usage_mb']:.1f}MB")

        # 获取最终统计
        final_stats = cache.get_cache_stats()

        print(f"   最终文件数: {final_stats['file_count']}")
        print(f"   最终内存使用: {final_stats['memory_usage_mb']:.2f}MB")
        print(f"   清理次数: {final_stats['cleanup_count']}")
        print(f"   内存警告: {final_stats['memory_warnings']}")
        print(f"   紧急清理: {final_stats['emergency_cleanups']}")

        # 验证内存限制有效
        assert final_stats['memory_usage_mb'] <= 5.0, f"内存限制失效: {final_stats['memory_usage_mb']:.2f}MB"
        assert final_stats['file_count'] <= 100, f"文件数量限制失效: {final_stats['file_count']}"

        print("✅ 内存压力检测测试通过!")
        return final_stats


def test_intelligent_lru_strategy():
    """测试智能LRU驱逐策略"""
    print("\n🧮 测试智能LRU驱逐策略...")

    cache = OptimizedFileCache(max_size=20, max_memory_mb=2)

    with tempfile.TemporaryDirectory() as temp_dir:
        test_files = create_large_project_files(temp_dir, 30)

        # 第一阶段: 正常访问
        print("   第一阶段: 正常加载文件...")
        for file_path in test_files[:15]:
            cache.get_file_lines(file_path)

        # 第二阶段: 创建访问模式
        print("   第二阶段: 创建访问模式...")
        # 高频访问某些文件
        high_freq_files = test_files[:5]
        for _ in range(5):  # 访问5次
            for file_path in high_freq_files:
                cache.get_file_lines(file_path)
                time.sleep(0.01)  # 小延迟模拟真实访问

        # 规律访问某些文件
        pattern_files = test_files[5:8]
        for _ in range(3):
            for file_path in pattern_files:
                cache.get_file_lines(file_path)
                time.sleep(0.05)  # 规律间隔

        # 第三阶段: 触发LRU驱逐
        print("   第三阶段: 触发LRU驱逐...")
        # 添加新文件，应该驱逐低频文件，保留高频和模式文件
        for file_path in test_files[20:]:
            cache.get_file_lines(file_path)

        # 验证智能LRU策略
        stats = cache.get_cache_stats()
        print(f"   最终文件数: {stats['file_count']}")
        print(f"   清理次数: {stats['cleanup_count']}")

        # 检查高频文件是否仍在缓存中
        high_freq_preserved = 0
        for file_path in high_freq_files:
            if file_path in cache._cache:
                high_freq_preserved += 1

        print(f"   高频文件保留: {high_freq_preserved}/{len(high_freq_files)}")

        # 验证策略效果
        assert stats['file_count'] <= 20, "文件数量控制失效"
        assert high_freq_preserved >= 3, "智能LRU策略未能保护高频文件"

        print("✅ 智能LRU策略测试通过!")
        return stats


def test_cache_statistics_monitoring():
    """测试缓存统计监控功能"""
    print("\n📊 测试缓存统计监控功能...")

    cache = OptimizedFileCache(max_size=50, max_memory_mb=3)

    with tempfile.TemporaryDirectory() as temp_dir:
        test_files = create_large_project_files(temp_dir, 60)

        # 执行各种操作来生成统计数据
        print("   执行缓存操作...")

        # 冷访问
        for file_path in test_files[:30]:
            cache.get_file_lines(file_path)

        # 热访问 (重复)
        for file_path in test_files[:15]:
            cache.get_file_lines(file_path)

        # 获取详细统计
        stats = cache.get_cache_stats()

        print(f"   📈 缓存统计报告:")
        print(f"      文件数量: {stats['file_count']}")
        print(f"      内存使用: {stats['memory_usage_mb']:.2f}MB")
        print(f"      缓存命中率: {stats['cache_hit_ratio']:.3f}")
        print(f"      总请求数: {stats['total_requests']}")
        print(f"      缓存命中: {stats['cache_hits']}")
        print(f"      缓存未命中: {stats['cache_misses']}")
        print(f"      运行时间: {stats['uptime_hours']:.2f}小时")
        print(f"      每小时请求: {stats['avg_requests_per_hour']:.1f}")
        print(f"      内存压力: {stats['memory_pressure']}")
        print(f"      系统内存: {stats['system_memory_mb']:.0f}MB")
        print(f"      可用内存: {stats['system_available_mb']:.0f}MB")

        # 验证统计数据合理性
        assert stats['total_requests'] > 0, "总请求数应该大于0"
        assert stats['cache_hits'] + stats['cache_misses'] == stats['total_requests'], "命中数据不一致"
        assert 0 <= stats['cache_hit_ratio'] <= 1, "命中率应该在0-1之间"
        assert stats['memory_usage_mb'] > 0, "内存使用应该大于0"

        # 检查访问模式统计
        if 'most_accessed_files' in stats:
            print(f"   🔥 最高访问文件数: {len(stats['most_accessed_files'])}")

        if 'recent_activity' in stats:
            activity = stats['recent_activity']
            print(f"   ⚡ 最近活动: {activity['active_files_last_hour']} 文件")
            print(f"   🎯 缓存效率: {activity['cache_efficiency']}")

        print("✅ 缓存统计监控测试通过!")
        return stats


def test_phase1_performance_targets():
    """测试Phase 1性能目标达成情况"""
    print("\n🎯 验证Phase 1性能目标...")

    # 清理全局缓存
    clear_global_cache()

    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建1000个文件的大型项目
        print("   创建1000文件的大型项目...")
        test_files = create_large_project_files(temp_dir, 1000)

        # 获取全局缓存 (使用智能大小)
        cache = get_file_cache()

        # 记录开始时的内存
        process = psutil.Process()
        start_memory = process.memory_info().rss / (1024 * 1024)  # MB

        print(f"   开始内存使用: {start_memory:.1f}MB")

        # 加载所有文件 (模拟实际使用)
        print("   加载文件中...")
        load_start = time.time()

        for i, file_path in enumerate(test_files):
            cache.get_file_lines(file_path)

            # 每100个文件打印进度
            if (i + 1) % 100 == 0:
                current_memory = process.memory_info().rss / (1024 * 1024)
                print(f"     进度: {i+1}/1000, 内存: {current_memory:.1f}MB")

        load_time = time.time() - load_start

        # 记录结束时的内存
        end_memory = process.memory_info().rss / (1024 * 1024)
        cache_memory = end_memory - start_memory

        # 获取详细统计
        stats = cache.get_cache_stats()

        print(f"\n   📊 Phase 1 性能结果:")
        print(f"      总加载时间: {load_time:.2f}秒")
        print(f"      缓存文件数: {stats['file_count']}")
        print(f"      缓存内存使用: {stats['memory_usage_mb']:.1f}MB")
        print(f"      进程内存增长: {cache_memory:.1f}MB")
        print(f"      缓存命中率: {stats['cache_hit_ratio']:.3f}")
        print(f"      清理次数: {stats['cleanup_count']}")

        # 验证Phase 1目标
        print(f"\n   🎯 目标验证:")

        # 目标1: 内存使用 < 100MB (1000文件)
        memory_target = cache_memory < 100
        print(f"      内存目标 (<100MB): {'✅' if memory_target else '❌'} {cache_memory:.1f}MB")

        # 目标2: 缓存命中率 > 70%
        hit_rate_target = stats['cache_hit_ratio'] > 0.7
        print(f"      命中率目标 (>70%): {'✅' if hit_rate_target else '❌'} {stats['cache_hit_ratio']:.1%}")

        # 目标3: 无内存泄漏 (合理的内存增长)
        memory_leak_check = cache_memory < 200  # 合理上限
        print(f"      内存泄漏检查 (<200MB): {'✅' if memory_leak_check else '❌'} {cache_memory:.1f}MB")

        # 目标4: 性能合理 (平均<1ms/文件)
        avg_time_per_file = (load_time / 1000) * 1000  # ms
        performance_target = avg_time_per_file < 1.0
        print(f"      性能目标 (<1ms/文件): {'✅' if performance_target else '❌'} {avg_time_per_file:.2f}ms")

        # 总体评估
        all_targets_met = all([memory_target, hit_rate_target, memory_leak_check, performance_target])

        print(f"\n   🏆 Phase 1 总体评估: {'✅ 全部达标' if all_targets_met else '❌ 部分未达标'}")

        return {
            'memory_usage_mb': cache_memory,
            'cache_hit_ratio': stats['cache_hit_ratio'],
            'load_time_seconds': load_time,
            'avg_time_per_file_ms': avg_time_per_file,
            'targets_met': all_targets_met,
            'detailed_stats': stats
        }


def main():
    """主测试入口"""
    print("=" * 80)
    print("🚀 Phase 1 内存管理优化验证测试")
    print("=" * 80)

    try:
        # 执行所有测试
        smart_sizing = test_smart_cache_sizing()
        memory_pressure = test_memory_pressure_detection()
        lru_strategy = test_intelligent_lru_strategy()
        cache_monitoring = test_cache_statistics_monitoring()
        performance_results = test_phase1_performance_targets()

        print("\n" + "=" * 80)
        print("🎉 Phase 1 优化验证完成!")
        print("=" * 80)

        # 总结报告
        print(f"\n📋 Phase 1 优化总结:")
        print(f"   智能缓存大小: ✅ 自动适配系统内存")
        print(f"   内存压力检测: ✅ 自动清理和保护")
        print(f"   智能LRU策略: ✅ 访问模式感知")
        print(f"   缓存统计监控: ✅ 完整性能指标")
        print(f"   性能目标达成: {'✅' if performance_results['targets_met'] else '❌'}")

        if performance_results['targets_met']:
            print(f"\n🏆 恭喜! Phase 1 内存管理优化全部目标达成:")
            print(f"   • 内存使用: {performance_results['memory_usage_mb']:.1f}MB (目标: <100MB)")
            print(f"   • 缓存命中率: {performance_results['cache_hit_ratio']:.1%} (目标: >70%)")
            print(f"   • 平均性能: {performance_results['avg_time_per_file_ms']:.2f}ms/文件 (目标: <1ms)")
            print(f"   • 加载时间: {performance_results['load_time_seconds']:.2f}秒/1000文件")

        return performance_results['targets_met']

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)