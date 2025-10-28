# 符号搜索修复设计文档

## 当前问题分析

### 1. 符号搜索失败问题

**现象**：
- `CodeIndex_search_code(pattern="test_apply_edit", search_type="symbol")` 返回空结果
- 文本搜索能找到该模式，但符号搜索失败

**根因分析**：
```python
# 当前实现问题 (search.py:301-363)
def _search_symbol_with_ripgrep(self, query: SearchQuery) -> List[Dict[str, Any]]:
    # 问题1: 过于复杂的正则模式
    patterns = [
        f"\\bdef\\s+{query.pattern}\\s*\\(",  # 只匹配 Python def
        f"\\bclass\\s+{query.pattern}\\b",   # 只匹配 Python class
        # ... 更多复杂模式
    ]
    
    # 问题2: ripgrep 失败后 fallback 不正确
    if not all_matches:
        # 简单词边界搜索可能仍然找不到
        cmd = ["rg", "--json", "--line-number", "-w", query.pattern]
        # ...
        if not output:
            return self._search_symbol_fallback(query)  # 但这个函数也有问题
```

**具体问题**：
1. `test_apply_edit` 不是真实函数，只是测试字符串中的字面量
2. ripgrep 的复杂模式对简单符号名失效
3. fallback 机制没有正确触发索引搜索

### 2. 索引搜索逻辑问题

**当前实现** (search.py:364-383)：
```python
def _search_symbol_fallback(self, query: SearchQuery) -> List[Dict[str, Any]]:
    pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
    matches = []
    for symbol_name, symbol_info in self.index.symbols.items():
        search_name = symbol_name.lower() if not query.case_sensitive else symbol_name
        if pattern in search_name:  # 问题：使用子串匹配，不是精确匹配
            matches.append({
                "symbol": symbol_name,
                "type": symbol_info.type,
                "file": symbol_info.file,
                "line": symbol_info.line,
            })
    return matches
```

**问题**：
- 使用 `in` 操作符进行子串匹配，应该支持精确匹配和前缀匹配
- 没有考虑符号名的规范化处理

## 修复方案设计

### 1. 新的符号搜索策略

**设计原则**：
- 优先使用最可靠的索引搜索
- ripgrep 作为辅助手段，用于发现未索引的符号
- 简化搜索逻辑，减少复杂性

**新实现**：
```python
def _search_symbol(self, query: SearchQuery) -> List[Dict[str, Any]]:
    """改进的符号搜索 - 优先索引，简化逻辑"""
    
    # 1. 优先使用索引搜索（最可靠）
    index_matches = self._search_symbol_index(query)
    if index_matches:
        return self._limit_results(index_matches, query.limit)
    
    # 2. fallback 到 ripgrep 搜索（发现未索引符号）
    if shutil.which("rg"):
        rg_matches = self._search_symbol_simple_rg(query)
        if rg_matches:
            return self._limit_results(rg_matches, query.limit)
    
    return []

def _search_symbol_index(self, query: SearchQuery) -> List[Dict[str, Any]]:
    """改进的索引搜索 - 支持多种匹配模式"""
    pattern = query.pattern.lower() if not query.case_sensitive else query.pattern
    matches = []
    
    for symbol_name, symbol_info in self.index.symbols.items():
        search_name = symbol_name.lower() if not query.case_sensitive else symbol_name
        
        # 支持多种匹配策略
        if self._symbol_matches(pattern, search_name, query):
            matches.append({
                "symbol": symbol_name,
                "type": symbol_info.type,
                "file": symbol_info.file,
                "line": symbol_info.line,
                "content": self._get_symbol_line_content(symbol_info),
                "language": self._detect_language(symbol_info.file),
            })
    
    return matches

def _symbol_matches(self, pattern: str, symbol_name: str, query: SearchQuery) -> bool:
    """符号匹配逻辑 - 支持精确、前缀、子串匹配"""
    if query.case_sensitive:
        # 精确匹配优先
        if pattern == symbol_name:
            return True
        # 前缀匹配
        if symbol_name.startswith(pattern):
            return True
        # 子串匹配
        if pattern in symbol_name:
            return True
    else:
        # 大小写不敏感的匹配
        pattern_lower = pattern.lower()
        symbol_lower = symbol_name.lower()
        
        if pattern_lower == symbol_lower:
            return True
        if symbol_lower.startswith(pattern_lower):
            return True
        if pattern_lower in symbol_lower:
            return True
    
    return False
```

### 2. 简化的 ripgrep 符号搜索

**设计原则**：
- 使用简单的词边界搜索
- 专注于发现实际的符号定义
- 减少复杂的正则表达式

**新实现**：
```python
def _search_symbol_simple_rg(self, query: SearchQuery) -> List[Dict[str, Any]]:
    """简化的 ripgrep 符号搜索"""
    # 使用简单的词边界搜索，配合符号定义关键词
    patterns = [
        f"\\b(def|class|function|struct|enum|interface)\\s+{re.escape(query.pattern)}\\b",
        f"\\b{re.escape(query.pattern)}\\s*\\(",  # 函数调用模式
        f"\\b(const|let|var)\\s+{re.escape(query.pattern)}\\s*=",  # 变量定义
    ]
    
    all_matches = []
    
    for pattern in patterns:
        cmd = ["rg", "--json", "--line-number"]
        if not query.case_sensitive:
            cmd.append("--ignore-case")
        cmd.extend([pattern, self.index.base_path])
        
        output = self._run_ripgrep_command(cmd)
        if output:
            matches = self._parse_rg_symbol_output(output, query.pattern)
            all_matches.extend(matches)
            
            # 早期退出优化
            if query.limit and len(all_matches) >= query.limit:
                break
    
    return all_matches
```

### 3. 改进的符号类型检测

**当前问题**：
- 符号类型检测过于复杂，容易误判
- 没有考虑语言特定的上下文

**改进方案**：
```python
def _detect_symbol_type_improved(self, line_content: str, symbol_name: str, file_path: str) -> str:
    """改进的符号类型检测"""
    line = line_content.strip()
    language = self._detect_language(file_path)
    
    # 语言特定的检测
    if language == "python":
        return self._detect_python_symbol_type(line, symbol_name)
    elif language in ["javascript", "typescript"]:
        return self._detect_js_symbol_type(line, symbol_name)
    elif language in ["java", "c", "cpp", "rust", "go"]:
        return self._detect_c_family_symbol_type(line, symbol_name)
    else:
        return self._detect_generic_symbol_type(line, symbol_name)

def _detect_python_symbol_type(self, line: str, symbol_name: str) -> str:
    """Python 符号类型检测"""
    if line.startswith("def " + symbol_name + "("):
        return "function"
    elif line.startswith("class " + symbol_name):
        return "class"
    elif line.startswith("async def " + symbol_name + "("):
        return "function"
    elif any(line.startswith(kw) for kw in ["import ", "from "]) and symbol_name in line:
        return "import"
    else:
        return "variable"

def _detect_js_symbol_type(self, line: str, symbol_name: str) -> str:
    """JavaScript/TypeScript 符号类型检测"""
    if line.startswith("function " + symbol_name + "("):
        return "function"
    elif line.startswith("const " + symbol_name) and "=" in line:
        return "variable"
    elif line.startswith("let " + symbol_name) and "=" in line:
        return "variable"
    elif line.startswith("var " + symbol_name) and "=" in line:
        return "variable"
    elif line.startswith("class " + symbol_name):
        return "class"
    else:
        return "unknown"
```

### 4. 增强的错误处理和日志

**设计原则**：
- 提供详细的调试信息
- 区分不同类型的失败
- 支持渐进式降级

**实现**：
```python
def _search_symbol_with_logging(self, query: SearchQuery) -> List[Dict[str, Any]]:
    """带详细日志的符号搜索"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug(f"Starting symbol search: pattern='{query.pattern}', type='{query.type}'")
    
    # 1. 索引搜索
    try:
        index_matches = self._search_symbol_index(query)
        logger.debug(f"Index search found {len(index_matches)} matches")
        if index_matches:
            return self._limit_results(index_matches, query.limit)
    except Exception as e:
        logger.warning(f"Index search failed: {e}")
    
    # 2. ripgrep 搜索
    if shutil.which("rg"):
        try:
            rg_matches = self._search_symbol_simple_rg(query)
            logger.debug(f"Ripgrep search found {len(rg_matches)} matches")
            if rg_matches:
                return self._limit_results(rg_matches, query.limit)
        except Exception as e:
            logger.warning(f"Ripgrep search failed: {e}")
    
    logger.debug(f"No symbol matches found for pattern: '{query.pattern}'")
    return []
```

## 测试策略

### 1. 单元测试

```python
def test_symbol_search_exact_match(self, search_engine):
    """测试精确匹配"""
    # 使用实际存在的符号
    query = SearchQuery(pattern="search_code", type="symbol", case_sensitive=True)
    result = search_engine.search(query)
    
    assert result.total_count > 0, "应该找到精确匹配的符号"
    exact_matches = [m for m in result.matches if m["symbol"] == "search_code"]
    assert len(exact_matches) > 0, "应该包含精确匹配的结果"

def test_symbol_search_prefix_match(self, search_engine):
    """测试前缀匹配"""
    query = SearchQuery(pattern="search", type="symbol", case_sensitive=True)
    result = search_engine.search(query)
    
    if result.total_count > 0:
        prefix_matches = [m for m in result.matches if m["symbol"].startswith("search")]
        assert len(prefix_matches) > 0, "应该找到前缀匹配的符号"

def test_symbol_search_case_insensitive(self, search_engine):
    """测试大小写不敏感搜索"""
    query = SearchQuery(pattern="SEARCH_CODE", type="symbol", case_sensitive=False)
    result = search_engine.search(query)
    
    if result.total_count > 0:
        # 应该找到大小写不敏感的匹配
        assert any("search" in m["symbol"].lower() for m in result.matches)
```

### 2. 集成测试

```python
def test_symbol_search_with_real_symbols(self, search_engine):
    """使用真实符号的集成测试"""
    # 获取索引中的实际符号
    if search_engine.index.symbols:
        test_symbol = list(search_engine.index.symbols.keys())[0]
        
        query = SearchQuery(pattern=test_symbol, type="symbol")
        result = search_engine.search(query)
        
        assert result.total_count > 0, f"应该找到实际存在的符号: {test_symbol}"
        assert any(m["symbol"] == test_symbol for m in result.matches), "结果应包含精确匹配"
```

## 性能考虑

### 1. 优化策略

- **早期退出**：找到足够结果后立即停止搜索
- **缓存结果**：缓存常用符号的搜索结果
- **并行处理**：对于大型项目，考虑并行搜索

### 2. 性能指标

- 符号搜索响应时间 < 1秒（1000个符号以内）
- 内存使用增长 < 10%
- CPU 使用率保持在合理范围

## 向后兼容性

- 保持现有 API 接口不变
- 新增的日志功能不影响现有功能
- 错误处理改进只增强，不破坏现有行为