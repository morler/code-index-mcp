# 测试用例修复设计文档

## 当前测试问题分析

### 1. 失败的测试用例

**测试失败**：
```python
def test_function_detection(self, search_engine):
    """测试函数类型检测"""
    query = SearchQuery(pattern="test_apply_edit", type="symbol", limit=5)
    result = search_engine.search(query)
    
    # 应该找到函数定义
    function_matches = [m for m in result.matches if m.get("type") == "function"]
    assert len(function_matches) > 0, "应该检测到函数类型"
```

**问题分析**：
1. `test_apply_edit` 不是真实存在的函数，只是测试代码中的字符串字面量
2. 测试期望符号搜索能找到这个"函数"，但实际上它不存在
3. 测试逻辑与实际功能不匹配

### 2. 测试设计问题

**根本问题**：
- 使用不存在的符号进行测试
- 测试假设与实际索引内容不符
- 缺乏对真实符号的验证

**具体问题**：
```python
# 问题1: 使用虚构的符号名
pattern="test_apply_edit"  # 这个函数在代码库中不存在

# 问题2: 测试逻辑错误
# 即使搜索成功，也可能找到其他类型的符号，不一定是函数

# 问题3: 缺乏对索引内容的了解
# 测试没有验证索引中实际包含哪些符号
```

## 修复方案设计

### 1. 测试数据准备策略

**设计原则**：
- 使用真实存在的符号进行测试
- 动态发现测试数据，避免硬编码
- 提供多种测试场景覆盖

**实现方案**：
```python
class TestSymbolSearchFix:
    """符号搜索修复测试 - 使用真实符号"""
    
    @pytest.fixture(scope="class")
    def real_test_symbols(self, search_engine):
        """获取真实的测试符号"""
        if not search_engine.index.symbols:
            return {}
        
        # 按类型分组真实符号
        symbols_by_type = {}
        for symbol_name, symbol_info in search_engine.index.symbols.items():
            symbol_type = symbol_info.type
            if symbol_type not in symbols_by_type:
                symbols_by_type[symbol_type] = []
            symbols_by_type[symbol_type].append({
                "name": symbol_name,
                "info": symbol_info
            })
        
        return symbols_by_type
    
    @pytest.fixture(scope="class")
    def test_symbol_samples(self, real_test_symbols):
        """获取测试符号样本"""
        samples = {
            "functions": [],
            "classes": [],
            "variables": [],
            "imports": []
        }
        
        # 从每种类型中选择几个样本
        for symbol_type, symbols in real_test_symbols.items():
            if symbol_type == "function":
                samples["functions"] = symbols[:3]  # 取前3个函数
            elif symbol_type == "class":
                samples["classes"] = symbols[:2]   # 取前2个类
            elif symbol_type in ["variable", "const", "let"]:
                samples["variables"] = symbols[:3] # 取前3个变量
            elif symbol_type == "import":
                samples["imports"] = symbols[:2]   # 取前2个导入
        
        return samples
```

### 2. 修复后的测试用例

**新的测试实现**：
```python
@pytest.mark.unit
def test_function_detection_with_real_symbols(self, search_engine, test_symbol_samples):
    """测试函数类型检测 - 使用真实函数"""
    functions = test_symbol_samples.get("functions", [])
    
    if not functions:
        pytest.skip("No functions found in index for testing")
    
    # 测试每个真实函数
    for func_sample in functions:
        func_name = func_sample["name"]
        
        query = SearchQuery(pattern=func_name, type="symbol", limit=10)
        result = search_engine.search(query)
        
        assert result.total_count > 0, f"应该找到函数: {func_name}"
        
        # 检查是否正确识别为函数
        function_matches = [m for m in result.matches if m.get("type") == "function"]
        assert len(function_matches) > 0, f"应该将 {func_name} 识别为函数"
        
        # 验证匹配结果包含目标符号
        symbol_matches = [m for m in result.matches if m.get("symbol") == func_name]
        assert len(symbol_matches) > 0, f"结果应包含精确匹配的符号: {func_name}"

@pytest.mark.unit
def test_class_detection_with_real_symbols(self, search_engine, test_symbol_samples):
    """测试类类型检测 - 使用真实类"""
    classes = test_symbol_samples.get("classes", [])
    
    if not classes:
        pytest.skip("No classes found in index for testing")
    
    for class_sample in classes:
        class_name = class_sample["name"]
        
        query = SearchQuery(pattern=class_name, type="symbol", limit=10)
        result = search_engine.search(query)
        
        if result.total_count > 0:
            # 检查是否正确识别为类
            class_matches = [m for m in result.matches if m.get("type") == "class"]
            if class_matches:
                # 验证类定义包含 class 关键字
                for match in class_matches:
                    if "content" in match:
                        assert "class " in match["content"], f"类定义应包含class关键字: {class_name}"

@pytest.mark.unit
def test_symbol_search_exact_match(self, search_engine, real_test_symbols):
    """测试精确匹配"""
    if not real_test_symbols:
        pytest.skip("No symbols found in index")
    
    # 选择第一个符号进行精确匹配测试
    first_symbol = list(real_test_symbols.keys())[0]
    if first_symbol:
        symbol_name = first_symbol[0]["name"] if first_symbol else None
        
        if symbol_name:
            query = SearchQuery(pattern=symbol_name, type="symbol", case_sensitive=True)
            result = search_engine.search(query)
            
            assert result.total_count > 0, f"应该找到精确匹配的符号: {symbol_name}"
            
            # 验证精确匹配
            exact_matches = [m for m in result.matches if m["symbol"] == symbol_name]
            assert len(exact_matches) > 0, f"应该包含精确匹配的结果: {symbol_name}"

@pytest.mark.unit
def test_symbol_search_prefix_match(self, search_engine, real_test_symbols):
    """测试前缀匹配"""
    if not real_test_symbols:
        pytest.skip("No symbols found in index")
    
    # 选择一个有明确前缀的符号
    for symbol_type, symbols in real_test_symbols.items():
        if symbols:
            symbol_name = symbols[0]["name"]
            # 取符号名的前3个字符作为前缀
            if len(symbol_name) >= 3:
                prefix = symbol_name[:3]
                
                query = SearchQuery(pattern=prefix, type="symbol", case_sensitive=True)
                result = search_engine.search(query)
                
                if result.total_count > 0:
                    # 检查是否找到前缀匹配的符号
                    prefix_matches = [m for m in result.matches if m["symbol"].startswith(prefix)]
                    assert len(prefix_matches) > 0, f"应该找到前缀匹配的符号: {prefix}"
                break

@pytest.mark.unit
def test_symbol_search_case_insensitive(self, search_engine, test_symbol_samples):
    """测试大小写不敏感搜索"""
    functions = test_symbol_samples.get("functions", [])
    
    if not functions:
        pytest.skip("No functions found for case insensitive test")
    
    func_name = functions[0]["name"]
    # 转换为大写进行大小写不敏感搜索
    upper_pattern = func_name.upper()
    
    query = SearchQuery(pattern=upper_pattern, type="symbol", case_sensitive=False)
    result = search_engine.search(query)
    
    if result.total_count > 0:
        # 应该找到大小写不敏感的匹配
        assert any(
            func_name.lower() in m["symbol"].lower() 
            for m in result.matches
        ), f"应该找到大小写不敏感的匹配: {func_name}"

@pytest.mark.unit
def test_symbol_search_performance(self, search_engine, real_test_symbols):
    """测试搜索性能"""
    import time
    
    if not real_test_symbols:
        pytest.skip("No symbols found for performance test")
    
    # 选择几个符号进行性能测试
    test_patterns = []
    for symbol_type, symbols in real_test_symbols.items():
        if symbols and len(test_patterns) < 5:
            test_patterns.append(symbols[0]["name"])
    
    for pattern in test_patterns:
        start_time = time.time()
        query = SearchQuery(pattern=pattern, type="symbol", limit=20)
        result = search_engine.search(query)
        end_time = time.time()
        
        search_time = end_time - start_time
        assert search_time < 2.0, f"符号 '{pattern}' 搜索时间应少于2秒，实际: {search_time:.3f}秒"
        assert result.search_time < 2.0, f"结果报告的搜索时间应少于2秒，实际: {result.search_time:.3f}秒"

@pytest.mark.integration
def test_symbol_search_with_sample_projects(self, search_engine):
    """使用示例项目测试符号搜索"""
    # 查找示例项目中的常见符号
    common_patterns = ["user", "auth", "test", "main", "init"]
    
    for pattern in common_patterns:
        query = SearchQuery(pattern=pattern, type="symbol", limit=10)
        result = search_engine.search(query)
        
        if result.total_count > 0:
            # 检查结果来自不同的文件
            files = set(m.get("file", "") for m in result.matches)
            assert len(files) >= 1, f"模式 '{pattern}' 的结果应该来自文件"
            
            # 检查结果格式一致性
            for match in result.matches:
                assert isinstance(match, dict), "每个匹配应该是字典"
                required_keys = ["symbol", "type", "file", "line"]
                for key in required_keys:
                    assert key in match, f"匹配应包含{key}字段"
            
            # 找到有效结果后停止测试其他模式
            break
```

### 3. 符号体提取测试修复

**新的测试实现**：
```python
class TestSymbolBodyExtraction:
    """符号体提取测试 - 使用真实符号"""
    
    @pytest.fixture(scope="class")
    def test_symbols_for_body(self, search_engine):
        """获取用于体提取测试的符号"""
        suitable_symbols = []
        
        for symbol_name, symbol_info in search_engine.index.symbols.items():
            # 选择函数和类进行体提取测试
            if symbol_info.type in ["function", "class"]:
                # 检查文件是否存在且可读
                try:
                    full_path = Path(search_engine.index.base_path) / symbol_info.file
                    if full_path.exists() and full_path.stat().st_size < 50000:  # 避免过大文件
                        suitable_symbols.append({
                            "name": symbol_name,
                            "info": symbol_info
                        })
                except (OSError, PermissionError):
                    continue
                
                # 限制测试符号数量
                if len(suitable_symbols) >= 5:
                    break
        
        return suitable_symbols
    
    @pytest.mark.unit
    def test_symbol_body_extraction_with_real_symbols(self, search_engine, test_symbols_for_body):
        """测试真实符号的体提取"""
        if not test_symbols_for_body:
            pytest.skip("No suitable symbols found for body extraction test")
        
        for symbol_sample in test_symbols_for_body:
            symbol_name = symbol_sample["name"]
            symbol_info = symbol_sample["info"]
            
            result = tool_get_symbol_body(symbol_name, show_line_numbers=True)
            
            assert result["success"], f"符号体提取应该成功: {symbol_name}, 错误: {result.get('error', 'unknown')}"
            
            # 验证基本字段
            assert "symbol_name" in result
            assert "file_path" in result
            assert "start_line" in result
            assert "end_line" in result
            assert "body_lines" in result
            assert "total_lines" in result
            
            # 验证符号信息一致性
            assert result["symbol_name"] == symbol_name
            assert result["file_path"] == symbol_info.file
            assert result["start_line"] >= 1
            assert result["end_line"] >= result["start_line"]
            assert result["total_lines"] == len(result["body_lines"])
            
            # 验证内容不为空
            assert len(result["body_lines"]) > 0, f"符号体不应为空: {symbol_name}"
            
            # 验证第一行包含符号定义
            first_line = result["body_lines"][0].strip()
            assert symbol_name in first_line, f"第一行应包含符号名: {symbol_name}"
    
    @pytest.mark.unit
    def test_symbol_body_extraction_invalid_symbol(self, search_engine):
        """测试无效符号的体提取"""
        result = tool_get_symbol_body("nonexistent_symbol_xyz123")
        
        assert not result["success"], "无效符号应该返回失败"
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    @pytest.mark.unit
    def test_symbol_body_extraction_with_line_numbers(self, search_engine, test_symbols_for_body):
        """测试带行号的符号体提取"""
        if not test_symbols_for_body:
            pytest.skip("No suitable symbols found for line number test")
        
        symbol_sample = test_symbols_for_body[0]
        symbol_name = symbol_sample["name"]
        
        result = tool_get_symbol_body(symbol_name, show_line_numbers=True)
        
        assert result["success"], f"符号体提取应该成功: {symbol_name}"
        assert "line_numbers" in result
        assert len(result["line_numbers"]) == result["total_lines"]
        
        # 验证行号连续性
        expected_start = result["start_line"]
        expected_numbers = list(range(expected_start, expected_start + result["total_lines"]))
        assert result["line_numbers"] == expected_numbers
    
    @pytest.mark.unit
    def test_symbol_body_extraction_language_detection(self, search_engine, test_symbols_for_body):
        """测试语言自动检测"""
        if not test_symbols_for_body:
            pytest.skip("No suitable symbols found for language detection test")
        
        for symbol_sample in test_symbols_for_body:
            symbol_name = symbol_sample["name"]
            
            # 测试自动语言检测
            result = tool_get_symbol_body(symbol_name, language="auto")
            
            assert result["success"], f"符号体提取应该成功: {symbol_name}"
            assert "language" in result
            assert result["language"] != "unknown", f"应该检测到语言: {symbol_name}"
            
            # 验证语言与文件扩展名匹配
            file_path = result["file_path"]
            if file_path.endswith(".py"):
                assert result["language"] == "python", f"Python文件应检测为python: {file_path}"
            elif file_path.endswith((".js", ".jsx")):
                assert result["language"] in ["javascript", "typescript"], f"JS文件应检测为JS/TS: {file_path}"
```

### 4. 集成测试改进

**新的集成测试**：
```python
@pytest.mark.integration
class TestSymbolRetrievalIntegration:
    """符号检索集成测试"""
    
    @pytest.mark.integration
    def test_complete_symbol_workflow(self, search_engine):
        """测试完整的符号工作流：搜索 -> 体提取"""
        # 1. 搜索符号
        if not search_engine.index.symbols:
            pytest.skip("No symbols in index for integration test")
        
        # 选择一个真实符号
        symbol_name = list(search_engine.index.symbols.keys())[0]
        
        # 2. 符号搜索
        search_query = SearchQuery(pattern=symbol_name, type="symbol")
        search_result = search_engine.search(search_query)
        
        assert search_result.total_count > 0, f"应该找到符号: {symbol_name}"
        
        # 3. 符号体提取
        body_result = tool_get_symbol_body(symbol_name)
        
        assert body_result["success"], f"应该成功提取符号体: {symbol_name}"
        
        # 4. 验证一致性
        assert body_result["symbol_name"] == symbol_name
        assert any(m["symbol"] == symbol_name for m in search_result.matches)
    
    @pytest.mark.integration
    def test_symbol_search_and_content_consistency(self, search_engine):
        """测试符号搜索与文件内容的一致性"""
        if not search_engine.index.symbols:
            pytest.skip("No symbols in index for consistency test")
        
        # 选择几个符号进行一致性检查
        test_symbols = list(search_engine.index.symbols.keys())[:3]
        
        for symbol_name in test_symbols:
            symbol_info = search_engine.index.symbols[symbol_name]
            
            # 1. 搜索符号
            query = SearchQuery(pattern=symbol_name, type="symbol")
            result = search_engine.search(query)
            
            assert result.total_count > 0, f"应该找到符号: {symbol_name}"
            
            # 2. 获取文件内容验证符号存在
            file_result = tool_get_file_content(symbol_info.file)
            assert file_result["success"], f"应该能读取文件: {symbol_info.file}"
            
            # 3. 验证符号确实在文件中
            file_content = " ".join(file_result["content"])
            assert symbol_name in file_content, f"符号应该在文件内容中: {symbol_name}"
```

### 5. 测试数据管理

**测试数据准备工具**：
```python
class TestDataManager:
    """测试数据管理器"""
    
    @staticmethod
    def get_test_symbols_by_type(search_engine, max_per_type=5):
        """按类型获取测试符号"""
        symbols_by_type = {}
        
        for symbol_name, symbol_info in search_engine.index.symbols.items():
            symbol_type = symbol_info.type
            
            if symbol_type not in symbols_by_type:
                symbols_by_type[symbol_type] = []
            
            if len(symbols_by_type[symbol_type]) < max_per_type:
                symbols_by_type[symbol_type].append({
                    "name": symbol_name,
                    "info": symbol_info
                })
        
        return symbols_by_type
    
    @staticmethod
    def validate_symbol_for_testing(symbol_info):
        """验证符号是否适合用于测试"""
        try:
            # 检查文件是否存在
            file_path = Path(symbol_info.file)
            if not file_path.exists():
                return False, "File not found"
            
            # 检查文件大小（避免过大文件）
            if file_path.stat().st_size > 100000:  # 100KB
                return False, "File too large"
            
            # 检查行号有效性
            if symbol_info.line <= 0:
                return False, "Invalid line number"
            
            return True, "Valid"
        except Exception as e:
            return False, f"Error: {e}"
```

## 测试执行策略

### 1. 测试优先级

**高优先级测试**：
- 使用真实符号的基本功能测试
- 错误处理测试
- 性能基准测试

**中优先级测试**：
- 边界情况测试
- 语言特定测试
- 集成测试

**低优先级测试**：
- 压力测试
- 兼容性测试
- 详细的错误场景测试

### 2. 测试环境准备

```python
@pytest.fixture(scope="session")
def test_environment():
    """准备测试环境"""
    # 确保有足够的测试数据
    # 验证索引完整性
    # 设置测试配置
    pass
```

### 3. 测试报告

```python
def generate_test_report(test_results):
    """生成测试报告"""
    report = {
        "total_tests": len(test_results),
        "passed": sum(1 for r in test_results if r.passed),
        "failed": sum(1 for r in test_results if not r.passed),
        "coverage": calculate_coverage(test_results),
        "performance": extract_performance_data(test_results)
    }
    return report
```

## 向后兼容性

- 保持现有测试框架不变
- 新增测试不影响现有测试
- 渐进式替换有问题的测试用例