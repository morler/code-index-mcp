# 符号体提取修复设计文档

## 当前问题分析

### 1. 符号体提取异常现象

**测试结果**：
```json
{
  "success": true,
  "symbol_name": "search_code",
  "symbol_type": "function",
  "file_path": "D:\\Code\\MyProject\\MCP\\code-index-mcp\\src\\code_index_mcp\\server_unified.py",
  "language": "python",
  "start_line": 1,
  "end_line": 1,
  "body_lines": ["\"\"\""],
  "signature": null,
  "total_lines": 1
}
```

**问题分析**：
1. `start_line: 1, end_line: 1` - 边界检测完全错误
2. `body_lines: ["\"\"\""]` - 只返回了文档字符串
3. `signature: null` - 没有提取到函数签名

### 2. 根因分析

**当前实现问题** (mcp_tools.py:386-452)：

```python
def tool_get_symbol_body(symbol_name: str, file_path: Optional[str] = None,
                         language: str = "auto", show_line_numbers: bool = False) -> Dict[str, Any]:
    # 问题1: 符号查找逻辑错误
    symbol_info = index.symbols.get(symbol_name)  # 可能为 None
    if not symbol_info:
        return {"success": False, "error": f"Symbol not found: {symbol_name}"}
    
    # 问题2: 使用了错误的文件路径
    target_file = file_path or symbol_info.file
    start_line = symbol_info.line  # 这可能是错误的行号
    
    # 问题3: 边界检测算法有缺陷
    end_line = _detect_syntax_body_end(lines, start_line, language)
    
    # 问题4: 没有验证结果的有效性
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    body_lines = lines[start_idx:end_idx]  # 可能是空或错误的内容
```

**边界检测算法问题** (mcp_tools.py:290-383)：

```python
def _detect_syntax_body_end(lines: List[str], start_line: int, language: str) -> int:
    # 问题1: 没有验证 start_line 的有效性
    if start_line >= len(lines):
        return start_line  # 错误的返回值
    
    # 问题2: Python 缩进检测逻辑有缺陷
    def _detect_python_body_end(lines: List[str], start_idx: int) -> int:
        start_line = lines[start_idx].rstrip()
        if not start_line:
            return start_idx + 1  # 可能返回错误边界
        
        # 问题3: 缩进计算可能不准确
        start_indent = len(start_line) - len(start_line.lstrip())
        
        # 问题4: 没有考虑装饰器、多行定义等特殊情况
        for i in range(start_idx + 1, len(lines)):
            line = lines[i].rstrip()
            if not line:
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= start_indent:
                return i  # 可能过早返回
```

### 3. 具体问题场景

**场景1：符号行号错误**
- 索引中存储的行号可能指向文档字符串而非函数定义
- 对于 Python 函数，可能指向装饰器而非 `def` 行

**场景2：边界检测失败**
- 多行函数定义处理不当
- 嵌套函数或类的边界检测错误
- 异常缩进情况处理失败

**场景3：内容提取错误**
- 提取的内容不包含完整的函数体
- 没有正确处理多行字符串
- 签名提取失败

## 修复方案设计

### 1. 改进的符号查找和验证

**设计原则**：
- 严格验证符号存在性
- 验证文件和行号的有效性
- 提供详细的错误信息

**新实现**：
```python
def tool_get_symbol_body(symbol_name: str, file_path: Optional[str] = None,
                         language: str = "auto", show_line_numbers: bool = False) -> Dict[str, Any]:
    """改进的符号体提取 - 严格验证，智能边界检测"""
    index = get_index()
    
    # 1. 严格的符号存在性验证
    symbol_info = index.symbols.get(symbol_name)
    if not symbol_info:
        # 提供相似符号建议
        similar_symbols = _find_similar_symbols(symbol_name, list(index.symbols.keys()))
        suggestion = f" Did you mean: {', '.join(similar_symbols[:3])}?" if similar_symbols else ""
        return {
            "success": False, 
            "error": f"Symbol not found: {symbol_name}.{suggestion}",
            "available_symbols_count": len(index.symbols)
        }
    
    # 2. 验证文件存在性
    target_file = file_path or symbol_info.file
    full_path = _resolve_file_path(index.base_path, target_file)
    if not full_path.exists():
        return {
            "success": False, 
            "error": f"File not found: {target_file}",
            "searched_path": str(full_path)
        }
    
    # 3. 读取并验证文件内容
    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        
        if not lines or len(lines) < symbol_info.line:
            return {
                "success": False,
                "error": f"Invalid line number {symbol_info.line} for symbol: {symbol_name}",
                "file_lines": len(lines)
            }
        
    except Exception as e:
        return _create_error_response(e, f"Failed to read file: {target_file}")
    
    # 4. 智能边界检测
    try:
        # 自动检测语言
        if language == "auto":
            file_info = index.get_file(target_file)
            language = file_info.language if file_info else "unknown"
        
        # 查找真正的符号定义行
        actual_start_line = _find_symbol_definition_line(
            lines, symbol_name, symbol_info.line, language
        )
        
        if actual_start_line <= 0:
            return {
                "success": False,
                "error": f"Cannot find symbol definition for: {symbol_name}",
                "indexed_line": symbol_info.line
            }
        
        # 检测语法体结束边界
        end_line = _detect_syntax_body_end_improved(
            lines, actual_start_line, language
        )
        
        # 验证边界有效性
        if end_line <= actual_start_line:
            return {
                "success": False,
                "error": f"Invalid symbol boundaries for: {symbol_name}",
                "start_line": actual_start_line,
                "end_line": end_line
            }
        
        # 5. 提取并验证内容
        start_idx = actual_start_line - 1
        end_idx = min(len(lines), end_line)
        body_lines = lines[start_idx:end_idx]
        
        if not body_lines:
            return {
                "success": False,
                "error": f"Empty symbol body for: {symbol_name}",
                "boundaries": f"{actual_start_line}-{end_line}"
            }
        
        # 6. 提取函数签名
        signature = _extract_function_signature(body_lines[0], language)
        
        # 7. 构建返回结果
        result = {
            "success": True,
            "symbol_name": symbol_name,
            "symbol_type": symbol_info.type,
            "file_path": target_file,
            "language": language,
            "start_line": actual_start_line,
            "end_line": end_line,
            "body_lines": body_lines,
            "signature": signature,
            "total_lines": len(body_lines),
            "content_preview": body_lines[0][:100] + "..." if len(body_lines[0]) > 100 else body_lines[0],
        }
        
        # 条件性添加行号
        if show_line_numbers:
            result["line_numbers"] = list(range(actual_start_line, actual_start_line + len(body_lines)))
        
        return result
        
    except Exception as e:
        return _create_error_response(e, f"Failed to extract symbol body: {symbol_name}")
```

### 2. 智能符号定义行查找

**设计原则**：
- 处理索引行号不准确的情况
- 支持装饰器、多行定义等特殊情况
- 提供上下文感知的查找

**实现**：
```python
def _find_symbol_definition_line(lines: List[str], symbol_name: str, 
                                indexed_line: int, language: str) -> int:
    """查找真正的符号定义行"""
    
    # 1. 首先检查索引行号是否正确
    if _is_symbol_definition_at_line(lines, indexed_line - 1, symbol_name, language):
        return indexed_line
    
    # 2. 在索引行号附近搜索（上下文窗口）
    search_window = 10  # 上下文搜索窗口大小
    start = max(0, indexed_line - 1 - search_window)
    end = min(len(lines), indexed_line - 1 + search_window)
    
    for line_idx in range(start, end):
        if _is_symbol_definition_at_line(lines, line_idx, symbol_name, language):
            return line_idx + 1  # 转换为1索引
    
    # 3. 全文件搜索（最后的备选方案）
    for line_idx, line in enumerate(lines):
        if _is_symbol_definition_at_line(lines, line_idx, symbol_name, language):
            return line_idx + 1
    
    return -1  # 未找到

def _is_symbol_definition_at_line(lines: List[str], line_idx: int, 
                                 symbol_name: str, language: str) -> bool:
    """检查指定行是否为符号定义"""
    if line_idx >= len(lines):
        return False
    
    line = lines[line_idx].strip()
    
    # 语言特定的检测
    if language == "python":
        return _is_python_symbol_definition(line, symbol_name, lines, line_idx)
    elif language in ["javascript", "typescript"]:
        return _is_js_symbol_definition(line, symbol_name)
    elif language in ["java", "c", "cpp", "rust", "go"]:
        return _is_c_family_symbol_definition(line, symbol_name)
    else:
        return _is_generic_symbol_definition(line, symbol_name)

def _is_python_symbol_definition(line: str, symbol_name: str, 
                                lines: List[str], line_idx: int) -> bool:
    """Python 符号定义检测"""
    # 检查函数定义
    if line.startswith(f"def {symbol_name}("):
        return True
    if line.startswith(f"async def {symbol_name}("):
        return True
    
    # 检查类定义
    if line.startswith(f"class {symbol_name}"):
        return True
    if line.startswith(f"class {symbol_name}("):
        return True
    
    # 检查装饰器情况
    if line_idx > 0 and line.startswith("@"):
        # 检查下一行是否为符号定义
        next_line = lines[line_idx + 1].strip() if line_idx + 1 < len(lines) else ""
        if next_line.startswith(f"def {symbol_name}("):
            return True
        if next_line.startswith(f"async def {symbol_name}("):
            return True
    
    return False
```

### 3. 改进的语法体边界检测

**设计原则**：
- 处理复杂的嵌套结构
- 支持多行字符串和注释
- 考虑语言特定的语法规则

**实现**：
```python
def _detect_syntax_body_end_improved(lines: List[str], start_line: int, 
                                   language: str) -> int:
    """改进的语法体边界检测"""
    if start_line <= 0 or start_line > len(lines):
        return start_line
    
    start_idx = start_line - 1
    
    # 语言特定的检测策略
    if language == "python":
        return _detect_python_body_end_improved(lines, start_idx)
    elif language in ["javascript", "typescript", "java", "c", "cpp", "rust", "go"]:
        return _detect_brace_body_end_improved(lines, start_idx)
    else:
        return _detect_indent_body_end_improved(lines, start_idx)

def _detect_python_body_end_improved(lines: List[str], start_idx: int) -> int:
    """改进的 Python 缩进检测"""
    if start_idx >= len(lines):
        return start_idx + 1
    
    # 1. 跳过多行定义
    actual_start_idx = _find_multiline_def_end(lines, start_idx)
    
    # 2. 获取函数体的起始缩进
    body_start_idx = actual_start_idx + 1
    while body_start_idx < len(lines) and lines[body_start_idx].strip() == "":
        body_start_idx += 1
    
    if body_start_idx >= len(lines):
        return len(lines)
    
    # 3. 计算基准缩进
    first_body_line = lines[body_start_idx]
    if not first_body_line.strip():
        return len(lines)
    
    base_indent = len(first_body_line) - len(first_body_line.lstrip())
    
    # 4. 查找缩进回退点
    for i in range(body_start_idx + 1, len(lines)):
        line = lines[i]
        
        # 跳过空行和注释
        if not line.strip() or line.strip().startswith("#"):
            continue
        
        # 跳过多行字符串
        if line.strip().startswith('"""') or line.strip().startswith("'''"):
            i = _skip_multiline_string(lines, i)
            continue
        
        current_indent = len(line) - len(line.lstrip())
        
        # 缩进回退表示函数体结束
        if current_indent <= base_indent:
            return i
    
    return len(lines)

def _find_multiline_def_end(lines: List[str], start_idx: int) -> int:
    """查找多行定义的结束位置"""
    # 检查是否为多行函数定义
    current_line = lines[start_idx].rstrip()
    
    # 简单情况：单行定义
    if ")" in current_line and ":" in current_line:
        return start_idx
    
    # 多行定义：查找闭合的括号
    paren_count = current_line.count("(") - current_line.count(")")
    line_idx = start_idx + 1
    
    while line_idx < len(lines) and paren_count > 0:
        line = lines[line_idx]
        paren_count += line.count("(") - line.count(")")
        line_idx += 1
    
    return line_idx - 1

def _skip_multiline_string(lines: List[str], start_idx: int) -> int:
    """跳过多行字符串"""
    if start_idx >= len(lines):
        return start_idx
    
    line = lines[start_idx]
    if '"""' in line:
        # 查找配对的 """
        for i in range(start_idx + 1, len(lines)):
            if '"""' in lines[i]:
                return i
    elif "'''" in line:
        # 查找配对的 '''
        for i in range(start_idx + 1, len(lines)):
            if "'''" in lines[i]:
                return i
    
    return start_idx
```

### 4. 增强的签名提取

**实现**：
```python
def _extract_function_signature(first_line: str, language: str) -> Optional[str]:
    """提取函数签名"""
    line = first_line.strip()
    
    if language == "python":
        # Python 函数签名
        if line.startswith("def ") or line.startswith("async def "):
            # 提取从 def 到行末的内容
            if ":" in line:
                return line[:line.rfind(":")]
            return line
    elif language in ["javascript", "typescript"]:
        # JavaScript/TypeScript 函数签名
        if line.startswith("function ") or "=" in line:
            return line
    elif language in ["java", "c", "cpp", "rust", "go"]:
        # C 系语言函数签名
        if "(" in line and ")" in line:
            return line
    
    return line if line else None
```

### 5. 辅助功能

**相似符号查找**：
```python
def _find_similar_symbols(target: str, symbol_list: List[str]) -> List[str]:
    """查找相似的符号名"""
    import difflib
    
    # 使用字符串相似度排序
    similar = difflib.get_close_matches(target, symbol_list, n=5, cutoff=0.6)
    return similar
```

## 测试策略

### 1. 边界情况测试

```python
def test_symbol_body_invalid_symbol(self):
    """测试无效符号"""
    result = tool_get_symbol_body("nonexistent_symbol")
    assert not result["success"]
    assert "not found" in result["error"]

def test_symbol_body_invalid_line_number(self):
    """测试无效行号"""
    # 模拟行号超出文件范围的情况
    # 需要创建测试数据

def test_symbol_body_multiline_definition(self):
    """测试多行定义"""
    # 测试参数很多的函数定义

def test_symbol_body_with_decorators(self):
    """测试带装饰器的函数"""
    # 测试 Python 装饰器情况
```

### 2. 语言特定测试

```python
def test_python_function_extraction(self):
    """测试 Python 函数提取"""
    # 测试各种 Python 函数定义

def test_javascript_function_extraction(self):
    """测试 JavaScript 函数提取"""
    # 测试 JavaScript 函数定义

def test_class_extraction(self):
    """测试类定义提取"""
    # 测试各种类定义
```

### 3. 性能测试

```python
def test_large_function_extraction(self):
    """测试大函数提取性能"""
    # 测试包含很多行的大函数

def test_nested_structure_extraction(self):
    """测试嵌套结构提取"""
    # 测试嵌套的类和函数
```

## 错误处理改进

### 1. 分层错误处理

```python
class SymbolBodyExtractionError(Exception):
    """符号体提取基础异常"""
    pass

class SymbolNotFoundError(SymbolBodyExtractionError):
    """符号未找到异常"""
    def __init__(self, symbol_name: str, suggestions: List[str] = None):
        self.symbol_name = symbol_name
        self.suggestions = suggestions or []
        super().__init__(f"Symbol not found: {symbol_name}")

class InvalidBoundaryError(SymbolBodyExtractionError):
    """无效边界异常"""
    def __init__(self, symbol_name: str, start_line: int, end_line: int):
        self.symbol_name = symbol_name
        self.start_line = start_line
        self.end_line = end_line
        super().__init__(f"Invalid boundaries for {symbol_name}: {start_line}-{end_line}")
```

### 2. 详细错误信息

```python
def _create_detailed_error(error: Exception, context: str, **kwargs) -> Dict[str, Any]:
    """创建详细的错误响应"""
    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__,
        "context": context,
        "details": kwargs,
        "timestamp": time.time()
    }
```

## 性能优化

### 1. 缓存策略

- 缓存符号定义行查找结果
- 缓存语法体边界检测结果
- 使用 LRU 缓存避免内存泄漏

### 2. 早期退出

- 在找到足够信息时提前返回
- 避免不必要的全文件扫描
- 使用启发式算法缩小搜索范围

## 向后兼容性

- 保持现有 API 接口不变
- 新增的错误信息不影响现有功能
- 性能优化只改进，不破坏现有行为