# Technical Specifications

## Project Overview

**Code Index MCP** is a Model Context Protocol server implementing Linus Torvalds' design philosophy for intelligent code indexing and analysis. The project provides semantic code analysis, cross-file symbol tracking, and AI-powered refactoring capabilities with SCIP protocol support.

### Current State Analysis

**Code Metrics:**
- **Source Files**: 42 Python files
- **Core Modules**: 15 core modules, 8 MCP modules, 6 indexing modules
- **Test Files**: 8 test files + sample projects for 8 languages
- **Version**: 2.3.2 (production-ready)
- **Dependencies**: 15 core dependencies, 8 dev dependencies

**Architecture Compliance:**
- ✅ **File Size**: All files under 200 lines (verified)
- ✅ **Function Length**: All functions under 30 lines (verified)
- ✅ **Linus Principles**: Direct data manipulation, no service abstractions
- ✅ **Unified Interface**: Single `unified_tool()` replaces 30+ specialized tools

## Architecture Specifications

### Core Design Philosophy

**Linus-style Architecture Principles:**
1. **Direct Data Manipulation**: No service abstractions, unified data structures only
2. **"Good Taste"**: Unified interfaces eliminate if/else chains
3. **"Never Break Userspace"**: Backward-compatible MCP tools
4. **"Pragmatism First"**: Solve real problems, not theoretical ones
5. **"Simplicity Obsession"**: <200 lines per file, <3 indentation levels

### Module Structure

```
src/
├── core/                    # Core functionality (15 modules)
│   ├── tool_registry.py     # Unified tool registry
│   ├── mcp_tools.py         # MCP tool implementations
│   ├── edit_operations.py   # File editing operations
│   ├── backup.py           # Backup and recovery
│   ├── index.py            # Code indexing engine
│   ├── search.py           # Search functionality
│   ├── memory_monitor.py   # Memory management
│   └── ...
├── code_index_mcp/         # MCP server layer (8 modules)
│   ├── server_unified.py   # Main MCP server
│   ├── indexing/           # Indexing strategies
│   ├── tools/              # Tool configurations
│   └── config.py           # Configuration management
└── tests/                  # Comprehensive test suite
```

### Key Patterns

**Unified Tool Interface:**
```python
# Single entry point for all operations
def unified_tool(operation: str, **params) -> Dict[str, Any]:
    return execute_tool(operation, **params)
```

**Operation Registry:**
```python
# Function dispatch eliminates conditional chains
def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    tools = get_tool_registry()
    tool_func = tools.get(tool_name)
    return tool_func(**kwargs)
```

**Atomic Operations:**
- Edit/search/index operations with automatic rollback
- Incremental updates using xxhash comparison
- Direct tool access with zero abstraction layers

## Technology Stack

### Core Dependencies

**Runtime Requirements:**
- **Python**: 3.10+ (required)
- **MCP Framework**: mcp>=0.3.0
- **Parsing Engine**: tree-sitter>=0.20.0 with multi-language support
- **Protocol Support**: SCIP (Source Code Intelligence Protocol)

**Language Parsers:**
- Python, JavaScript, TypeScript, Java, Go, Zig, Rust, C/C++
- Fallback strategy for 40+ additional file types

**System Libraries:**
- `watchdog>=3.0.0` - File system monitoring
- `psutil>=5.9.0` - System resource monitoring
- `msgpack>=1.0.0` - Efficient serialization
- `xxhash>=3.0.0` - Fast file hashing

### Development Tools

**Quality Assurance:**
- `mypy>=1.0.0` - Type checking
- `pytest>=7.0.0` - Testing framework
- `black>=25.9.0` - Code formatting
- `ruff>=0.14.0` - Linting and formatting
- `pylint>=4.0.1` - Additional linting

## Code Standards

### Formatting Rules

**File Structure:**
- Maximum 200 lines per file
- Maximum 3 indentation levels
- Maximum 100 characters per line
- Functions under 30 lines

**Naming Conventions:**
- `snake_case` for variables and functions
- `PascalCase` for classes
- `UPPER_CASE` for constants

**Import Organization:**
```python
# Standard library imports
import os
import sys
from typing import Any, Dict, Optional

# Third-party imports
from mcp.server.fastmcp import FastMCP

# Local imports
from core.tool_registry import get_tool_registry
```

### Data Structures

**Preferred Patterns:**
- Use `dataclasses` for data structures
- Use `Optional[T]` for nullable fields
- Use `Dict[str, Any]` for generic mappings
- Direct error raising, no wrapper exceptions

**Example:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileInfo:
    path: str
    size: int
    hash: str
    last_modified: Optional[float] = None
```

### Error Handling

**Guidelines:**
- Validate inputs early
- Direct error raising, no wrapper exceptions
- Use standard exception types
- Include meaningful error messages

**Example:**
```python
def process_file(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.endswith('.py'):
        raise ValueError(f"Unsupported file type: {file_path}")
    
    # Process file...
```

## Performance Requirements

### Memory Management

**Constraints:**
- Automatic cleanup at 80% memory threshold
- Efficient handling of large codebases (>10K files)
- LRU caching for frequently accessed data
- Incremental updates to minimize memory usage

### Response Times

**Targets:**
- Sub-second response times for common operations
- File indexing: <100ms per file
- Search operations: <500ms
- Edit operations: <50ms

### Scalability

**Requirements:**
- Support for projects with 10K+ files
- Multi-language codebases
- Concurrent file operations
- Efficient incremental updates

## Security Considerations

### File System Access

**Guidelines:**
- Validate all file paths
- Prevent directory traversal attacks
- Respect file system permissions
- Handle file locking properly

### Data Protection

**Requirements:**
- No logging of sensitive content
- Secure handling of file paths
- Memory cleanup after operations
- Safe serialization/deserialization

## Testing Strategy

### Test Organization

**Structure:**
```
tests/
├── unit/                   # Unit tests (@pytest.mark.unit)
├── integration/            # Integration tests (@pytest.mark.integration)
├── performance/            # Performance tests (@pytest.mark.slow)
└── sample-projects/        # Test data for multiple languages
```

### Coverage Requirements

**Targets:**
- 95%+ coverage for core functionality
- 100% coverage for critical paths
- All error conditions tested
- Performance benchmarks included

### Test Categories

**Unit Tests:**
- Individual component testing
- Mock external dependencies
- Fast execution (<1s per test)

**Integration Tests:**
- Cross-component functionality
- Real file system operations
- End-to-end workflows

**Performance Tests:**
- Memory usage validation
- Response time benchmarks
- Large codebase handling

## Quality Assurance

### Type Checking

**Configuration:**
```toml
[tool.mypy]
python_version = "3.10"
packages = ["src/code_index_mcp"]
ignore_missing_imports = true
warn_return_any = true
disallow_untyped_defs = false
check_untyped_defs = true
```

### Code Quality

**Tools:**
- **Black**: Code formatting
- **Ruff**: Linting and formatting
- **Pylint**: Additional quality checks
- **MyPy**: Type checking

**Pre-commit Hooks:**
- Automatic formatting
- Type checking
- Linting validation
- Test execution

## Documentation Standards

### Code Documentation

**Requirements:**
- Module-level docstrings
- Function documentation with parameters
- Type hints for all public APIs
- Usage examples for complex operations

**Example:**
```python
def search_code(pattern: str, search_type: str = "text") -> Dict[str, Any]:
    """
    Search for code patterns across the project.
    
    Args:
        pattern: Search pattern (regex or text)
        search_type: Type of search ("text", "regex", "symbol")
        
    Returns:
        Dictionary with search results and metadata
        
    Raises:
        ValueError: If search_type is invalid
    """
```

### API Documentation

**Requirements:**
- Complete API reference
- Usage examples
- Error handling documentation
- Performance characteristics

## Deployment Specifications

### Environment Requirements

**Minimum Requirements:**
- Python 3.10+
- 2GB RAM (4GB recommended)
- 1GB disk space
- Network access for package installation

### Installation

**Standard Installation:**
```bash
pip install code-index-mcp
```

**Development Installation:**
```bash
git clone https://github.com/johnhuang316/code-index-mcp
cd code-index-mcp
uv sync --dev
```

### Configuration

**Default Configuration:**
- Memory limit: 80% of available RAM
- Cache size: 100MB
- Index update interval: 5 seconds
- File watching: Enabled

## Maintenance Guidelines

### Release Process

**Version Management:**
- Semantic versioning (MAJOR.MINOR.PATCH)
- Backward compatibility maintained
- Changelog updated for each release
- Tagged releases in Git

### Update Strategy

**Incremental Updates:**
- Only reprocess changed files
- Maintain backward compatibility
- Graceful degradation for errors
- Automatic recovery mechanisms

### Monitoring

**Metrics to Track:**
- Memory usage patterns
- Response time distributions
- Error rates and types
- User adoption metrics

## Future Extensibility

### Plugin Architecture

**Design Principles:**
- Language-agnostic core
- Pluggable parsing strategies
- Extensible tool registry
- Configurable behavior

### Integration Points

**Supported Integrations:**
- IDE plugins
- Build system integration
- CI/CD pipeline integration
- External tool compatibility

This technical specification serves as the authoritative reference for Code Index MCP development, ensuring consistency, quality, and maintainability across all project components.