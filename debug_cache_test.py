#!/usr/bin/env python3
"""
调试缓存系统 - 直接验证缓存是否工作
"""

import sys
import time
from pathlib import Path

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from core.index import CodeIndex
    from core.builder import IndexBuilder
    from core.tree_sitter_cache import get_tree_cache, clear_global_tree_cache
    from core.symbol_cache import get_symbol_cache, clear_global_symbol_cache
    from core.cache import get_file_cache, clear_global_cache
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def test_caches_directly():
    """直接测试缓存功能"""
    print("🔧 直接测试缓存功能...")

    # 清空所有缓存
    clear_global_cache()
    clear_global_tree_cache()
    clear_global_symbol_cache()

    # 测试项目
    test_path = Path(__file__).parent

    print(f"📁 测试项目: {test_path}")

    # 第一次构建 - 应该填充缓存
    print("\n📊 第一次索引构建 (填充缓存)...")
    index1 = CodeIndex(str(test_path), {}, {})
    builder1 = IndexBuilder(index1)

    start_time = time.time()
    builder1.build_index()
    first_build_time = time.time() - start_time

    # 获取缓存统计
    file_cache_stats = get_file_cache().get_cache_stats()
    tree_cache_stats = get_tree_cache().get_cache_stats()
    symbol_cache_stats = get_symbol_cache().get_cache_stats()

    print(f"   构建时间: {first_build_time:.3f}s")
    print(f"   文件数量: {len(index1.files)}")
    print(f"   文件缓存: {file_cache_stats['file_count']} 文件")
    print(f"   Tree缓存: {tree_cache_stats['cached_trees']} 解析树")
    print(f"   符号缓存: {symbol_cache_stats['cached_files']} 文件")

    # 第二次构建 - 应该使用缓存
    print("\n📊 第二次索引构建 (使用缓存)...")
    index2 = CodeIndex(str(test_path), {}, {})
    builder2 = IndexBuilder(index2)

    start_time = time.time()
    builder2.build_index()
    second_build_time = time.time() - start_time

    # 获取最新缓存统计
    file_cache_stats2 = get_file_cache().get_cache_stats()
    tree_cache_stats2 = get_tree_cache().get_cache_stats()
    symbol_cache_stats2 = get_symbol_cache().get_cache_stats()

    print(f"   构建时间: {second_build_time:.3f}s")
    print(f"   文件数量: {len(index2.files)}")
    print(f"   文件缓存命中率: {file_cache_stats2['cache_hit_ratio']:.1%}")
    print(f"   Tree缓存命中率: {tree_cache_stats2['hit_ratio']:.1%}")
    print(f"   符号缓存命中率: {symbol_cache_stats2['hit_ratio']:.1%}")

    # 计算改善比例
    improvement = first_build_time / second_build_time if second_build_time > 0 else 1
    print(f"\n🚀 整体性能提升: {improvement:.2f}x")

    # 详细缓存分析
    print(f"\n🔍 缓存详情:")
    print(f"   文件缓存: {file_cache_stats2['cache_hits']} 命中 / {file_cache_stats2['cache_misses']} 未命中")
    print(f"   Tree缓存: {tree_cache_stats2['cache_hits']} 命中 / {tree_cache_stats2['cache_misses']} 未命中")
    print(f"   符号缓存: {symbol_cache_stats2['cache_hits']} 命中 / {symbol_cache_stats2['cache_misses']} 未命中")

    return {
        "first_build_time": first_build_time,
        "second_build_time": second_build_time,
        "improvement": improvement,
        "file_cache_hit_rate": file_cache_stats2['cache_hit_ratio'],
        "tree_cache_hit_rate": tree_cache_stats2['hit_ratio'],
        "symbol_cache_hit_rate": symbol_cache_stats2['hit_ratio']
    }

if __name__ == "__main__":
    results = test_caches_directly()

    print(f"\n🎯 缓存测试结果:")
    print(f"   改善效果: {results['improvement']:.2f}x")
    print(f"   文件缓存命中率: {results['file_cache_hit_rate']:.1%}")
    print(f"   Tree缓存命中率: {results['tree_cache_hit_rate']:.1%}")
    print(f"   符号缓存命中率: {results['symbol_cache_hit_rate']:.1%}")

    if results['tree_cache_hit_rate'] > 0 or results['symbol_cache_hit_rate'] > 0:
        print("\n✅ 缓存系统工作正常!")
    else:
        print("\n❌ 缓存系统可能存在问题")