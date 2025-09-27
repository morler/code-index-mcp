# Code Index MCP - Ripgrep Integration Plan

## 项目背景

基于对当前自研搜索引擎的性能分析和ripgrep技术研究，制定集成ripgrep的详细实施计划。

## 性能收益分析

### 当前性能基准（自研搜索引擎）
- **文本搜索**：0.0500-0.1500秒（中等项目）
- **正则搜索**：0.0800-0.2000秒
- **并行优化**：仅在文件数>500时启用
- **内存使用**：需完整加载文件内容到Python字符串

### Ripgrep核心技术优势
1. **Rust零成本抽象** + **SIMD优化**
2. **Boyer-Moore字符串算法** + **literal optimizations**
3. **原生并行搜索** - 无GIL限制
4. **内存映射文件访问** - 避免完整文件读取
5. **线性时间保证** - 有限自动机正则引擎

### 预期性能提升

#### 小型项目（<1000文件）
- **文本搜索**：3-5x速度提升（0.050s → 0.010-0.015s）
- **正则搜索**：5-8x速度提升（0.080s → 0.010-0.015s）
- **内存使用**：-60%（避免Python字符串拷贝）

#### 中型项目（1000-10000文件）
- **文本搜索**：8-15x速度提升（0.150s → 0.010-0.020s）
- **正则搜索**：10-20x速度提升（0.200s → 0.010-0.020s）
- **并行效率**：真正的并行vs Python的伪并行

#### 大型项目（>10000文件）
- **文本搜索**：15-30x速度提升
- **正则搜索**：20-40x速度提升
- **内存映射**：无文件大小限制

## 实现方案 - Linus风格

### 核心原则：直接、简单、有效

#### 1. 一次性实现 - 无阶段划分
```python
# 在 src/core/search.py 直接添加：
def _search_text(self, query: SearchQuery) -> List[Dict[str, Any]]:
    # 检查ripgrep可用性
    if shutil.which("rg"):
        return self._search_with_ripgrep(query)
    else:
        return self._search_text_single(query)

def _search_with_ripgrep(self, query: SearchQuery) -> List[Dict[str, Any]]:
    cmd = ["rg", "--json", "--line-number"]
    if not query.case_sensitive:
        cmd.append("--ignore-case")
    cmd.extend([query.pattern, self.index.project_path])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return self._parse_rg_output(result.stdout)

def _parse_rg_output(self, output: str) -> List[Dict[str, Any]]:
    matches = []
    for line in output.strip().split('\n'):
        if line:
            data = json.loads(line)
            if data.get('type') == 'match':
                matches.append({
                    "file": data['data']['path']['text'],
                    "line": data['data']['line_number'],
                    "content": data['data']['lines']['text'].strip(),
                    "language": self._detect_language(data['data']['path']['text'])
                })
    return matches
```

### 工作量
- **总计：30-50行代码**
- **开发时间：2-4小时**
- **测试时间：1小时**

## 开发任务

### 唯一任务：集成ripgrep
1. 修改`src/core/search.py`中的`_search_text`和`_search_regex`方法
2. 添加ripgrep检测和JSON解析
3. 运行现有测试确保兼容性
4. **完成**

### 不做的事情
- ❌ 不创建新的类或模块
- ❌ 不添加配置系统
- ❌ 不添加复杂的错误处理
- ❌ 不进行阶段性开发

## 结论

**"这不是解决不存在问题的过度工程，而是解决真实性能瓶颈的务实方案。"**

这是一个完美符合"好品味"原则的技术决策：
- ✅ **简单的实现**
- ✅ **巨大的收益**
- ✅ **零破坏性**
- ✅ **务实的解决方案**