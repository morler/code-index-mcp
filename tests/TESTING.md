# Testing Guide for Code Index MCP

遵循Linus的原则："好的程序员关心数据结构。"

## 测试架构概览

### 测试类型

1. **单元测试** (`@pytest.mark.unit`)
   - 测试单个服务和工具类
   - 使用mock隔离依赖
   - 快速执行，专注业务逻辑

2. **集成测试** (`@pytest.mark.integration`)
   - 测试端到端工作流程
   - 使用真实文件系统和临时目录
   - 验证组件间协作

3. **慢速测试** (`@pytest.mark.slow`)
   - 性能和扩展性测试
   - 大规模数据处理
   - 可选择性跳过

## 测试文件结构

```
tests/
├── conftest.py                    # 全局fixtures和配置
├── test_core_services.py          # 核心服务单元测试
├── test_core_functionality.py     # 基础功能集成测试
├── test_index_integration.py      # 索引构建集成测试
├── test_search_integration.py     # 搜索功能集成测试
└── test_search_basics_simple.py   # 简化的搜索基础测试
```

## 运行测试

### 基本命令

```bash
# 运行所有测试
make test

# 只运行单元测试
make test-unit

# 只运行集成测试
make test-integration

# 运行带覆盖率的测试
make test-coverage

# 跳过慢速测试
make test-fast
```

### 高级用法

```bash
# 使用pytest直接运行
uv run python -m pytest tests/ -v

# 运行特定文件
uv run python -m pytest tests/test_core_services.py -v

# 运行特定测试方法
uv run python -m pytest tests/test_core_services.py::TestBaseService::test_base_service_initialization -v

# 显示详细输出
uv run python -m pytest tests/ -v -s

# 只运行失败的测试
uv run python -m pytest tests/ --lf
```

## 当前测试统计

### 覆盖率报告
- **总体覆盖率**: 36%
- **测试通过率**: 97% (29/30)
- **核心服务覆盖**: BaseService (78%), SearchService (55%), FileDiscoveryService (92%)

### 测试分布
- **单元测试**: 24个
- **集成测试**: 6个
- **总测试数**: 30个

## 测试最佳实践

### 1. 遵循Linus原则

"好的测试关心数据流，而不是代码覆盖。"

```python
def test_data_flow_integrity(self):
    """测试数据流完整性而非代码行数。"""
    # 输入 -> 处理 -> 输出
    input_data = create_test_data()
    result = process_data(input_data)
    assert_data_integrity(result)
```

### 2. 简洁直接

"如果测试需要3层以上的嵌套，就重新设计。"

```python
# ✅ 好的测试
def test_search_finds_function(self):
    results = search_service.search("function_name")
    assert "function_name" in results

# ❌ 复杂的测试
def test_complex_nested_scenario(self):
    if condition1:
        if condition2:
            if condition3:
                # 太复杂了！
```

### 3. 专注边界条件

```python
def test_empty_input(self):
    """空输入应该优雅处理。"""

def test_large_input(self):
    """大输入应该不崩溃。"""

def test_invalid_input(self):
    """无效输入应该报告清晰错误。"""
```

## 添加新测试

### 1. 选择测试类型

- **单一功能** → 单元测试
- **多组件交互** → 集成测试
- **性能验证** → 慢速测试

### 2. 使用适当的fixtures

```python
def test_with_temp_project(self, minimal_python_project):
    """使用预定义的项目fixture。"""

def test_with_mock_service(self, mock_mcp_context):
    """使用mock context进行单元测试。"""
```

### 3. 清晰的断言

```python
# ✅ 具体断言
assert result["status"] == "success"
assert len(result["files"]) == 2

# ❌ 模糊断言
assert result  # 不够具体
assert "something" in str(result)  # 容易误判
```

## CI/CD集成

### GitHub Actions

测试在以下情况自动运行：
- 推送到main/master分支
- 创建Pull Request
- Python 3.10、3.11、3.12多版本测试

### 本地预提交检查

```bash
# 运行完整的质量检查
make quality

# 包含类型检查和测试
make ci
```

## 故障排除

### 常见问题

1. **导入错误**
   ```bash
   # 确保在项目根目录运行
   cd /path/to/code-index-mcp
   uv run python -m pytest
   ```

2. **Mock错误**
   ```python
   # 确保正确设置Mock返回值
   mock_method.return_value = expected_value
   # 而不是
   mock_method = expected_value
   ```

3. **临时文件清理**
   ```python
   # 使用context manager确保清理
   with tempfile.TemporaryDirectory() as temp_dir:
       # 测试代码
       pass  # 自动清理
   ```

### 调试技巧

```bash
# 显示详细输出
pytest -v -s

# 在第一个失败处停止
pytest -x

# 显示本地变量
pytest --tb=long

# 进入pdb调试器
pytest --pdb
```

## 性能考虑

### 测试执行时间

- **单元测试**: < 0.1秒/个
- **集成测试**: < 5秒/个
- **慢速测试**: < 30秒/个

### 优化建议

1. **并行执行**
   ```bash
   pytest -n auto  # 需要pytest-xdist
   ```

2. **选择性运行**
   ```bash
   pytest -m "not slow"  # 跳过慢速测试
   ```

3. **缓存fixtures**
   ```python
   @pytest.fixture(scope="session")
   def expensive_fixture():
       # 会话级别缓存
   ```

## 扩展测试套件

随着项目发展，考虑添加：

1. **性能回归测试**
2. **内存泄漏检测**
3. **并发测试**
4. **模糊测试(Fuzzing)**
5. **属性测试(Property-based testing)**

---

*"Never break userspace" - Linus Torvalds*

测试的目标是确保用户体验永不破坏。每个测试都应该从用户角度思考：这个变更会影响用户的工作流程吗？