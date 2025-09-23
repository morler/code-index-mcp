#!/usr/bin/env python3
"""
专门测试Tree-sitter缓存的基准测试
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

def test_treesitter_cache():
    """测试Tree-sitter缓存"""
    print("🔧 测试Tree-sitter缓存...")

    # 使用包含Go和JavaScript文件的测试项目
    test_path = Path(__file__).parent / "test" / "sample-projects"
    if not test_path.exists():
        print(f"❌ 测试项目不存在: {test_path}")
        return

    print(f"📁 测试项目: {test_path}")

    # 清空所有缓存
    clear_global_cache()
    clear_global_tree_cache()
    clear_global_symbol_cache()

    # 第一次构建 - 填充缓存
    print("\n📊 第一次索引构建 (填充缓存)...")
    index1 = CodeIndex(str(test_path), {}, {})
    builder1 = IndexBuilder(index1)

    start_time = time.time()
    builder1.build_index()
    first_build_time = time.time() - start_time

    # 获取缓存统计
    tree_cache_stats = get_tree_cache().get_cache_stats()
    symbol_cache_stats = get_symbol_cache().get_cache_stats()

    print(f"   构建时间: {first_build_time:.3f}s")
    print(f"   文件数量: {len(index1.files)}")
    print(f"   Tree缓存: {tree_cache_stats['cached_trees']} 解析树")
    print(f"   符号缓存: {symbol_cache_stats['cached_files']} 文件")

    # 第二次构建 - 使用缓存
    print("\n📊 第二次索引构建 (使用缓存)...")
    index2 = CodeIndex(str(test_path), {}, {})
    builder2 = IndexBuilder(index2)

    start_time = time.time()
    builder2.build_index()
    second_build_time = time.time() - start_time

    # 获取最新缓存统计
    tree_cache_stats2 = get_tree_cache().get_cache_stats()
    symbol_cache_stats2 = get_symbol_cache().get_cache_stats()

    print(f"   构建时间: {second_build_time:.3f}s")
    print(f"   文件数量: {len(index2.files)}")
    print(f"   Tree缓存命中率: {tree_cache_stats2['hit_ratio']:.1%}")
    print(f"   符号缓存命中率: {symbol_cache_stats2['hit_ratio']:.1%}")

    # 计算改善比例
    improvement = first_build_time / second_build_time if second_build_time > 0 else 1
    print(f"\n🚀 整体性能提升: {improvement:.2f}x")

    # 详细缓存分析
    print(f"\n🔍 缓存详情:")
    print(f"   Tree缓存: {tree_cache_stats2['cache_hits']} 命中 / {tree_cache_stats2['cache_misses']} 未命中")
    print(f"   符号缓存: {symbol_cache_stats2['cache_hits']} 命中 / {symbol_cache_stats2['cache_misses']} 未命中")

    return improvement, tree_cache_stats2['hit_ratio'], symbol_cache_stats2['hit_ratio']

def test_single_file_cache():
    """测试单个文件的缓存效果"""
    print("\n🔧 测试单个Go文件缓存...")

    go_file = Path(__file__).parent / "test" / "sample-projects" / "go" / "user-management" / "cmd" / "server" / "main.go"
    if not go_file.exists():
        print(f"❌ Go文件不存在: {go_file}")
        return

    # 清空缓存
    clear_global_tree_cache()
    clear_global_symbol_cache()

    # 创建builder
    index = CodeIndex(str(go_file.parent.parent.parent), {}, {})
    builder = IndexBuilder(index)

    # 第一次处理文件
    print(f"📄 处理文件: {go_file.name}")
    start_time = time.time()
    builder._process_tree_sitter(str(go_file))
    first_time = time.time() - start_time

    tree_stats = get_tree_cache().get_cache_stats()
    symbol_stats = get_symbol_cache().get_cache_stats()

    print(f"   首次处理: {first_time*1000:.2f}ms")
    print(f"   Tree缓存: {tree_stats['cached_trees']} 解析树")
    print(f"   符号缓存: {symbol_stats['cached_files']} 文件")

    # 第二次处理同一文件
    start_time = time.time()
    builder._process_tree_sitter(str(go_file))
    second_time = time.time() - start_time

    tree_stats2 = get_tree_cache().get_cache_stats()
    symbol_stats2 = get_symbol_cache().get_cache_stats()

    print(f"   二次处理: {second_time*1000:.2f}ms")
    print(f"   Tree缓存命中率: {tree_stats2['hit_ratio']:.1%}")
    print(f"   符号缓存命中率: {symbol_stats2['hit_ratio']:.1%}")

    if second_time > 0:
        speedup = first_time / second_time
        print(f"   加速比: {speedup:.2f}x")
        return speedup
    return 1.0

if __name__ == "__main__":
    # 测试整个项目
    overall_improvement, tree_hit_rate, symbol_hit_rate = test_treesitter_cache()

    # 测试单个文件
    file_speedup = test_single_file_cache()

    print(f"\n🎯 测试总结:")
    print(f"   整体改善: {overall_improvement:.2f}x")
    print(f"   单文件加速: {file_speedup:.2f}x")
    print(f"   Tree缓存命中率: {tree_hit_rate:.1%}")
    print(f"   符号缓存命中率: {symbol_hit_rate:.1%}")

    if tree_hit_rate > 0 or symbol_hit_rate > 0:
        print("\n✅ Tree-sitter缓存系统工作正常!")
    else:
        print("\n❌ Tree-sitter缓存系统未生效")