# Code Index MCP

<div align="center">

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.3.2-blue)](#)

**Linus-style intelligent code indexing with SCIP protocol support**

Direct data manipulation, zero abstractions, maximum performance for AI code analysis.

</div>

<a href="https://glama.ai/mcp/servers/@johnhuang316/code-index-mcp">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@johnhuang316/code-index-mcp/badge" alt="code-index-mcp MCP server" />
</a>

## Overview

Code Index MCP is a [Model Context Protocol](https://modelcontextprotocol.io) server implementing **Linus Torvalds' design philosophy**: direct data manipulation, elimination of special cases, and zero unnecessary abstractions. Built with SCIP protocol support for semantic code analysis.

**Architecture Principles:**
- **"Good Taste"**: Unified interfaces eliminate if/else chains
- **"Never Break Userspace"**: Backward-compatible MCP tools
- **"Pragmatism First"**: Solve real problems, not theoretical ones
- **"Simplicity Obsession"**: <200 lines per file, <3 indentation levels

**Perfect for:** Semantic code analysis, cross-file symbol tracking, intelligent refactoring, and architectural understanding.

## Quick Start

### 🚀 **Recommended Setup (Most Users)**

The easiest way to get started with any MCP-compatible application:

**Prerequisites:** Python 3.10+ and [uv](https://github.com/astral-sh/uv)

1. **Add to your MCP configuration** (e.g., `claude_desktop_config.json` or `~/.claude.json`):
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

2. **Restart your application** – `uvx` automatically handles installation and execution

3. **Start using** (give these prompts to your AI assistant):
   ```
   Set the project path to /Users/dev/my-react-app
   Find all TypeScript files in this project
   Search for "authentication" functions
   Analyze the main App.tsx file
   ```

## Typical Use Cases

**Code Review**: "Find all places using the old API"
**Refactoring Help**: "Where is this function called?"
**Learning Projects**: "Show me the main components of this React project"
**Debugging**: "Search for all error handling related code"

## Key Features

### 🏗️ **Linus-style Unified Architecture**
- **Single CodeIndex**: Direct data structure handles ALL operations
- **Zero Abstractions**: No service wrappers, no delegation patterns
- **Operation Registry**: Eliminates if/else chains through function dispatch
- **Atomic Operations**: Edit/search/index operations with automatic rollback
- **Direct Tool Access**: `unified_tool()` handles 30+ specialized functions

### 🔬 **SCIP Protocol Integration**
- **Semantic Symbol IDs**: Industry-standard symbol identification
- **Cross-file References**: Track symbol usage across entire codebase
- **Definition/Reference Tracking**: Precise navigation between symbols
- **Symbol Hierarchy**: Complete inheritance and dependency graphs
- **Export Compatibility**: Generate SCIP indexes for external tools

### 🌳 **Multi-Language Tree-sitter Parsing**
- **7 Core Languages**: Python, JavaScript, TypeScript, Java, Go, Zig, Objective-C
- **Direct AST Access**: No regex fallbacks - fail fast with clear errors
- **Symbol Extraction**: Functions, classes, methods, variables, imports
- **Signature Capture**: Complete method signatures and type information
- **Call Relationship Tracking**: Who calls whom, cross-file analysis

### ⚡ **Performance Optimizations**
- **Incremental Updates**: Only reprocess changed files
- **LRU Caching**: File content and regex compilation caching
- **Memory Management**: Automatic cleanup at 80% threshold
- **Hash-based Change Detection**: xxhash for rapid file comparison
- **Optimized Data Structures**: Direct dictionary access, zero copying

## Supported File Types

<details>
<summary><strong>📁 Programming Languages (Click to expand)</strong></summary>

**Languages with Specialized Tree-sitter Strategies:**
- **Python** (`.py`, `.pyw`) - Full AST analysis with class/method extraction and call tracking
- **JavaScript** (`.js`, `.jsx`, `.mjs`, `.cjs`) - ES6+ class and function parsing with tree-sitter
- **TypeScript** (`.ts`, `.tsx`) - Complete type-aware symbol extraction with interfaces
- **Java** (`.java`) - Full class hierarchy, method signatures, and call relationships
- **Go** (`.go`) - Struct methods, receiver types, and function analysis
- **Objective-C** (`.m`, `.mm`) - Class/instance method distinction with +/- notation
- **Zig** (`.zig`, `.zon`) - Function and struct parsing with tree-sitter AST

**All Other Programming Languages:**
All other programming languages use the **FallbackParsingStrategy** which provides basic file indexing and metadata extraction. This includes:
- **System & Low-Level:** C/C++ (`.c`, `.cpp`, `.h`, `.hpp`), Rust (`.rs`)
- **Object-Oriented:** C# (`.cs`), Kotlin (`.kt`), Scala (`.scala`), Swift (`.swift`)
- **Scripting & Dynamic:** Ruby (`.rb`), PHP (`.php`), Shell (`.sh`, `.bash`)
- **And 40+ more file types** - All handled through the fallback strategy for basic indexing

</details>

<details>
<summary><strong>🌐 Web & Frontend (Click to expand)</strong></summary>

**Frameworks & Libraries:**
- Vue (`.vue`)
- Svelte (`.svelte`)
- Astro (`.astro`)

**Styling:**
- CSS (`.css`, `.scss`, `.less`, `.sass`, `.stylus`, `.styl`)
- HTML (`.html`)

**Templates:**
- Handlebars (`.hbs`, `.handlebars`)
- EJS (`.ejs`)
- Pug (`.pug`)

</details>

<details>
<summary><strong>🗄️ Database & SQL (Click to expand)</strong></summary>

**SQL Variants:**
- Standard SQL (`.sql`, `.ddl`, `.dml`)
- Database-specific (`.mysql`, `.postgresql`, `.psql`, `.sqlite`, `.mssql`, `.oracle`, `.ora`, `.db2`)

**Database Objects:**
- Procedures & Functions (`.proc`, `.procedure`, `.func`, `.function`)
- Views & Triggers (`.view`, `.trigger`, `.index`)

**Migration & Tools:**
- Migration files (`.migration`, `.seed`, `.fixture`, `.schema`)
- Tool-specific (`.liquibase`, `.flyway`)

**NoSQL & Modern:**
- Graph & Query (`.cql`, `.cypher`, `.sparql`, `.gql`)

</details>

<details>
<summary><strong>📄 Documentation & Config (Click to expand)</strong></summary>

- Markdown (`.md`, `.mdx`)
- Configuration (`.json`, `.xml`, `.yml`, `.yaml`)

</details>

### 🛠️ **Development Setup**

For contributing or local development:

1. **Clone and install:**
   ```bash
   git clone https://github.com/johnhuang316/code-index-mcp.git
   cd code-index-mcp
   uv sync
   ```

> **Important:** Activate the provided virtual environment (.venv\Scripts\activate) or use uv run code-index-mcp before running helper scripts such as python run.py. These commands require the project dependencies to be installed.

2. **Configure for local development:**
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

3. **Debug with MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector uv run code-index-mcp
   ```

<details>
<summary><strong>Alternative: Manual pip Installation</strong></summary>

If you prefer traditional pip management:

```bash
pip install code-index-mcp
```

Then configure:
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


## Available Tools

### 🏗️ **Core Project Management**
| Tool | Description |
|------|-------------|
| **`set_project_path`** | Initialize Linus-style direct indexing for project |
| **`get_index_stats`** | View indexed files, symbols, and performance metrics |
| **`update_incrementally`** | Smart incremental updates (Linus principle: only changed files) |
| **`full_rebuild_index`** | Force complete rebuild when needed |

### 🔍 **Unified Search Interface**
| Tool | Description |
|------|-------------|
| **`search_code`** | Unified search: text, regex, symbol types through single interface |
| **`find_files`** | Glob pattern file discovery (e.g., `**/*.py`) |
| **`semantic_search`** | SCIP-powered semantic symbol search |
| **`find_references`** | Cross-file symbol reference tracking |
| **`find_definition`** | Navigate to symbol definitions |
| **`find_callers`** | Who calls this function/method |

### 📁 **File & Symbol Analysis**
| Tool | Description |
|------|-------------|
| **`get_file_content`** | Direct file access with line range support |
| **`get_file_summary`** | Tree-sitter parsed structure: functions, classes, imports |
| **`get_symbol_body`** | Extract complete syntax bodies (auto-detects boundaries) |
| **`get_changed_files`** | List files modified since last index |

### ✏️ **Semantic Editing (NEW)**
| Tool | Description |
|------|-------------|
| **`rename_symbol`** | Cross-file safe symbol renaming with backup |
| **`add_import`** | Smart import insertion at correct file locations |
| **`apply_edit`** | Atomic content editing with automatic rollback |

### 🔬 **SCIP Protocol Tools**
| Tool | Description |
|------|-------------|
| **`generate_scip_symbol_id`** | Create industry-standard symbol identifiers |
| **`find_scip_symbol`** | SCIP-based symbol search with overload support |
| **`get_cross_references`** | Complete cross-file usage analysis |
| **`get_symbol_graph`** | Full dependency and relationship graphs |
| **`export_scip_index`** | Generate standard SCIP format for external tools |

## Usage Examples

### 🎯 **Quick Start Workflow**

**1. Initialize Your Project**
```
Set the project path to /Users/dev/my-react-app
```
*Automatically indexes your codebase and creates searchable cache*

**2. Explore Project Structure**
```
Find all TypeScript component files in src/components
```
*Uses: `find_files` with pattern `src/components/**/*.tsx`*

**3. Analyze Key Files**
```
Give me a summary of src/api/userService.ts
```
*Uses: `get_file_summary` to show functions, imports, and complexity*

### 🔍 **Advanced Search Examples**

<details>
<summary><strong>Unified Search Interface</strong></summary>

```
Search for "get.*Data" using regex pattern
```
*Uses: `search_code` with `search_type="regex"` - finds getData(), getUserData(), etc.*

</details>

<details>
<summary><strong>SCIP Semantic Search</strong></summary>

```
Find all references to the authenticateUser function
```
*Uses: `find_references` - tracks cross-file usage with SCIP protocol*

</details>

<details>
<summary><strong>Symbol Navigation</strong></summary>

```
Show me who calls the validateInput method
```
*Uses: `find_callers` - complete call graph analysis*

</details>

<details>
<summary><strong>Smart Symbol Editing</strong></summary>

```
Rename function getUserById to fetchUserById across all files
```
*Uses: `rename_symbol` - safe cross-file renaming with automatic backup*

</details>

<details>
<summary><strong>Incremental Updates</strong></summary>

```
Update the index to include my recent file changes
```
*Uses: `update_incrementally` - Linus principle: only process changed files*

</details>

<details>
<summary><strong>Complete Symbol Analysis</strong></summary>

```
Get the full implementation of the DatabaseManager class
```
*Uses: `get_symbol_body` - extracts complete syntax with auto-detected boundaries*

</details>

## Troubleshooting

### 🏗️ **Index Issues**

**Files not appearing in search:**
- Use `update_incrementally` to refresh changed files
- Check `get_index_stats` to verify project path is set
- Try `full_rebuild_index` for complete refresh

**Symbol search not working:**
- Verify tree-sitter parser availability for your language
- Use `get_file_summary` to check if symbols were extracted
- Tree-sitter supports: Python, JS, TS, Java, Go, Zig, Objective-C

**Performance issues:**
- Check `get_changed_files` to see incremental update scope
- Large projects: Use file patterns to search specific directories
- Memory usage: System automatically cleans cache at 80% threshold

## Development & Contributing

### 🔧 **Building from Source**
```bash
git clone https://github.com/johnhuang316/code-index-mcp.git
cd code-index-mcp
uv sync
uv run code-index-mcp
```

### 🐛 **Debugging**
```bash
npx @modelcontextprotocol/inspector uvx code-index-mcp
```

### 🤝 **Contributing**
Contributions are welcome! Please feel free to submit a Pull Request.

---

### 📜 **License**
[MIT License](LICENSE)

### 🌐 **Translations**
- [简体中文](README_CN.md)