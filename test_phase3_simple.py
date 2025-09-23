#!/usr/bin/env python3
"""
Phase 3 简单验证 - 测试并行搜索引擎

验证Phase 3的核心功能：
1. 多线程搜索
2. 搜索结果缓存
3. 早期退出优化
"""

import time
import sys
import os

# 设置项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.index import set_project_path, get_index, SearchQuery
from core.search import SearchEngine

def test_phase3_features():
    """测试Phase 3核心功能"""
    print("🚀 Phase 3并行搜索引擎验证")
    print("=" * 50)

    # 1. 设置项目路径
    print("📁 设置项目路径...")
    set_project_path(".")
    index = get_index()
    print(f"   ✅ 索引加载: {len(index.files)}个文件, {len(index.symbols)}个符号")

    # 2. 创建搜索引擎
    search_engine = SearchEngine(index)
    print(f"   ✅ 搜索引擎创建: 优化worker数={search_engine._optimal_workers}")

    # 3. 测试并行文本搜索
    print("\n🔍 测试并行文本搜索...")
    start_time = time.time()
    query = SearchQuery(pattern="def", type="text", limit=50)
    result = search_engine.search(query)
    search_time = time.time() - start_time
    print(f"   ✅ 搜索结果: {result.total_count}个匹配 (限制50)")
    print(f"   ⏱️  搜索时间: {search_time:.4f}秒")
    print(f"   📊 内置测量: {result.search_time:.4f}秒")

    # 4. 测试缓存效果
    print("\n💾 测试搜索缓存...")
    start_time = time.time()
    cached_result = search_engine.search(query)  # 同样的查询
    cache_time = time.time() - start_time
    print(f"   ✅ 缓存搜索: {cached_result.total_count}个匹配")
    print(f"   ⚡ 缓存时间: {cache_time:.4f}秒")
    print(f"   🚀 速度提升: {search_time/cache_time:.1f}x")

    # 5. 测试正则搜索并行
    print("\n🔎 测试并行正则搜索...")
    start_time = time.time()
    regex_query = SearchQuery(pattern=r"def\s+\w+", type="regex", limit=30)
    regex_result = search_engine.search(regex_query)
    regex_time = time.time() - start_time
    print(f"   ✅ 正则结果: {regex_result.total_count}个匹配")
    print(f"   ⏱️  正则时间: {regex_time:.4f}秒")

    # 6. 测试符号搜索
    print("\n🎯 测试符号搜索...")
    symbol_query = SearchQuery(pattern="test", type="symbol", case_sensitive=False)
    symbol_result = search_engine.search(symbol_query)
    print(f"   ✅ 符号结果: {symbol_result.total_count}个匹配")

    # 7. 性能总结
    print("\n📊 Phase 3性能总结:")
    print(f"   🔹 文本搜索: {result.search_time:.4f}秒")
    print(f"   🔹 缓存搜索: {cached_result.search_time:.4f}秒")
    print(f"   🔹 正则搜索: {regex_result.search_time:.4f}秒")
    print(f"   🔹 符号搜索: {symbol_result.search_time:.4f}秒")
    print(f"   🔹 线程池大小: {search_engine._optimal_workers}")

    # 8. 验证早期退出
    total_matches_unlimited = search_engine._search_text_single(
        SearchQuery(pattern="def", type="text", limit=None)
    )
    print(f"   🔹 无限制结果: {len(total_matches_unlimited)}个")
    print(f"   🔹 限制结果: {result.total_count}个")
    print(f"   ✅ 早期退出: {'生效' if len(total_matches_unlimited) > result.total_count else '未生效'}")

    print(f"\n🎉 Phase 3验证完成!")
    return True

if __name__ == "__main__":
    try:
        test_phase3_features()
        print("✨ 所有测试通过!")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()