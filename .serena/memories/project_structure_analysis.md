# Code Index MCP 项目结构分析

## 项目概况
Code Index MCP 是一个基于Model Context Protocol的代码索引和分析服务器，为大型语言模型提供智能代码理解能力。

## 技术栈
- **语言**: Python 3.10+
- **核心框架**: MCP (Model Context Protocol)
- **构建工具**: setuptools, uv
- **代码解析**: tree-sitter (7种语言深度支持)
- **文件监控**: watchdog
- **打包**: msgpack

## 架构设计哲学 - Linus风格重构
项目遵循Linus Torvalds的设计哲学，进行了重大架构简化：

### 核心改进
1. **统一数据结构**: 单一CodeIndex处理所有操作
2. **零抽象层**: 直接数据操作，无服务包装
3. **操作注册表**: 消除if/else条件链
4. **代码精简**: 服务器从705行减少到49行 (93%减少)

### 项目结构
```
src/
├── code_index_mcp/          # MCP服务器入口
│   ├── server_unified.py    # 统一服务器(49行)
│   └── constants.py         # 常量定义
└── core/                    # 核心数据结构
    ├── index.py            # 统一CodeIndex(71行)
    ├── builder.py          # 索引构建
    ├── search_optimized.py # 优化搜索引擎
    ├── mcp_tools.py        # MCP工具实现
    ├── edit.py             # 语义编辑操作
    └── operations.py       # 操作实现
```

## 支持的编程语言
- **Tree-sitter深度解析(7种)**: Python, JavaScript, TypeScript, Java, Go, Objective-C, Zig
- **后备策略支持(50+种)**: C/C++, Rust, Ruby, PHP等所有其他语言

## 关键特性
- 智能搜索和分析
- 实时文件监控
- 语义编辑操作
- 跨文件符号重命名
- 自动导入管理