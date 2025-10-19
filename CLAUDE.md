<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code Index MCP is a Model Context Protocol server providing intelligent code indexing, search, and analysis capabilities for Large Language Models.

**Core Architecture**: Linus-style direct data manipulation - no service abstractions, no wrappers, just pure data structures.

> *"Bad programmers worry about the code. Good programmers worry about data structures and their relationships."* - Linus Torvalds

## Development Commands

### Setup and Installation
```bash
# Development setup (recommended)
uv sync

# Activate virtual environment (if needed)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

# Run server locally
uv run code-index-mcp

# Test simplified architecture
python tests/test_simple_architecture.py
```

### Testing and Quality
```bash
# Run all tests
pytest tests/

# Run specific test types
pytest tests/ -m unit
pytest tests/ -m integration
pytest tests/ -m "not slow"

# Run test coverage
pytest --cov=src/code_index_mcp tests/

# Type checking
mypy src/code_index_mcp

# Debug with MCP Inspector
npx @modelcontextprotocol/inspector uv run code-index-mcp
```

### Dependencies Management
- **Build system**: setuptools
- **Package manager**: uv (recommended) or pip
- **Python version**: 3.10+
- **Core dependencies**: mcp, tree-sitter (multiple language parsers), watchdog, msgpack, xxhash
- **Dev dependencies**: pytest, pytest-cov, mypy

## Architecture Overview - Linus Style

### Unified Data Structure Architecture
The project follows **Linus principles** with direct data manipulation:

🟢 **What We Have Now**:
- **Single CodeIndex**: Unified data structure handling ALL operations
- **Direct access**: No service wrappers or abstractions
- **Zero special cases**: Unified interfaces eliminate if/else chains
- **Pure functions**: Direct data transformation

### Core Components

#### 1. Core Data Structures (`src/core/`)
```
src/core/
├── index.py          # Unified CodeIndex - main data structure
├── builder.py        # Direct index building
├── edit.py           # Semantic editing operations ✨ NEW
├── mcp_tools.py      # MCP tool implementations
├── cache.py          # Caching infrastructure
└── incremental.py    # Incremental update logic
```

#### 2. Simplified Server (`src/code_index_mcp/server_unified.py`)
- **Minimal implementation** - dramatically reduced complexity
- Uses unified tool entry point
- Direct tool registration via `execute_tool(operation, **params)`
- Backward compatibility for specific tools

#### 3. Unified Tool Interface
**Single entry point** - the `unified_tool` function handles all operations:
```python
# Unified tool pattern - eliminates special cases
execute_tool("search_code", pattern="function", search_type="text")
execute_tool("find_files", pattern="*.py")
execute_tool("set_project_path", path="/path/to/project")

# Direct index access
index = get_index()
result = index.search(SearchQuery(pattern, search_type))
files = index.find_files_by_pattern("*.py")
```

### Search Engine Integration
**Operation registry pattern** eliminates conditional logic:
```python
# No more if/else chains!
_search_ops = {
    "text": self._search_text,
    "regex": self._search_regex,
    "symbol": self._search_symbol,
    "references": self._find_references,
    "definition": self._find_definition,
    "callers": self._find_callers
}

# Single unified interface
def search(self, query: SearchQuery) -> SearchResult:
    return self._search_ops[query.type](query)
```

### Key Improvements

#### Code Reduction
- **Server.py**: 705 → 49 lines (93% reduction)
- **Total services**: 12 files → 0 files (100% elimination)
- **Architecture complexity**: High → Minimal

#### Performance Gains
- **Direct data access**: No wrapper overhead
- **Unified caching**: Single index instance
- **Simplified control flow**: No service delegation

#### Maintainability
- **Single point of truth**: CodeIndex handles everything
- **No abstractions**: What you see is what you get
- **Debuggable**: Direct data structure inspection

### 🆕 Semantic Editing Features

#### Linus-Style Code Editing
- **Direct file operations**: No service wrappers
- **Atomic editing**: Automatic backup and rollback
- **Simple implementation**: 130 lines vs 600+ complex service

#### Available Edit Operations
```python
# Symbol renaming (cross-file)
rename_symbol(old_name="old_func", new_name="new_func")

# Smart import adding
add_import(file_path="src/main.py", import_statement="import os")

# Direct content editing
apply_edit(file_path="file.py", old_content="...", new_content="...")
```

#### Safety Mechanisms
- **Automatic backup**: Every edit creates .bak files
- **Atomic operations**: All-or-nothing editing
- **Validation**: Symbol name checking
- **Rollback support**: Restore from backups

## Important Implementation Details

### Core Principles Applied

1. **"Good Taste" Implementation**
   - Eliminated special cases through unified SearchQuery interface
   - Operation registry replaces conditional chains
   - Direct data manipulation, no wrappers

2. **"Never Break Userspace"**
   - MCP tool interfaces remain unchanged
   - Backward compatibility maintained
   - Same functionality, simpler implementation

3. **"Pragmatic Solutions"**
   - Removed theoretical "perfect" service abstractions
   - Focus on real-world usage patterns
   - Simple beats complex every time

4. **"Simplicity Obsession"**
   - Files kept under 200 lines each
   - Functions under 30 lines
   - Maximum 2 levels of indentation

### Direct Data Access Pattern

All operations work directly with data:
```python
# Add data directly
index.add_file(path, file_info)
index.add_symbol(name, symbol_info)

# Query data directly
files = index.find_files_by_pattern("*.py")
result = index.search(query)

# Access data directly
file_info = index.get_file(path)
stats = index.get_stats()
```

### Thread Safety
- **Single global index**: Thread-safe singleton pattern
- **Immutable queries**: SearchQuery objects are read-only
- **No shared state**: Each operation is stateless

## Entry Points

- **Main server**: `src/code_index_mcp/server_unified.py:main()` (unified tool interface)
- **Core index**: `src/core/index.py:CodeIndex` (unified data structure)
- **Tool execution**: `src/core/mcp_tools.py:execute_tool()` (operation dispatcher)
- **Test runner**: `tests/test_simple_architecture.py` (validation)

## Configuration

- **No config files**: Simple global index initialization
- **Project setup**: `set_project_path()` function
- **Index building**: `IndexBuilder(index).build_index()`

## Working with the Codebase

### Adding New Features
1. **Extend CodeIndex** directly in `src/core/index.py`
2. **Add search operation** to `_search_ops` registry
3. **Add MCP tool** in `src/core/mcp_tools.py`
4. **Test with** `pytest tests/test_simple_architecture.py`

### Linus Development Rules
- **No new abstractions**: Extend existing data structures
- **No service layers**: Direct data manipulation only
- **No wrappers**: Functions operate on data directly
- **Keep it simple**: If it needs >3 indentation levels, redesign

### Performance Optimization
- **Direct access**: No service delegation overhead
- **Single index**: Unified caching strategy
- **Minimal objects**: Dataclasses over complex objects
- **Pure functions**: No side effects in search operations

## Migration Notes

### What Was Removed
- `src/code_index_mcp/services/` (entire directory)
- Complex service initialization code
- Validation helper abstractions
- Context management overhead
- Error wrapping layers

### What Replaces It
- `src/core/index.py` - Single data structure
- `src/core/builder.py` - Direct index building
- `src/core/mcp_tools.py` - Simple tool functions with unified interface
- `src/code_index_mcp/server_unified.py` - Minimal server with operation dispatch

### Compatibility
- ✅ All MCP tools work identically
- ✅ Same search functionality
- ✅ Same performance characteristics
- ✅ Same external interfaces
- 🚀 Dramatically simplified codebase

## Success Metrics Achieved

### Quantitative Results
- **Code lines**: Reduced by 35%+
- **File count**: Reduced by 25%+
- **Server complexity**: 705 → 49 lines (93% reduction)
- **Architecture layers**: 3+ → 1 (direct access)

### Qualitative Improvements
- **Understanding time**: New developers can understand architecture in <30 minutes
- **Feature additions**: Modify only 1-2 files instead of 5-8
- **Debugging**: Direct data structure inspection
- **Maintenance**: No more service abstraction complexity

---

## 🎯 Linus-Style Development Philosophy

*"This codebase now embodies the Unix philosophy: Do one thing, do it well, and do it simply. We eliminated the Java-style over-engineering that was choking the system. The result is 10x simpler architecture that solves the same problems with direct, efficient code."*

**Remember**: Simplicity is the ultimate sophistication. Always choose the direct path over the abstracted one.

## Package Configuration

### Entry Point
```bash
# Package entry point (pyproject.toml)
code-index-mcp = "code_index_mcp.server_unified:main"
```

### Multi-Language Tree-sitter Support
The project includes tree-sitter parsers for:
- Python, JavaScript, TypeScript, Java, Go, Zig, Objective-C, C, C++, Rust

### Available Test Commands
```bash
# Quick architecture validation
python tests/test_simple_architecture.py

# Full test suite with multiple types
pytest tests/test_*.py

# Specific test categories
pytest tests/ -m unit          # Unit tests only
pytest tests/ -m integration   # Integration tests only
pytest tests/ -m "not slow"    # Skip slow tests
```

### Debugging Features
```bash
# MCP Inspector for tool debugging
npx @modelcontextprotocol/inspector uv run code-index-mcp

# Enable verbose logging
export MCP_LOG_LEVEL=debug
uv run code-index-mcp
```

- **Proactively use the CodeIndex tool for code analysis, search, read, edit and rewrite**