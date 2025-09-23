# Code Index MCP Performance Optimization Plan

## 🎯 Project Goal
Implement Linus-style performance optimizations to achieve 2-3x overall performance improvement while reducing memory usage by 50% for large projects (1000+ files).

## 📋 Development Phases

### Phase 1: Memory Management Optimization ⭐⭐⭐
**Priority**: Critical
**Estimated Time**: 2-3 days
**Target**: Reduce memory usage by 50%

#### Tasks:
1. **Smart Cache Sizing**
   - Modify `src/core/cache.py:235` to implement dynamic cache sizing
   - Add system memory detection using `psutil`
   - Set intelligent defaults: 400 files per GB of system RAM
   - Maximum cache memory: 20% of total system memory

2. **Cache Eviction Improvements**
   - Implement smarter LRU eviction based on file access patterns
   - Add cache statistics monitoring
   - Implement cache warming for frequently accessed files

3. **Memory Usage Monitoring**
   - Add memory usage tracking to cache statistics
   - Implement memory pressure detection
   - Add emergency cache clearing when memory is low

#### Success Criteria:
- Memory usage under 100MB for projects with 1000+ files
- Cache hit rate > 70%
- No memory leaks in long-running sessions

### Phase 2: Ultra-Fast File Change Detection ⭐⭐⭐
**Priority**: Critical
**Estimated Time**: 1-2 days
**Target**: 3-5x faster change detection

#### Tasks:
1. **Metadata-Only Hashing**
   - Replace full content hashing with metadata for files > 10KB
   - Use `mtime:size:inode` for large files
   - Keep content hashing only for small files (< 10KB)

2. **Smart Hash Strategy**
   ```python
   def _calculate_file_hash_ultra_fast(self, file_path: str) -> str:
       stat = Path(file_path).stat()
       if stat.st_size < 10240:
           # Small files: content hash
           return xxhash.xxh3_64(content).hexdigest()
       else:
           # Large files: metadata only
           return f"{stat.st_mtime}:{stat.st_size}:{stat.st_ino}"
   ```

3. **Batch Change Detection**
   - Process multiple files in parallel
   - Use `os.scandir()` for faster directory traversal
   - Implement early exit for unchanged directories

#### Success Criteria:
- File change detection < 1ms per file on average
- 90%+ accuracy in change detection
- No false negatives for actual file changes

### Phase 3: Parallel Search Engine ⭐⭐
**Priority**: High
**Estimated Time**: 2-3 days
**Target**: 2-4x faster search on large projects

#### Tasks:
1. **Multi-threaded Search**
   - Implement `ThreadPoolExecutor` for file searching
   - Optimal worker count: `min(4, file_count//10)`
   - Graceful fallback to single-threaded for small projects

2. **Search Result Caching**
   ```python
   @lru_cache(maxsize=100)
   def _search_cached(self, query_hash: str, file_signatures: tuple):
       # Cache search results when file signatures unchanged
   ```

3. **Early Exit Optimization**
   - Add result limit parameter to search queries
   - Default maximum: 1000 results
   - Stop searching when limit reached

#### Success Criteria:
- Search time < 10ms for typical queries
- Linear scaling with CPU cores (up to 4 cores)
- No race conditions or thread safety issues

### Phase 4: Advanced Caching Layer ⭐⭐
**Priority**: Medium
**Estimated Time**: 2-3 days
**Target**: 10x+ faster repeated operations

#### Tasks:
1. **Query Result Caching**
   - Cache search results with file signature dependencies
   - Intelligent cache invalidation on file changes
   - Separate caches for different query types

2. **Tree-sitter Parse Caching**
   ```python
   class TreeSitterCache:
       def __init__(self):
           self._tree_cache = {}  # content_hash -> parsed_tree

       def get_tree(self, file_path: str, content_hash: str):
           # Return cached parse tree or create new one
   ```

3. **Symbol Index Caching**
   - Cache extracted symbols with file hash dependencies
   - Incremental symbol updates
   - Cross-file symbol reference caching

#### Success Criteria:
- Repeated searches < 1ms response time
- Parse tree reuse rate > 80%
- Symbol extraction cache hit rate > 90%

### Phase 5: I/O Optimization ⭐
**Priority**: Low
**Estimated Time**: 1-2 days
**Target**: Reduce I/O bottlenecks

#### Tasks:
1. **Async File Operations**
   - Use `aiofiles` for non-blocking file reads
   - Batch file operations where possible
   - Implement read-ahead for predictable access patterns

2. **Optimized File Reading**
   - Use memory-mapped files for large files
   - Implement streaming readers for huge files
   - Buffer size optimization based on file type

3. **Directory Traversal Optimization**
   - Use `os.scandir()` instead of `os.listdir()`
   - Implement parallel directory scanning
   - Smart filtering during traversal

#### Success Criteria:
- File read operations < 0.1ms for cached files
- Directory scanning 2x faster than current
- No I/O blocking during indexing

## 🔧 Implementation Strategy

### Development Approach:
1. **Measure First**: Run current benchmarks to establish baseline
2. **Incremental Changes**: Implement one optimization at a time
3. **Continuous Testing**: Run performance tests after each change
4. **Rollback Ready**: Keep backup implementations for critical paths

### Testing Strategy:
1. **Performance Regression Tests**
   ```bash
   # Run before and after each phase
   python phase4_benchmark.py
   python tests/test_hash_performance.py
   python tests/test_cache_performance.py
   ```

2. **Memory Profiling**
   ```python
   # Add memory tracking to all major operations
   import psutil
   process = psutil.Process()
   memory_before = process.memory_info().rss
   # ... operation ...
   memory_after = process.memory_info().rss
   ```

3. **Load Testing**
   - Test with projects of varying sizes (10, 100, 1000, 10000 files)
   - Test with different file types and sizes
   - Test concurrent access patterns

### Quality Gates:
- **Phase 1**: Memory usage < 100MB for 1000 files
- **Phase 2**: Change detection < 1ms per file
- **Phase 3**: Search time < 10ms for typical queries
- **Phase 4**: Repeated operations < 1ms
- **Phase 5**: File operations < 0.1ms for cached files

## 📊 Success Metrics

### Performance Targets:
| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Memory Usage (1000 files) | ~200MB | <100MB | 50% reduction |
| File Change Detection | ~2ms | <1ms | 2x faster |
| Search Time (typical) | ~25ms | <10ms | 2.5x faster |
| Repeated Search | ~25ms | <1ms | 25x faster |
| Index Initialization | ~100ms | <50ms | 2x faster |

### Code Quality Targets:
- Maintain current test coverage (>90%)
- Keep functions under 30 lines (Linus principle)
- No new complexity beyond 2 indentation levels
- All optimizations must be backwards compatible

## 🛡️ Risk Mitigation

### Technical Risks:
1. **Memory Leaks**: Implement comprehensive memory monitoring
2. **Thread Safety**: Use proven concurrent patterns only
3. **Cache Invalidation**: Conservative invalidation strategies
4. **Platform Compatibility**: Test on Windows/Linux/macOS

### Rollback Strategy:
- Keep original implementations as fallback options
- Feature flags for new optimizations
- Gradual rollout with monitoring

## 📅 Timeline

**Week 1**: Phase 1 (Memory Management)
**Week 2**: Phase 2 (Fast Change Detection)
**Week 3**: Phase 3 (Parallel Search)
**Week 4**: Phase 4 (Advanced Caching)
**Week 5**: Phase 5 (I/O Optimization) + Integration Testing

**Total Estimated Time**: 5 weeks

## 🎉 Expected Outcomes

After completing all phases:
- **2-3x overall performance improvement** on large projects
- **50% memory usage reduction**
- **Sub-second response times** for all operations
- **Scalable architecture** ready for projects with 10,000+ files
- **Maintained code simplicity** following Linus principles

---

*"Premature optimization is the root of all evil, but when you do optimize, do it right."* - Following Linus Torvalds' approach: measure, optimize the bottlenecks, keep it simple.