# Code Index MCP System Architecture

## Overview

Code Index MCP is a Model Context Protocol (MCP) server that provides intelligent code indexing, search, and analysis capabilities. The system uses a **service-oriented architecture** with Tree-sitter based parsing strategies and JSON-based persistent indexing.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Interface Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                        Service Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                   JSON Index Management                        │
├─────────────────────────────────────────────────────────────────┤
│                   Tree-sitter Strategies                       │
├─────────────────────────────────────────────────────────────────┤
│                    Search & Utils Layer                        │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. MCP Interface Layer (`server.py`)
**Purpose**: Exposes MCP tools and handles protocol communication

**Key Components**:
- MCP tool definitions (`@mcp.tool()`)
- Error handling and response formatting
- Context management and lifecycle

**MCP Tools** (12 tools total):
- `set_project_path` - Initialize project path for indexing
- `find_files` - File discovery with glob patterns
- `get_file_summary` - File analysis and complexity metrics
- `search_code_advanced` - Advanced code search with multiple backends
- `refresh_index` - Manual index rebuilding
- `get_file_watcher_status` - File monitoring status
- `configure_file_watcher` - File watcher configuration
- `get_settings_info` - System settings and debug info
- `create_temp_directory` - Temporary directory management
- `check_temp_directory` - Directory status validation
- `clear_settings` - Reset all settings and cache
- `refresh_search_tools` - Re-detect available search tools

**MCP Resources** (3 resources):
- `config://code-indexer` - Current project configuration
- `files://{file_path}` - Individual file content access
- `structure://project` - Project structure tree

### 2. Service Layer (`services/`)
**Purpose**: Business logic orchestration and workflow management

**Key Services**:
- `BaseService` - Common functionality and context management
- `ProjectManagementService` - Project lifecycle and initialization
- `SearchService` - Advanced code search with tool auto-detection
- `FileDiscoveryService` - File pattern matching and discovery
- `CodeIntelligenceService` - File analysis and symbol intelligence
- `IndexManagementService` - Index rebuild and cache operations
- `SettingsService` - Configuration and settings management
- `SystemManagementService` - File watcher and system operations

**Architecture Pattern**: Service delegation with shared context helper

### 3. JSON Index Management (`indexing/`)
**Purpose**: Persistent index storage and retrieval

**Core Components**:
- `JSONIndexManager` - Index lifecycle and persistence
- `JSONIndexBuilder` - Multi-threaded index construction
- `IndexSerializer` - JSON/msgpack serialization with fallback
- `FileWalker` - Unified file traversal logic

**Features**:
- **Performance**: Msgpack binary format with JSON fallback
- **Concurrency**: ThreadPoolExecutor for parallel processing
- **Caching**: Persistent index with incremental updates

### 4. Tree-sitter Strategies (`indexing/strategies/`)
**Purpose**: Language-specific code parsing using Tree-sitter

**Dual Strategy Architecture**:
- **Specialized Strategies** (7 languages): Full AST parsing with symbol extraction
  - `PythonParsingStrategy` - Python functions, classes, imports
  - `JavaScriptParsingStrategy` - JS/TS functions, classes, interfaces
  - `TypeScriptParsingStrategy` - TS-specific enhancements
  - `JavaParsingStrategy` - Java classes, methods, fields
  - `GoParsingStrategy` - Go functions, types, interfaces
  - `ObjectiveCParsingStrategy` - Objective-C classes, methods
  - `ZigParsingStrategy` - Zig functions, structs, enums
- **Fallback Strategy** (50+ file types): Basic file indexing
  - Handles C/C++, Rust, web files, configs, etc.
  - Provides consistent interface with minimal parsing

**Strategy Factory**: Thread-safe factory with auto-detection based on file extensions

### 5. Search & Utils Layer
**Purpose**: Code search and utility functions

**Search Engine Abstraction** (`search/`):
- **Auto-detecting hierarchy**: ugrep → ripgrep → ag → grep → basic
- **Advanced features**: Fuzzy search, regex patterns, context lines
- **Performance optimization**: Tool-specific optimizations

**Utilities** (`utils/`):
- `FileWalker` - Unified file traversal with filtering
- `PathMatcher` - Pattern matching and validation
- `ErrorHandler` - MCP error formatting and handling

## Data Flow Architecture

### File Analysis Workflow
```
User Request → Service Layer → Strategy Factory → Tree-sitter Parsing → JSON Index
```

### Index Management Workflow
```
File Changes → File Watcher → Index Management Service → JSONIndexBuilder → Persistent Cache
```

### Search Workflow
```
Search Query → Search Service → Auto-detected Tools (ugrep/ripgrep/ag/grep) → Filtered Results
```

## Implementation Details

### Index Format
```json
{
  "metadata": {
    "index_version": "2.0.0-strategy",
    "timestamp": "2025-09-18T14:55:17Z",
    "total_files": 165,
    "total_symbols": 1119
  },
  "files": {
    "file_path": {
      "symbols": {"functions": [...], "classes": [...], "imports": [...]},
      "metadata": {"language": "python", "size": 1024}
    }
  }
}
```

### Language Support Strategy

**Tree-sitter Parsing** (7 languages with full symbol extraction):
- **Python**: Functions, classes, methods, imports, decorators
- **JavaScript/TypeScript**: Functions, classes, interfaces, methods, exports
- **Java**: Classes, methods, fields, interfaces, packages
- **Go**: Functions, types, interfaces, structs, imports
- **Objective-C**: Classes, methods, protocols, properties
- **Zig**: Functions, structs, enums, unions, constants

**Fallback Strategy** (50+ file types with basic indexing):
- File-level metadata without symbol extraction
- Consistent interface for unsupported languages

**Symbol Information Captured**:
- Symbol definitions with precise line/column positions
- Import/export relationships
- Symbol types and accessibility
- Documentation strings and comments

## Configuration and Extensibility

### File Watcher System
- **Real-time monitoring**: Watchdog-based file system events
- **Debounced rebuilds**: Configurable delay for batching rapid changes
- **Smart filtering**: Excludes build dirs, temporary files, version control
- **Thread-safe**: Concurrent file monitoring and index updates

### Search Tool Auto-Detection
- **Hierarchical fallback**: ugrep → ripgrep → ag → grep → basic Python
- **Feature detection**: Automatically uses best available tool
- **Performance optimization**: Tool-specific optimizations and patterns
- **Refresh capability**: Dynamic re-detection of newly installed tools

## Performance Characteristics (Current Baseline)

### Indexing Performance
- **Index time**: 1.13s for 165 files (12% improvement with msgpack)
- **Memory usage**: 2.95 MiB peak (5% improvement)
- **Symbol extraction**: 1,119 symbols across 12 languages
- **Parallel processing**: ThreadPoolExecutor for concurrent file analysis
- **Caching**: Msgpack binary format with JSON fallback

### Search Performance
- **Advanced tools**: ugrep (preferred), ripgrep, ag, grep backends
- **Pattern optimization**: Glob-based file filtering and regex support
- **Context support**: Configurable before/after line context
- **Large datasets**: Efficient handling of large codebases

## Error Handling and Reliability

### Fault Tolerance
- **Graceful degradation**: Continue indexing on individual file failures
- **Error isolation**: Per-file error boundaries
- **Recovery mechanisms**: Automatic retry on transient failures
- **Comprehensive logging**: Debug and audit trail support

### Validation
- **Input sanitization**: Path traversal protection
- **Range validation**: SCIP position boundary checking
- **Schema validation**: Protocol buffer structure verification

## Future Architecture Considerations

### Planned Enhancements
1. **Function Call Relationships**: Complete call graph analysis
2. **Type Information**: Enhanced semantic analysis
3. **Cross-repository Navigation**: Multi-project symbol resolution
4. **Language Server Protocol**: LSP compatibility layer
5. **Distributed Indexing**: Horizontal scaling support

### Extension Points
- **Custom strategies**: Plugin architecture for new languages
- **Analysis plugins**: Custom symbol analyzers
- **Export formats**: Multiple output format support
- **Integration APIs**: External tool connectivity

## Directory Structure

```
src/code_index_mcp/
├── server.py                   # MCP interface layer (12 tools, 3 resources)
├── services/                   # Business logic services
│   ├── base_service.py         # Common service functionality
│   ├── project_management_service.py
│   ├── search_service.py       # Advanced search with tool detection
│   ├── file_discovery_service.py
│   ├── code_intelligence_service.py
│   ├── index_management_service.py
│   ├── settings_service.py
│   └── system_management_service.py
├── indexing/                   # JSON index management
│   ├── json_index_manager.py   # Index lifecycle and persistence
│   ├── json_index_builder.py   # Multi-threaded index construction
│   ├── serialization.py        # Msgpack/JSON serialization
│   └── strategies/             # Language-specific parsing
│       ├── strategy_factory.py # Thread-safe strategy selection
│       ├── python_strategy.py  # Tree-sitter Python parsing
│       ├── javascript_strategy.py
│       ├── typescript_strategy.py
│       ├── java_strategy.py
│       ├── go_strategy.py
│       ├── objective_c_strategy.py
│       ├── zig_strategy.py
│       └── fallback_strategy.py # Basic file indexing
├── search/                     # Search engine abstraction
│   ├── advanced_search_strategy.py
│   └── basic_search_strategy.py
├── utils/                      # Shared utilities
│   ├── file_walker.py          # Unified file traversal
│   ├── path_matcher.py         # Pattern matching
│   └── error_handler.py        # MCP error handling
├── tools/                      # Legacy tool components
├── project_settings.py         # Project configuration
└── constants.py                # System constants
```

## Key Design Principles

1. **Service-Oriented Architecture**: Clear separation of business logic in services
2. **Language Strategy Pattern**: Extensible parsing with Tree-sitter strategies
3. **Performance Optimization**: Multi-threading, caching, and tool auto-detection
4. **Reliability**: Fault-tolerant with comprehensive error handling and validation
5. **MCP Protocol Compliance**: Full MCP tool and resource implementation
6. **Maintainability**: Modular design with shared utilities and base classes

## Quality Metrics (Current Status)

- **Pylint Score**: 9.14/10 (+1.09 improvement)
- **MyPy Errors**: 56 (maintained baseline, zero regressions)
- **Test Coverage**: 36% with 29/30 tests passing
- **Index Performance**: 1.13s for 165 files, 1,119 symbols
- **Memory Usage**: 2.95 MiB peak (5% improvement with optimizations)

---

*Last updated: 2025-09-18*
*Architecture version: 2.0.0-strategy*