# 开发命令参考

## 基本设置和安装
```bash
# 推荐的开发环境设置
uv sync

# 激活虚拟环境 (如需要)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# 本地运行服务器
uv run code-index-mcp

# 测试简化架构
python test_simple_architecture.py
```

## 测试和调试
```bash
# 使用MCP Inspector进行调试
npx @modelcontextprotocol/inspector uv run code-index-mcp

# 运行测试套件
pytest

# 带覆盖率的测试
pytest --cov=src/code_index_mcp

# 性能测试
python phase4_benchmark.py
```

## 代码质量检查
```bash
# 类型检查
mypy src/code_index_mcp

# 代码格式检查
pylint src/code_index_mcp

# 运行所有质量检查
make check  # 如果存在Makefile
```

## 系统兼容性
由于运行在Windows/MSYS2环境:
- 使用 `ls` 而不是 `dir`
- 路径分隔符自动处理
- Git命令直接可用
- Python路径使用斜杠分隔

## 任务完成后必须运行的命令
1. `pytest` - 运行所有测试
2. `mypy src/code_index_mcp` - 类型检查
3. `python test_simple_architecture.py` - 验证架构
4. 更新 todo.md 进度记录