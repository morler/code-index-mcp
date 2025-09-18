# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Code Index MCP is a Model Context Protocol server that provides intelligent code indexing, search, and analysis capabilities for Large Language Models. It bridges the gap between AI models and complex codebases through advanced AST parsing and search tools.

**Core Architecture**: Service-oriented design with MCP decorators delegating to domain-specific services for business logic.

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

# Alternative development runner
python run.py
```

### Testing and Debugging
```bash
# Debug with MCP Inspector
npx @modelcontextprotocol/inspector uv run code-index-mcp

# Alternative pip installation (if needed)
pip install code-index-mcp
```

### Dependencies Management
- **Build system**: setuptools
- **Package manager**: uv (recommended) or pip
- **Python version**: 3.10+
- **Key dependencies**: mcp, watchdog, tree-sitter libraries, pathspec, msgpack

## Architecture Overview

### Service Layer Architecture
The project uses a **service-oriented architecture** where MCP tool decorators delegate to specialized services:

- **BaseService**: Abstract base providing common functionality (context management, validation, path helpers)
- **Domain Services**: Specialized services for different concerns
  - `ProjectManagementService`: Project initialization and configuration
  - `SearchService`: Advanced code search with multiple tool backends
  - `FileDiscoveryService`: File pattern matching and discovery
  - `CodeIntelligenceService`: File analysis and complexity metrics
  - `IndexManagementService`: Index rebuilding and management
  - `SettingsService`: Configuration and settings management
  - `SystemManagementService`: File watcher and system configuration

### Parsing Strategy Pattern
**Dual-strategy architecture** for language support:

1. **Specialized Tree-sitter Strategies** (7 languages):
   - Python, JavaScript, TypeScript, Java, Go, Objective-C, Zig
   - Full AST parsing with accurate symbol extraction
   - Located in `src/code_index_mcp/indexing/strategies/`

2. **Fallback Strategy** (50+ file types):
   - Basic file indexing for all other languages and file types
   - Handles C/C++, Rust, web files, databases, configs, etc.
   - Provides consistent interface despite different parsing depth

**StrategyFactory**: Thread-safe factory managing strategy initialization and selection based on file extensions.

### Search Engine Abstraction
**Auto-detecting search tool hierarchy**:
- **ugrep** (preferred): Native fuzzy search, best performance
- **ripgrep**: Fast regex search, cross-platform
- **ag (Silver Searcher)**: Alternative fast search
- **grep**: Basic fallback
- **basic**: Pure Python fallback

Search tools automatically selected based on availability and feature requirements.

### Key Components

#### Index Management
- **Persistent caching**: Uses msgpack for efficient serialization
- **File watcher**: Real-time monitoring with debounced updates
- **Smart filtering**: Excludes build dirs, temporary files automatically
- **Cross-platform**: Native OS file system monitoring

#### MCP Integration
- **Resources**: Project config, file content, structure trees
- **Tools**: 12 specialized tools for indexing, search, analysis, management
- **Prompts**: Pre-built prompts for code analysis and search workflows
- **Context management**: Thread-safe context sharing across all services

## Important Implementation Details

### Language Strategy Extensions
When adding new language support, extensions are mapped in `StrategyFactory`:
```python
# Specialized strategies (get their own .py file)
self._strategies[ext] = SpecializedStrategy()

# Fallback strategy mappings
self._file_type_mappings = {
    '.newlang': 'language_name'
}
```

### Service Pattern Usage
All new functionality should follow the service pattern:
1. Inherit from `BaseService`
2. Use `self.helper` for context access
3. Call `self._require_project_setup()` for operations needing valid projects
4. Use `self._require_valid_file_path()` for file operations

### Thread Safety
- All services are designed to be thread-safe
- StrategyFactory uses RLock for initialization
- Index operations are synchronized through the UnifiedIndexManager

### Error Handling
- Services use `@handle_mcp_tool_errors` decorator for consistent error responses
- Validation helpers provide standardized error messages
- Fail-fast approach with clear error messages for missing dependencies

## Entry Points

- **Main server**: `src/code_index_mcp/server.py:main()`
- **Development runner**: `run.py` (adds src to path, handles dependencies)
- **Package script**: `code-index-mcp` console script via pyproject.toml

## Configuration

- **No config files required**: Server initializes with empty project path
- **Project setup**: First step is always calling `set_project_path` tool
- **File watching**: Configurable via `configure_file_watcher` tool
- **Search tools**: Auto-detected, can be refreshed via `refresh_search_tools`

## Working with the Codebase

When implementing new features:
1. Create or extend appropriate service in `services/`
2. Add MCP tool decorator in `server.py` that delegates to service method
3. Follow the established pattern of validation → business logic → response formatting
4. Test with MCP Inspector for immediate feedback
5. Consider thread safety for any shared state
- **主动使用CodeIndex工具**进行代码分析、搜索和重构
