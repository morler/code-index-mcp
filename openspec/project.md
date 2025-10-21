# Project Context

## Purpose
Code Index MCP is a Model Context Protocol server implementing Linus Torvalds' design philosophy for intelligent code indexing and analysis. The project provides semantic code analysis, cross-file symbol tracking, and AI-powered refactoring capabilities with SCIP protocol support. It aims to eliminate unnecessary abstractions while providing maximum performance for AI code analysis tasks.

## Tech Stack
- **Primary Language**: Python 3.10+
- **Core Framework**: Model Context Protocol (MCP) server
- **Parsing Engine**: Tree-sitter with multi-language support
- **Protocol Support**: SCIP (Source Code Intelligence Protocol)
- **Key Dependencies**:
  - `mcp>=0.3.0` - Model Context Protocol server framework
  - `tree-sitter>=0.20.0` - AST parsing for multiple languages
  - `watchdog>=3.0.0` - File system monitoring
  - `msgpack>=1.0.0` - Efficient serialization
  - `xxhash>=3.0.0` - Fast file hashing
  - `psutil>=5.9.0` - System resource monitoring
- **Development Tools**: uv package manager, pytest, mypy, black, ruff

## Project Conventions

### Code Style
**Linus-style Architecture Principles:**
- **Direct Data Manipulation**: No service abstractions, unified data structures only
- **File Size Limit**: Maximum 200 lines per file
- **Indentation**: Maximum 3 indentation levels
- **Function Length**: Functions under 30 lines
- **Line Length**: Maximum 100 characters
- **Naming Conventions**: 
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
- **Import Organization**: Group stdlib, third-party, local imports with `TYPE_CHECKING` for type hints
- **Data Structures**: Use dataclasses for data structures, `Optional[T]` for nullable fields
- **Error Handling**: Direct error raising, no wrapper exceptions, validate inputs early

### Architecture Patterns
**Core Design Philosophy:**
- **"Good Taste"**: Unified interfaces eliminate if/else chains
- **"Never Break Userspace"**: Backward-compatible MCP tools
- **"Pragmatism First"**: Solve real problems, not theoretical ones
- **"Simplicity Obsession"**: <200 lines per file, <3 indentation levels

**Key Patterns:**
- **Unified Tool Interface**: Single `unified_tool()` function handles 30+ specialized operations
- **Operation Registry**: Function dispatch eliminates conditional chains
- **Atomic Operations**: Edit/search/index operations with automatic rollback
- **Incremental Updates**: Only reprocess changed files using xxhash comparison
- **Direct Tool Access**: Zero abstraction layers between MCP and core functionality

### Testing Strategy
**Testing Framework**: pytest with comprehensive markers
- **Unit Tests**: `@pytest.mark.unit` - Individual component testing
- **Integration Tests**: `@pytest.mark.integration` - Cross-component functionality
- **Performance Tests**: `@pytest.mark.slow` - Memory and performance benchmarks
- **Coverage Requirements**: Full coverage of core indexing and search functionality
- **Test Organization**: Separate test files for each major component
- **Mock Strategy**: Mock external dependencies (file system, network calls)

**Quality Assurance:**
- Type checking with MyPy
- Code formatting with Black and Ruff
- Linting with Pylint
- Coverage reporting with pytest-cov

### Git Workflow
**Branching Strategy**: 
- **Main Branch**: `main` - Stable releases
- **Development**: Feature branches from main
- **Contribution**: Pull requests with code review

**Commit Conventions**:
- **Format**: Conventional commits with clear purpose
- **Language**: Chinese for conversations, English for documentation
- **Documentation**: Markdown format for all documentation
- **No Heredoc**: Avoid heredoc in git commit messages

## Domain Context

**Code Analysis Domain:**
- **Multi-Language Support**: Python, JavaScript, TypeScript, Java, Go, Zig, Objective-C with Tree-sitter AST parsing
- **Fallback Strategy**: Basic indexing for 40+ additional file types
- **SCIP Protocol**: Industry-standard symbol identification and cross-file references
- **Semantic Analysis**: Function extraction, class hierarchies, call relationship tracking
- **Symbol Operations**: Definition/reference tracking, cross-file renaming, import management

**AI Assistant Integration:**
- **MCP Protocol**: Standardized interface for AI model interaction
- **Tool Registry**: Dynamic tool registration and execution
- **Performance Optimization**: LRU caching, incremental updates, memory management
- **Error Recovery**: Automatic rollback and backup mechanisms

## Important Constraints

**Technical Constraints:**
- **Memory Management**: Automatic cleanup at 80% threshold
- **Performance**: Sub-second response times for common operations
- **Compatibility**: Python 3.10+ required, MCP protocol compliance
- **File Limits**: Efficient handling of large codebases (>10K files)
- **Language Support**: Tree-sitter parser availability for core languages

**Design Constraints:**
- **Linus Principles**: No service abstractions, direct data manipulation only
- **File Size**: Strict <200 lines per file limit
- **Complexity**: Maximum 3 indentation levels
- **Dependencies**: Minimal external dependencies, prefer built-in solutions

**Business Constraints:**
- **Open Source**: MIT License, community-driven development
- **Backward Compatibility**: Maintain MCP tool compatibility
- **Documentation**: Comprehensive English documentation with Chinese development discussions

## External Dependencies

**Core Runtime Dependencies:**
- **MCP Framework**: Model Context Protocol server implementation
- **Tree-sitter Parsers**: Language-specific AST parsers (Python, JS/TS, Java, Go, Zig, Rust, C/C++)
- **System Libraries**: psutil for system monitoring, watchdog for file system events

**Development Dependencies:**
- **Package Management**: uv for fast dependency resolution
- **Quality Tools**: mypy, pytest, black, ruff, pylint
- **Documentation**: Markdown-based documentation system

**Protocol Dependencies:**
- **SCIP Protocol**: Source Code Intelligence Protocol for semantic analysis
- **MCP Protocol**: Model Context Protocol for AI assistant integration
- **File System**: Standard file system APIs with cross-platform compatibility

**Optional Integrations:**
- **External Tools**: SCIP index export for external tool compatibility
- **IDE Integration**: Support for various IDE configurations
- **Build Systems**: Integration with common build tools (Make, pyproject.toml)
