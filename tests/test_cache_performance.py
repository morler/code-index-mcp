#!/usr/bin/env python3
"""
测试缓存性能 - Linus风格直接验证

验证内容：
1. 文件缓存命中率
2. 内存使用控制
3. LRU淘汰策略
4. I/O性能提升
"""

import time
import tempfile
from pathlib import Path
from typing import List

from src.core.cache import OptimizedFileCache, get_file_cache, clear_global_cache
from src.core.index import CodeIndex
from src.core.search_optimized import OptimizedSearchEngine


def create_test_files(base_dir: str, count: int = 100) -> List[str]:
    """创建测试文件 - Linus原则: 真实数据测试"""
    files = []
    base_path = Path(base_dir)

    for i in range(count):
        file_path = base_path / f"test_file_{i}.py"
        content = f'''"""
测试文件 {i}
"""

class TestClass{i}:
    def __init__(self):
        self.value = {i}
    
    def method_{i}(self, param):
        """Method {i} documentation"""
        return param + {i}

def function_{i}():
    """Function {i} documentation"""
    return {i} * 2

# 变量定义
TEST_CONSTANT_{i} = {i}
''' + "\n".join(
            [f"# 填充行 {j}" for j in range(50)]
        )  # 增加文件大小

        file_path.write_text(content, encoding="utf-8")
        files.append(str(file_path))

    return files


def test_cache_performance():
    """测试缓存性能 - 直接数据验证"""
    print("🚀 开始缓存性能测试...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. 创建测试文件
        print("📁 创建测试文件...")
        test_files = create_test_files(temp_dir, 50)

        # 2. 创建独立缓存实例进行测试
        cache = OptimizedFileCache(max_size=30, max_memory_mb=5)

        # 3. 第一次读取 - 冷缓存
        print("❄️ 冷缓存测试...")
        start_time = time.time()
        for file_path in test_files:
            lines = cache.get_file_lines(file_path)
            assert len(lines) > 0, f"文件 {file_path} 读取失败"
        cold_time = time.time() - start_time

        stats_cold = cache.get_cache_stats()
        print(f"   冷缓存时间: {cold_time:.3f}s")
        print(f"   缓存文件数: {stats_cold['file_count']}")
        print(f"   内存使用: {stats_cold['memory_usage_mb']:.2f}MB")

        # 4. 第二次读取 - 热缓存
        print("🔥 热缓存测试...")
        start_time = time.time()
        for file_path in test_files[:30]:  # 只读取缓存中的文件
            lines = cache.get_file_lines(file_path)
            assert len(lines) > 0, f"文件 {file_path} 缓存读取失败"
        hot_time = time.time() - start_time

        stats_hot = cache.get_cache_stats()
        print(f"   热缓存时间: {hot_time:.3f}s")
        print(f"   性能提升: {cold_time/hot_time:.1f}x")
        print(f"   缓存命中率: {stats_hot['cache_hit_ratio']:.2f}")

        # 5. 测试LRU淘汰机制
        print("🗑️ LRU淘汰测试...")
        # 超过max_size限制，应该触发淘汰
        extra_dir = Path(temp_dir) / "extra"
        extra_dir.mkdir(exist_ok=True)
        extra_files = create_test_files(str(extra_dir), 25)
        for file_path in extra_files:
            cache.get_file_lines(file_path)

        stats_lru = cache.get_cache_stats()
        print(f"   淘汰后文件数: {stats_lru['file_count']}")
        print(f"   内存使用: {stats_lru['memory_usage_mb']:.2f}MB")
        assert stats_lru["file_count"] <= cache._max_size, "LRU淘汰机制失效"

        # 6. 测试文件变更检测
        print("🔄 文件变更检测测试...")
        test_file = test_files[0]
        original_lines = cache.get_file_lines(test_file)

        # 修改文件
        Path(test_file).write_text(
            "# 修改后的内容\nnew_line = True\n", encoding="utf-8"
        )

        # 重新读取应该检测到变更
        updated_lines = cache.get_file_lines(test_file)
        assert len(updated_lines) != len(original_lines), "文件变更检测失败"
        assert "new_line = True" in updated_lines[1], "文件内容更新失败"

        print("✅ 缓存性能测试通过!")
        return True


def test_search_engine_cache():
    """测试搜索引擎缓存集成"""
    print("\n🔍 测试搜索引擎缓存集成...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 清理全局缓存
        clear_global_cache()

        # 创建测试文件
        test_files = create_test_files(temp_dir, 20)

        # 创建索引和搜索引擎
        index = CodeIndex(base_path=temp_dir, files={}, symbols={})
        search_engine = OptimizedSearchEngine(index)

        # 添加文件到索引
        from src.core.index import FileInfo

        for file_path in test_files:
            file_info = FileInfo(
                language="python", line_count=100, symbols={}, imports=[]
            )
            index.add_file(file_path, file_info)

        # 执行搜索测试
        from src.core.index import SearchQuery

        start_time = time.time()
        query = SearchQuery(pattern="TestClass", type="text", case_sensitive=False)
        results = search_engine.search(query)
        search_time = time.time() - start_time

        print(f"   搜索结果数: {len(results.matches)}")
        print(f"   搜索时间: {search_time:.3f}s")

        # 获取缓存统计
        cache_stats = search_engine.get_cache_stats()
        print(f"   文件缓存: {cache_stats['file_cache']['file_count']} 文件")
        print(f"   正则缓存: {cache_stats['regex_cache']['current_size']} 模式")

        # 第二次相同搜索 - 应该更快
        start_time = time.time()
        results2 = search_engine.search(query)
        search_time2 = time.time() - start_time

        print(f"   二次搜索时间: {search_time2:.3f}s")
        print(f"   性能提升: {search_time/search_time2:.1f}x")

        assert len(results.matches) == len(results2.matches), "搜索结果不一致"
        print("✅ 搜索引擎缓存测试通过!")

        return True


def test_memory_limits():
    """测试内存限制功能"""
    print("\n💾 测试内存限制功能...")

    # 创建小内存限制的缓存
    cache = OptimizedFileCache(max_size=1000, max_memory_mb=1)  # 仅1MB

    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建大文件超过内存限制
        large_files = []
        for i in range(10):
            file_path = Path(temp_dir) / f"large_file_{i}.py"
            # 创建较大内容
            content = "\n".join([f"# 大文件行 {j}" + "x" * 100 for j in range(1000)])
            file_path.write_text(content, encoding="utf-8")
            large_files.append(str(file_path))

        # 加载文件，应该触发内存清理
        for file_path in large_files:
            cache.get_file_lines(file_path)

        stats = cache.get_cache_stats()
        print(f"   最终文件数: {stats['file_count']}")
        print(f"   内存使用: {stats['memory_usage_mb']:.2f}MB")

        # 验证内存限制生效
        assert (
            stats["memory_usage_mb"] <= 1.0
        ), f"内存限制失效: {stats['memory_usage_mb']:.2f}MB"
        print("✅ 内存限制测试通过!")

        return True


def main():
    """主测试入口"""
    print("=" * 60)
    print("🧪 Linus风格缓存性能测试套件")
    print("=" * 60)

    try:
        # 执行所有测试
        test_cache_performance()
        test_search_engine_cache()
        test_memory_limits()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过! 缓存系统工作正常")
        print("=" * 60)

        # 显示最终统计
        global_cache = get_file_cache()
        final_stats = global_cache.get_cache_stats()
        print("\n📊 全局缓存统计:")
        print(f"   文件数量: {final_stats['file_count']}")
        print(f"   内存使用: {final_stats['memory_usage_mb']:.2f}MB")
        print(f"   缓存命中率: {final_stats['cache_hit_ratio']:.2f}")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
