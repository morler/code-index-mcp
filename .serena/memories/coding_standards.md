# 代码标准和约定

## Linus风格编程哲学

### 核心原则
1. **"Good Taste"** - 消除特殊情况，让代码简单优雅
2. **"Never Break Userspace"** - 绝不破坏向后兼容性  
3. **直接数据操作** - 不要包装器，不要抽象层
4. **简单胜过复杂** - 如果需要超过3层缩进，重新设计

### 代码风格约定

#### 文件结构
- 每个文件不超过200行
- 每个函数不超过30行
- 最多2层缩进

#### 命名约定
```python
# 类名: PascalCase
class CodeIndex:

# 函数名: snake_case  
def search_code():

# 常量: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024

# 私有方法: _leading_underscore
def _internal_method():
```

#### 数据结构设计
```python
# 优先使用dataclass
@dataclass
class FileInfo:
    language: str
    line_count: int
    symbols: Dict[str, List[str]]

# 避免复杂继承，使用组合
# 好: index.search(query)
# 坏: SearchService(BaseService).execute()
```

#### 错误处理
```python
# 统一错误格式
{
    "success": bool,
    "error": Optional[str],
    "data": Any
}

# 使用装饰器统一异常处理
@handle_errors
def tool_function():
    pass
```

### 操作注册表模式
```python
# 好的设计 - 零分支
operations = {
    "search": search_handler,
    "find": find_handler,
    "edit": edit_handler
}
result = operations[op_type](params)

# 避免的设计 - 特殊情况堆积
if op_type == "search":
    # ...
elif op_type == "find":
    # ...
```

### 类型提示
- 所有公共函数必须有类型提示
- 使用 `Optional[T]` 而不是 `Union[T, None]`
- 复杂类型使用 `TypedDict`

### 文档字符串
```python
def search_code(pattern: str, search_type: str) -> SearchResult:
    """搜索代码 - 统一入口点
    
    Args:
        pattern: 搜索模式
        search_type: 搜索类型 (text|regex|symbol)
    
    Returns:
        SearchResult: 包含匹配结果和统计信息
    """
```

### 测试约定
- 每个核心功能必须有测试
- 测试函数名: `test_功能_场景`
- 使用pytest fixture进行设置
- 向后兼容性测试必须通过

### Git提交约定
```
🎯 Fix symbol indexing - Register symbols to global index
🔧 Add semantic editing - Direct file operations  
🧹 Clean up documentation - Remove obsolete files
```