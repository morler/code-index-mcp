# 修复符号检索功能问题变更提案

## 问题概述

当前代码检索功能存在两个关键问题：
1. **符号搜索失败**：符号搜索返回空结果，无法找到已索引的符号
2. **符号体提取异常**：符号体提取只返回文档字符串，无法正确提取完整函数体

这些问题影响了代码分析工具的核心功能，需要立即修复。

## 变更目标

1. **修复符号搜索功能**：确保符号搜索能正确返回已索引的符号
2. **修复符号体提取功能**：确保能正确提取符号的完整语法体
3. **改进错误处理**：增强边界情况处理和错误提示
4. **修正测试用例**：使用实际存在的符号进行测试

## 技术方案

### 1. 符号搜索修复方案

**问题根因**：
- ripgrep 符号搜索模式过于复杂，对简单符号名失效
- fallback 机制在 ripgrep 失败时没有正确触发
- 索引搜索逻辑存在缺陷

**解决方案**：
```python
# 简化符号搜索策略，优先使用索引搜索
def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
    # 1. 优先使用索引搜索（最可靠）
    index_matches = self._search_symbol_index(query)
    if index_matches:
        return index_matches[:query.limit] if query.limit else index_matches
    
    # 2. fallback 到简单 ripgrep 搜索
    if shutil.which("rg"):
        rg_matches = self._search_symbol_simple_rg(query)
        if rg_matches:
            return rg_matches[:query.limit] if query.limit else rg_matches
    
    return []
```

### 2. 符号体提取修复方案

**问题根因**：
- 符号存在性验证不足
- 语法体边界检测算法错误
- 错误处理机制缺失

**解决方案**：
```python
def tool_get_symbol_body(symbol_name: str, file_path: Optional[str] = None, 
                         language: str = "auto", show_line_numbers: bool = False) -> Dict[str, Any]:
    # 1. 严格的符号存在性验证
    symbol_info = index.symbols.get(symbol_name)
    if not symbol_info:
        return {"success": False, "error": f"Symbol not found: {symbol_name}"}
    
    # 2. 验证文件存在性
    target_file = file_path or symbol_info.file
    full_path = _resolve_file_path(index.base_path, target_file)
    if not full_path.exists():
        return {"success": False, "error": f"File not found: {target_file}"}
    
    # 3. 改进的语法体边界检测
    try:
        lines = full_path.read_text(encoding="utf-8", errors="ignore").split("\n")
        end_line = _detect_syntax_body_end_improved(lines, symbol_info.line, language)
        
        # 4. 验证边界有效性
        if end_line <= symbol_info.line:
            return {"success": False, "error": f"Invalid symbol boundaries for: {symbol_name}"}
        
        # 5. 提取并验证内容
        body_lines = lines[symbol_info.line-1:end_line]
        if not body_lines or len(body_lines) == 1:
            return {"success": False, "error": f"Empty or invalid symbol body: {symbol_name}"}
        
        return {"success": True, ...}
    except Exception as e:
        return _create_error_response(e, f"Failed to extract symbol body: {symbol_name}")
```

### 3. 测试用例修复方案

**问题根因**：
- 使用不存在的符号 `test_apply_edit` 进行测试
- 测试逻辑与实际功能不匹配

**解决方案**：
```python
# 使用实际存在的符号进行测试
def test_function_detection(self, search_engine):
    """测试函数类型检测 - 使用实际存在的符号"""
    # 使用项目中实际存在的函数
    query = SearchQuery(pattern="search_code", type="symbol", limit=5)
    result = search_engine.search(query)
    
    if result.total_count > 0:
        function_matches = [m for m in result.matches if m.get("type") == "function"]
        assert len(function_matches) > 0, "应该检测到函数类型"
```

## 实施计划

### Phase 1: 核心修复（高优先级）
1. **修复符号搜索逻辑** (`src/core/search.py`)
   - 简化搜索策略，优先使用索引搜索
   - 改进 fallback 机制
   - 增强错误处理

2. **修复符号体提取逻辑** (`src/core/mcp_tools.py`)
   - 增强符号存在性验证
   - 改进语法体边界检测算法
   - 完善错误处理机制

### Phase 2: 测试修复（中优先级）
1. **修正测试用例** (`tests/test_symbol_search_fix.py`)
   - 使用实际存在的符号
   - 调整测试断言逻辑
   - 增加边界情况测试

2. **增加集成测试**
   - 测试符号搜索与体提取的完整流程
   - 验证错误处理机制

### Phase 3: 验证和优化（低优先级）
1. **性能验证**
   - 确保修复不影响搜索性能
   - 验证内存使用情况

2. **文档更新**
   - 更新 API 文档
   - 添加使用示例

## 风险评估

**低风险变更**：
- 符号搜索逻辑优化：主要是算法改进，不改变接口
- 错误处理增强：只增加错误检查，不影响正常流程

**中等风险变更**：
- 符号体提取算法：需要仔细测试边界情况
- 测试用例修改：需要确保测试覆盖率

**缓解措施**：
- 分阶段实施，每个阶段都进行充分测试
- 保留原有逻辑作为备份
- 增加详细的日志记录用于调试

## 验收标准

1. **功能验收**：
   - 符号搜索能返回已索引的符号
   - 符号体能正确提取完整语法体
   - 错误情况有明确的错误提示

2. **性能验收**：
   - 符号搜索响应时间 < 1秒
   - 符号体提取响应时间 < 0.5秒

3. **测试验收**：
   - 所有相关测试用例通过
   - 测试覆盖率保持或提升

## 影响范围

**直接影响**：
- `src/core/search.py` - 符号搜索逻辑
- `src/core/mcp_tools.py` - 符号体提取逻辑
- `tests/test_symbol_search_fix.py` - 测试用例

**间接影响**：
- MCP 服务器接口（通过工具函数）
- 依赖符号检索的其他功能

**无影响**：
- 文本搜索功能
- 文件查找功能
- 索引构建功能

## 时间估算

- **Phase 1**: 2-3 天（核心修复）
- **Phase 2**: 1-2 天（测试修复）
- **Phase 3**: 1 天（验证优化）

**总计**: 4-6 天

## 后续计划

1. **监控**：部署后监控符号检索功能的稳定性
2. **反馈**：收集用户反馈，持续优化
3. **扩展**：基于修复后的基础功能，开发更高级的代码分析功能