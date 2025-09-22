#!/usr/bin/env python3
"""
哈希算法性能对比测试 - Linus风格直接测量

对比:
1. MD5 vs xxhash3 性能
2. 文件大小对性能的影响
3. 缓存命中率改进
"""

import time
import tempfile
import hashlib
import xxhash
from pathlib import Path
from typing import List, Tuple


def create_test_files_various_sizes(base_dir: str) -> List[Tuple[str, int]]:
    """创建不同大小的测试文件"""
    files = []
    base_path = Path(base_dir)
    
    sizes = [
        (100, "tiny"),         # 100 字节
        (1024, "small"),       # 1KB 
        (10240, "medium"),     # 10KB
        (51200, "large"),      # 50KB (触发分段采样)
        (512000, "xlarge"),    # 500KB
        (5120000, "xxlarge")   # 5MB (大文件)
    ]
    
    for size, name in sizes:
        for i in range(10):  # 每种大小创建10个文件
            file_path = base_path / f"{name}_file_{i}.py"
            
            # 创建指定大小的内容
            content = f"# 测试文件 {name} {i}\n"
            content += "x" * (size - len(content.encode()))
            
            file_path.write_text(content, encoding='utf-8')
            files.append((str(file_path), size))
    
    return files


def benchmark_md5(file_path: str, size: int) -> float:
    """MD5 哈希性能测试 - 模拟旧算法"""
    try:
        path = Path(file_path)
        stat = path.stat()
        
        start_time = time.perf_counter()
        
        # 小文件简单处理
        if size < 1024:
            result = hashlib.md5(f"{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
        else:
            # 大文件处理
            hasher = hashlib.md5()
            hasher.update(f"{stat.st_mtime}:{stat.st_size}".encode())
            
            with open(file_path, 'rb') as f:
                hasher.update(f.read(512))
                if size > 50000:
                    f.seek(size // 2)
                    hasher.update(f.read(512))
                    f.seek(-512, 2)
                    hasher.update(f.read(512))
            
            result = hasher.hexdigest()
        
        end_time = time.perf_counter()
        return end_time - start_time
        
    except Exception:
        return 0.0


def benchmark_xxhash3(file_path: str, size: int) -> float:
    """xxhash3 性能测试 - 新优化算法"""
    try:
        path = Path(file_path)
        stat = path.stat()
        
        start_time = time.perf_counter()
        
        # 小文件极速处理
        if size < 1024:
            result = xxhash.xxh3_64(f"{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()
        else:
            # 大文件分段采样
            hasher = xxhash.xxh3_64()
            hasher.update(f"{stat.st_mtime}:{stat.st_size}".encode())
            
            with open(file_path, 'rb') as f:
                hasher.update(f.read(512))
                if size > 50000:
                    f.seek(size // 2)
                    hasher.update(f.read(512))
                    f.seek(-512, 2)
                    hasher.update(f.read(512))
            
            result = hasher.hexdigest()
        
        end_time = time.perf_counter()
        return end_time - start_time
        
    except Exception:
        return 0.0


def test_hash_performance():
    """哈希算法性能对比"""
    print("🏁 哈希算法性能对比测试")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print("📁 创建测试文件...")
        test_files = create_test_files_various_sizes(temp_dir)
        print(f"   创建了 {len(test_files)} 个测试文件")
        
        # 按文件大小分组测试
        size_groups = {}
        for file_path, size in test_files:
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append((file_path, size))
        
        print("\n📊 性能测试结果:")
        print(f"{'文件大小':<12} {'MD5 (ms)':<12} {'xxhash3 (ms)':<14} {'提升倍数':<10}")
        print("-" * 60)
        
        total_md5_time = 0
        total_xxhash_time = 0
        
        for size in sorted(size_groups.keys()):
            files = size_groups[size]
            
            # 测试 MD5
            md5_times = []
            for file_path, file_size in files:
                md5_time = benchmark_md5(file_path, file_size)
                md5_times.append(md5_time)
            
            # 测试 xxhash3
            xxhash_times = []
            for file_path, file_size in files:
                xxhash_time = benchmark_xxhash3(file_path, file_size)
                xxhash_times.append(xxhash_time)
            
            # 计算平均时间
            avg_md5 = sum(md5_times) / len(md5_times) * 1000  # 转换为毫秒
            avg_xxhash = sum(xxhash_times) / len(xxhash_times) * 1000
            
            total_md5_time += avg_md5
            total_xxhash_time += avg_xxhash
            
            # 计算提升倍数
            improvement = avg_md5 / avg_xxhash if avg_xxhash > 0 else 0
            
            # 格式化大小显示
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024*1024:
                size_str = f"{size//1024}KB"
            else:
                size_str = f"{size//(1024*1024)}MB"
            
            print(f"{size_str:<12} {avg_md5:<12.3f} {avg_xxhash:<14.3f} {improvement:<10.1f}x")
        
        print("-" * 60)
        total_improvement = total_md5_time / total_xxhash_time if total_xxhash_time > 0 else 0
        print(f"{'总计':<12} {total_md5_time:<12.1f} {total_xxhash_time:<14.1f} {total_improvement:<10.1f}x")
        
        return total_improvement


def test_cache_integration():
    """测试新哈希算法在缓存中的集成效果"""
    print("\n🔗 缓存集成效果测试")
    print("=" * 60)
    
    from src.core.cache import OptimizedFileCache
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        test_files = create_test_files_various_sizes(temp_dir)
        cache = OptimizedFileCache(max_size=100, max_memory_mb=10)
        
        print("⏱️  第一次访问 (冷缓存 + 哈希计算)...")
        start_time = time.perf_counter()
        for file_path, size in test_files:
            lines = cache.get_file_lines(file_path)
        first_access_time = time.perf_counter() - start_time
        
        print("⚡ 第二次访问 (热缓存，无哈希计算)...")
        start_time = time.perf_counter()
        for file_path, size in test_files:
            lines = cache.get_file_lines(file_path)
        second_access_time = time.perf_counter() - start_time
        
        print("🔄 修改文件后访问 (哈希检测变更)...")
        # 修改一个文件
        Path(test_files[0][0]).write_text("# 修改内容\nnew_content = True\n")
        
        start_time = time.perf_counter()
        lines = cache.get_file_lines(test_files[0][0])
        change_detect_time = time.perf_counter() - start_time
        
        cache_stats = cache.get_cache_stats()
        
        print(f"\n📈 结果:")
        print(f"   冷缓存时间: {first_access_time*1000:.1f}ms")
        print(f"   热缓存时间: {second_access_time*1000:.1f}ms") 
        print(f"   变更检测时间: {change_detect_time*1000:.1f}ms")
        print(f"   缓存文件数: {cache_stats['file_count']}")
        print(f"   内存使用: {cache_stats['memory_usage_mb']:.2f}MB")
        
        cache_speedup = first_access_time / second_access_time
        print(f"   缓存加速比: {cache_speedup:.1f}x")
        
        return cache_speedup


def main():
    """主测试函数"""
    print("🧪 xxhash3 vs MD5 性能对比测试")
    print("Linus原则: 用真实数据测试真实性能")
    print("=" * 60)
    
    try:
        # 哈希算法性能对比
        hash_improvement = test_hash_performance()
        
        # 缓存集成测试
        cache_speedup = test_cache_integration()
        
        print("\n" + "=" * 60)
        print("🎉 性能测试完成!")
        print(f"📊 哈希算法提升: {hash_improvement:.1f}x")
        print(f"🚀 缓存系统加速: {cache_speedup:.1f}x")
        
        if hash_improvement > 2.0:
            print("✅ xxhash3 显著优于 MD5 - 升级成功!")
        else:
            print("⚠️  性能提升有限，但仍然是改进")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)