# Code Index MCP

<div align="center">

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.3.2-blue)](#)

**Linus风格的智能代码索引，支持SCIP协议**

直接数据操作，零抽象层，为AI代码分析提供最大性能。

</div>

<a href="https://glama.ai/mcp/servers/@johnhuang316/code-index-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@johnhuang316/code-index-mcp/badge" alt="code-index-mcp MCP server" />
</a>

## 概述

Code Index MCP是一个实现了**Linus Torvalds设计哲学**的[模型上下文协议](https://modelcontextprotocol.io)服务器：直接数据操作、消除特殊情况、零不必要抽象。内置SCIP协议支持语义代码分析。

**架构原则：**
- **"好品味"**：统一接口消除if/else链
- **"永不破坏用户空间"**：向后兼容的MCP工具
- **"实用主义优先"**：解决真实问题，不是理论问题
- **"简洁强迫症"**：每文件<200行，缩进<3层

**完美适用于：** 语义代码分析、跨文件符号追踪、智能重构、架构理解。

## 快速开始

### 🚀 **推荐设置（大多数用户）**

适用于任何MCP兼容应用的最简单方法：

**先决条件：** Python 3.10+ 和 [uv](https://github.com/astral-sh/uv)

1. **添加到您的MCP配置** (如 `claude_desktop_config.json` 或 `~/.claude.json`)：
   ```json
   {
     "mcpServers": {
       "code-index": {
         "command": "uvx",
         "args": ["code-index-mcp"]
       }
     }
   }
   ```

2. **重启您的应用** – `uvx` 自动处理安装和执行

3. **开始使用** (给您的AI助手这些提示)：
   ```
   将项目路径设置为 /Users/dev/my-react-app
   查找此项目中的所有TypeScript文件
   搜索"authentication"相关函数
   分析主要的App.tsx文件
   ```

## 典型用例

**代码审查**: "找到所有使用旧API的地方"
**重构帮助**: "这个函数在哪里被调用？"
**学习项目**: "显示这个React项目的主要组件"
**调试**: "搜索所有错误处理相关代码"

## 核心特性

### 🏗️ **Linus式统一架构**
- **单一CodeIndex**: 直接数据结构处理所有操作
- **零抽象**: 没有服务包装器，没有委托模式
- **操作注册表**: 通过函数分发消除if/else链
- **原子操作**: 编辑/搜索/索引操作支持自动回滚
- **直接工具访问**: `unified_tool()` 处理30+专门函数

### 🔬 **SCIP协议集成**
- **语义符号ID**: 行业标准符号识别
- **跨文件引用**: 追踪整个代码库的符号使用
- **定义/引用追踪**: 符号间的精确导航
- **符号层次结构**: 完整的继承和依赖图
- **导出兼容性**: 为外部工具生成SCIP索引

### 🌳 **多语言Tree-sitter解析**
- **7种核心语言**: Python, JavaScript, TypeScript, Java, Go, Zig, Objective-C
- **直接AST访问**: 没有正则表达式回退 - 快速失败并提供清晰错误
- **符号提取**: 函数、类、方法、变量、导入
- **签名捕获**: 完整的方法签名和类型信息
- **调用关系追踪**: 谁调用谁，跨文件分析

### ⚡ **性能优化**
- **增量更新**: 只重新处理更改的文件
- **LRU缓存**: 文件内容和正则表达式编译缓存
- **内存管理**: 80%阈值时自动清理
- **基于哈希的变更检测**: xxhash快速文件比较
- **优化数据结构**: 直接字典访问，零拷贝

## 支持的文件类型

<details>
<summary><strong>📁 编程语言 (点击展开)</strong></summary>

**支持专门Tree-sitter策略的语言：**
- **Python** (`.py`, `.pyw`) - 完整AST分析，类/方法提取和调用追踪
- **JavaScript** (`.js`, `.jsx`, `.mjs`, `.cjs`) - ES6+类和函数解析，使用tree-sitter
- **TypeScript** (`.ts`, `.tsx`) - 完整类型感知符号提取，包括接口
- **Java** (`.java`) - 完整类层次结构、方法签名和调用关系
- **Go** (`.go`) - 结构体方法、接收器类型和函数分析
- **Objective-C** (`.m`, `.mm`) - 类/实例方法区分，+/-标记
- **Zig** (`.zig`, `.zon`) - 函数和结构体解析，使用tree-sitter AST

**所有其他编程语言：**
所有其他编程语言使用**回退解析策略**，提供基本文件索引和元数据提取。包括：
- **系统和底层**: C/C++ (`.c`, `.cpp`, `.h`, `.hpp`), Rust (`.rs`)
- **面向对象**: C# (`.cs`), Kotlin (`.kt`), Scala (`.scala`), Swift (`.swift`)
- **脚本和动态**: Ruby (`.rb`), PHP (`.php`), Shell (`.sh`, `.bash`)
- **和40+种文件类型** - 全部通过回退策略处理基本索引

</details>

<details>
<summary><strong>🌐 Web和前端 (点击展开)</strong></summary>

**框架和库：**
- Vue (`.vue`)
- Svelte (`.svelte`)
- Astro (`.astro`)

**样式：**
- CSS (`.css`, `.scss`, `.less`, `.sass`, `.stylus`, `.styl`)
- HTML (`.html`)

**模板：**
- Handlebars (`.hbs`, `.handlebars`)
- EJS (`.ejs`)
- Pug (`.pug`)

</details>

<details>
<summary><strong>🗄️ 数据库和SQL (点击展开)</strong></summary>

**SQL变体：**
- 标准SQL (`.sql`, `.ddl`, `.dml`)
- 数据库特定 (`.mysql`, `.postgresql`, `.psql`, `.sqlite`, `.mssql`, `.oracle`, `.ora`, `.db2`)

**数据库对象：**
- 过程和函数 (`.proc`, `.procedure`, `.func`, `.function`)
- 视图和触发器 (`.view`, `.trigger`, `.index`)

**迁移和工具：**
- 迁移文件 (`.migration`, `.seed`, `.fixture`, `.schema`)
- 工具特定 (`.liquibase`, `.flyway`)

**NoSQL和现代：**
- 图和查询 (`.cql`, `.cypher`, `.sparql`, `.gql`)

</details>

<details>
<summary><strong>📄 文档和配置 (点击展开)</strong></summary>

- Markdown (`.md`, `.mdx`)
- 配置 (`.json`, `.xml`, `.yml`, `.yaml`)

</details>

### 🛠️ **开发设置**

用于贡献或本地开发：

1. **克隆和安装:**
   ```bash
   git clone https://github.com/johnhuang316/code-index-mcp.git
   cd code-index-mcp
   uv sync
   ```

> **重要:** 激活提供的虚拟环境 (.venv\Scripts\activate) 或在运行辅助脚本(如 python run.py)前使用 uv run code-index-mcp。这些命令需要安装项目依赖。

2. **配置本地开发:**
   ```json
   {
     "mcpServers": {
       "code-index": {
         "command": "uv",
         "args": ["run", "code-index-mcp"]
       }
     }
   }
   ```

3. **使用MCP检查器调试:**
   ```bash
   npx @modelcontextprotocol/inspector uv run code-index-mcp
   ```

<details>
<summary><strong>替代方案: 手动pip安装</strong></summary>

如果您偏好传统pip管理：

```bash
pip install code-index-mcp
```

然后配置：
```json
{
  "mcpServers": {
    "code-index": {
      "command": "code-index-mcp",
      "args": []
    }
  }
}
```

</details>


## 可用工具

### 🏗️ **核心项目管理**
| 工具 | 描述 |
|------|-------------|
| **`set_project_path`** | 为项目初始化Linus式直接索引 |
| **`get_index_stats`** | 查看已索引文件、符号和性能指标 |
| **`update_incrementally`** | 智能增量更新（Linus原则：仅更改文件） |
| **`full_rebuild_index`** | 需要时强制完全重建 |

### 🔍 **统一搜索接口**
| 工具 | 描述 |
|------|-------------|
| **`search_code`** | 统一搜索：通过单一接口进行文本、正则、符号类型搜索 |
| **`find_files`** | Glob模式文件发现 (如 `**/*.py`) |
| **`semantic_search`** | SCIP驱动的语义符号搜索 |
| **`find_references`** | 跨文件符号引用追踪 |
| **`find_definition`** | 导航到符号定义 |
| **`find_callers`** | 谁调用了这个函数/方法 |

### 📁 **文件和符号分析**
| 工具 | 描述 |
|------|-------------|
| **`get_file_content`** | 支持行范围的直接文件访问 |
| **`get_file_summary`** | Tree-sitter解析结构：函数、类、导入 |
| **`get_symbol_body`** | 提取完整语法体（自动检测边界） |
| **`get_changed_files`** | 列出自上次索引以来修改的文件 |

### ✏️ **语义编辑（新功能）**
| 工具 | 描述 |
|------|-------------|
| **`rename_symbol`** | 跨文件安全符号重命名，支持备份 |
| **`add_import`** | 在正确文件位置智能插入导入 |
| **`apply_edit`** | 原子内容编辑，支持自动回滚 |

### 🔬 **SCIP协议工具**
| 工具 | 描述 |
|------|-------------|
| **`generate_scip_symbol_id`** | 创建行业标准符号标识符 |
| **`find_scip_symbol`** | 基于SCIP的符号搜索，支持重载 |
| **`get_cross_references`** | 完整跨文件使用分析 |
| **`get_symbol_graph`** | 完整依赖和关系图 |
| **`export_scip_index`** | 为外部工具生成标准SCIP格式 |

## 使用示例

### 🎯 **快速开始工作流**

**1. 初始化您的项目**
```
将项目路径设置为 /Users/dev/my-react-app
```
*自动索引您的代码库并创建可搜索缓存*

**2. 探索项目结构**
```
在src/components中查找所有TypeScript组件文件
```
*使用: `find_files` 配合模式 `src/components/**/*.tsx`*

**3. 分析关键文件**
```
给我src/api/userService.ts的摘要
```
*使用: `get_file_summary` 显示函数、导入和复杂度*

### 🔍 **高级搜索示例**

<details>
<summary><strong>统一搜索接口</strong></summary>

```
使用正则模式搜索"get.*Data"
```
*使用: `search_code` 配合 `search_type="regex"` - 查找getData(), getUserData()等*

</details>

<details>
<summary><strong>SCIP语义搜索</strong></summary>

```
查找authenticateUser函数的所有引用
```
*使用: `find_references` - 使用SCIP协议追踪跨文件使用*

</details>

<details>
<summary><strong>符号导航</strong></summary>

```
显示谁调用了validateInput方法
```
*使用: `find_callers` - 完整调用图分析*

</details>

<details>
<summary><strong>智能符号编辑</strong></summary>

```
将getUserById函数重命名为fetchUserById，影响所有文件
```
*使用: `rename_symbol` - 安全跨文件重命名，自动备份*

</details>

<details>
<summary><strong>增量更新</strong></summary>

```
更新索引以包含我最近的文件更改
```
*使用: `update_incrementally` - Linus原则：仅处理更改的文件*

</details>

<details>
<summary><strong>完整符号分析</strong></summary>

```
获取DatabaseManager类的完整实现
```
*使用: `get_symbol_body` - 提取完整语法，自动检测边界*

</details>

## 故障排除

### 🏗️ **索引问题**

**文件未出现在搜索中：**
- 使用 `update_incrementally` 刷新更改的文件
- 检查 `get_index_stats` 以验证是否设置了项目路径
- 尝试 `full_rebuild_index` 进行完全刷新

**符号搜索不工作：**
- 验证您的语言是否有tree-sitter解析器可用
- 使用 `get_file_summary` 检查是否提取了符号
- Tree-sitter支持：Python, JS, TS, Java, Go, Zig, Objective-C

**性能问题：**
- 检查 `get_changed_files` 查看增量更新范围
- 大型项目：使用文件模式搜索特定目录
- 内存使用：系统在80%阈值时自动清理缓存

## 开发和贡献

### 🔧 **从源码构建**
```bash
git clone https://github.com/johnhuang316/code-index-mcp.git
cd code-index-mcp
uv sync
uv run code-index-mcp
```

### 🐛 **调试**
```bash
npx @modelcontextprotocol/inspector uvx code-index-mcp
```

### 🤝 **贡献**
欢迎贡献！请随时提交Pull Request。

---

### 📜 **许可证**
[MIT许可证](LICENSE)

### 🌐 **其他语言**
- [English](README.md)