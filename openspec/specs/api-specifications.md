# API Specifications

## Overview

This document defines the complete API specification for Code Index MCP, including all MCP tools, data models, and response formats. The API follows Linus-style design principles with unified interfaces and direct data manipulation.

## Core Architecture

### Unified Tool Interface

All operations are accessed through a single unified interface that eliminates special cases and provides consistent behavior across all functionality.

```python
def unified_tool(operation: str, **params) -> Dict[str, Any]:
    """
    Single entry point for all Code Index MCP operations.
    
    Args:
        operation: The specific operation to perform
        **params: Operation-specific parameters
        
    Returns:
        Dictionary with success status and operation-specific data
    """
```

### Response Format Standard

All API responses follow a consistent format:

```python
{
    "success": bool,           # Operation success status
    "error": str | None,       # Error message if success=False
    # Operation-specific fields...
}
```

## Core Tools API

### Project Management

#### set_project_path

**Purpose**: Initialize project and set working directory.

**Signature**:
```python
def set_project_path(path: str) -> Dict[str, Any]
```

**Parameters**:
- `path` (str): Absolute path to project directory

**Response**:
```python
{
    "success": True,
    "path": "/path/to/project",
    "files_indexed": 1250,
    "symbols_indexed": 8432
}
```

**Error Response**:
```python
{
    "success": False,
    "error": "Directory does not exist: /invalid/path"
}
```

### Search Operations

#### search_code

**Purpose**: Unified search across all file types and content.

**Signature**:
```python
def search_code(
    pattern: str,
    search_type: str = "text",
    file_pattern: Optional[str] = None,
    case_sensitive: bool = True
) -> Dict[str, Any]
```

**Parameters**:
- `pattern` (str): Search pattern (text or regex)
- `search_type` (str): "text", "regex", "symbol", "references", "definition"
- `file_pattern` (Optional[str]): Glob pattern for file filtering
- `case_sensitive` (bool): Case sensitivity flag

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/main.py",
            "line": 42,
            "column": 15,
            "content": "def search_function():",
            "context": "    def search_function():\n        # Search logic"
        }
    ],
    "total_count": 15,
    "search_time": 0.023,
    "query_type": "text"
}
```

#### find_files

**Purpose**: Find files by name pattern.

**Signature**:
```python
def find_files(pattern: str) -> Dict[str, Any]
```

**Parameters**:
- `pattern` (str): Glob pattern for file matching

**Response**:
```python
{
    "success": True,
    "files": [
        "src/main.py",
        "tests/test_main.py",
        "docs/main.md"
    ],
    "count": 3
}
```

### File Operations

#### get_file_content

**Purpose**: Retrieve file content with optional line ranges.

**Signature**:
```python
def get_file_content(
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    show_line_numbers: bool = False
) -> Dict[str, Any]
```

**Parameters**:
- `file_path` (str): Path to file
- `start_line` (Optional[int]): Starting line number (1-based)
- `end_line` (Optional[int]): Ending line number (inclusive)
- `show_line_numbers` (bool): Include line numbers in response

**Response**:
```python
{
    "success": True,
    "file_path": "src/main.py",
    "content": [
        "def main():",
        "    print('Hello, World!')",
        "    return 0"
    ],
    "total_lines": 3,
    "language": "python",
    "encoding": "utf-8",
    "start_line": 1,
    "end_line": 3,
    "line_numbers": [1, 2, 3]  # Only if show_line_numbers=True
}
```

#### get_file_summary

**Purpose**: Get file metadata and statistics.

**Signature**:
```python
def get_file_summary(file_path: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "file_path": "src/main.py",
    "language": "python",
    "line_count": 125,
    "symbol_count": 8,
    "imports": ["os", "sys", "typing"],
    "exports": ["main", "helper_function"]
}
```

### Symbol Operations

#### get_symbol_body

**Purpose**: Extract complete syntax body for symbols.

**Signature**:
```python
def get_symbol_body(
    symbol_name: str,
    file_path: Optional[str] = None,
    language: str = "auto",
    show_line_numbers: bool = False
) -> Dict[str, Any]
```

**Parameters**:
- `symbol_name` (str): Name of symbol to extract
- `file_path` (Optional[str]): Specific file to search in
- `language` (str): Language hint ("auto", "python", "javascript", etc.)
- `show_line_numbers` (bool): Include line numbers

**Response**:
```python
{
    "success": True,
    "symbol_name": "search_function",
    "symbol_type": "function",
    "file_path": "src/search.py",
    "language": "python",
    "start_line": 15,
    "end_line": 28,
    "body_lines": [
        "def search_function(pattern: str) -> List[str]:",
        "    \"\"\"Search for pattern in files.\"\"\"",
        "    results = []",
        "    for file_path in get_files():",
        "        if pattern in file_path.read_text():",
        "            results.append(file_path)",
        "    return results"
    ],
    "signature": "search_function(pattern: str) -> List[str]",
    "total_lines": 14,
    "line_numbers": [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
}
```

#### rename_symbol

**Purpose**: Safely rename symbols across all files.

**Signature**:
```python
def rename_symbol(old_name: str, new_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "files_changed": 5,
    "error": None
}
```

### Edit Operations

#### apply_edit

**Purpose**: Apply atomic edit operations with backup.

**Signature**:
```python
def apply_edit(
    file_path: str,
    old_content: str,
    new_content: str
) -> Dict[str, Any]
```

**Parameters**:
- `file_path` (str): Target file path
- `old_content` (str): Exact content to replace
- `new_content` (str): New content to insert

**Response**:
```python
{
    "success": True,
    "error": None,
    "files_changed": 1
}
```

#### add_import

**Purpose**: Add import statements with intelligent positioning.

**Signature**:
```python
def add_import(file_path: str, import_statement: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "files_changed": 1,
    "error": None
}
```

### Index Management

#### get_index_stats

**Purpose**: Get comprehensive index statistics.

**Signature**:
```python
def get_index_stats() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "files_indexed": 1250,
    "symbols_indexed": 8432,
    "languages": {
        "python": 450,
        "javascript": 320,
        "typescript": 280,
        "java": 200
    },
    "index_size_mb": 45.2,
    "last_update": "2025-01-15T10:30:00Z"
}
```

#### refresh_index

**Purpose**: Update index with incremental changes.

**Signature**:
```python
def refresh_index() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "files_indexed": 1255,
    "symbols_indexed": 8450,
    "update_stats": {
        "files_added": 5,
        "files_modified": 12,
        "files_removed": 2,
        "symbols_added": 18,
        "symbols_modified": 25,
        "symbols_removed": 5
    },
    "update_time": 0.156,
    "method": "incremental"
}
```

## Semantic Search API

### Reference Operations

#### find_references

**Purpose**: Find all references to a symbol.

**Signature**:
```python
def find_references(symbol_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/main.py",
            "line": 42,
            "column": 10,
            "content": "result = search_function(query)",
            "context": "    # Search for the query\n    result = search_function(query)\n    return result"
        }
    ],
    "total_count": 8,
    "search_time": 0.045
}
```

#### find_definition

**Purpose**: Find symbol definition location.

**Signature**:
```python
def find_definition(symbol_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/search.py",
            "line": 15,
            "column": 4,
            "content": "def search_function(pattern: str) -> List[str]:",
            "context": "def search_function(pattern: str) -> List[str]:\n    \"\"\"Search for pattern in files.\"\"\""
        }
    ],
    "total_count": 1
}
```

#### find_callers

**Purpose**: Find all functions that call a specific function.

**Signature**:
```python
def find_callers(function_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/main.py",
            "line": 42,
            "column": 15,
            "function": "main",
            "content": "results = search_function(query)"
        }
    ],
    "total_count": 3
}
```

#### find_implementations

**Purpose**: Find implementations of interfaces or abstract classes.

**Signature**:
```python
def find_implementations(interface_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/concrete.py",
            "line": 25,
            "column": 14,
            "class": "ConcreteImplementation",
            "content": "class ConcreteImplementation(MyInterface):"
        }
    ],
    "total_count": 2
}
```

#### find_hierarchy

**Purpose**: Find inheritance and type hierarchy.

**Signature**:
```python
def find_hierarchy(symbol_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "matches": [
        {
            "file_path": "src/interface.py",
            "line": 10,
            "relationship": "parent",
            "symbol": "BaseInterface"
        },
        {
            "file_path": "src/concrete.py",
            "line": 25,
            "relationship": "child",
            "symbol": "ConcreteImplementation"
        }
    ],
    "total_count": 2
}
```

## SCIP Protocol API

### SCIP Symbol Operations

#### generate_scip_symbol_id

**Purpose**: Generate SCIP-compliant symbol identifiers.

**Signature**:
```python
def generate_scip_symbol_id(
    symbol_name: str,
    file_path: str,
    language: str,
    symbol_type: str = "unknown"
) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "symbol_id": "myproject/src/main.py/MyClass.method_",
    "symbol_name": "method",
    "file_path": "src/main.py",
    "language": "python",
    "symbol_type": "method"
}
```

#### find_scip_symbol

**Purpose**: Find symbols using SCIP protocol.

**Signature**:
```python
def find_scip_symbol(symbol_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "symbol_name": "search_function",
    "matches": [
        {
            "symbol_id": "myproject/src/search.py/search_function_",
            "name": "search_function",
            "language": "python",
            "file_path": "src/search.py",
            "line": 15,
            "column": 4,
            "symbol_type": "function",
            "signature": "search_function(pattern: str) -> List[str]",
            "documentation": "Search for pattern in files."
        }
    ],
    "match_count": 1
}
```

#### get_cross_references

**Purpose**: Get cross-file symbol references.

**Signature**:
```python
def get_cross_references(symbol_name: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "symbol_name": "search_function",
    "references_by_file": {
        "src/main.py": [
            {
                "symbol_id": "myproject/src/search.py/search_function_",
                "line": 42,
                "column": 15,
                "occurrence_type": "reference",
                "context": "result = search_function(query)"
            }
        ],
        "tests/test_search.py": [
            {
                "symbol_id": "myproject/src/search.py/search_function_",
                "line": 10,
                "column": 8,
                "occurrence_type": "reference",
                "context": "assert search_function('test') != []"
            }
        ]
    },
    "total_references": 2,
    "files_with_references": 2
}
```

#### get_symbol_graph

**Purpose**: Get complete symbol relationship graph.

**Signature**:
```python
def get_symbol_graph(symbol_id: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "symbol_id": "myproject/src/search.py/search_function_",
    "symbol": {
        "name": "search_function",
        "language": "python",
        "file_path": "src/search.py",
        "line": 15,
        "symbol_type": "function",
        "signature": "search_function(pattern: str) -> List[str]"
    },
    "definitions": [
        {
            "file_path": "src/search.py",
            "line": 15,
            "column": 4,
            "occurrence_type": "definition"
        }
    ],
    "references": [
        {
            "file_path": "src/main.py",
            "line": 42,
            "column": 15,
            "occurrence_type": "reference",
            "context": "result = search_function(query)"
        }
    ],
    "cross_file_usage": true,
    "definition_count": 1,
    "reference_count": 3
}
```

#### export_scip_index

**Purpose**: Export index in SCIP format.

**Signature**:
```python
def export_scip_index() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "scip_index": {
        "metadata": {
            "version": "0.3.0",
            "tool_info": {
                "name": "code-index-mcp",
                "version": "2.3.2"
            }
        },
        "documents": [...],
        "external_symbols": [...]
    },
    "metadata": {
        "version": "0.3.0",
        "tool_info": {...}
    },
    "document_count": 1250,
    "external_symbols_count": 8432
}
```

#### process_file_with_scip

**Purpose**: Process individual file with SCIP.

**Signature**:
```python
def process_file_with_scip(
    file_path: str,
    language: Optional[str] = None
) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "file_path": "src/main.py",
    "language": "python",
    "symbols_processed": 8,
    "occurrences_created": 15,
    "external_symbols": 3,
    "document": {
        "relative_path": "src/main.py",
        "language": "python",
        "symbols": [
            {
                "symbol_id": "myproject/src/main.py/main_",
                "name": "main",
                "symbol_type": "function",
                "line": 1,
                "signature": "main() -> int"
            }
        ]
    }
}
```

## System Operations

### Utility Functions

#### check_file_exists

**Purpose**: Check if file exists and is indexed.

**Signature**:
```python
def check_file_exists(file_path: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "exists": true,
    "full_path": "/full/path/to/src/main.py",
    "in_index": true
}
```

### Incremental Index Operations

#### update_incrementally

**Purpose**: Force incremental index update.

**Signature**:
```python
def update_incrementally() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "update_stats": {
        "files_added": 5,
        "files_modified": 12,
        "files_removed": 2,
        "symbols_added": 18,
        "symbols_modified": 25,
        "symbols_removed": 5
    },
    "update_time": 0.156,
    "files_indexed": 1255,
    "symbols_indexed": 8450
}
```

#### force_update_file

**Purpose**: Force update specific file.

**Signature**:
```python
def force_update_file(file_path: str) -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "file_path": "src/main.py",
    "files_indexed": 1255,
    "symbols_indexed": 8450
}
```

#### get_changed_files

**Purpose**: Get list of changed files.

**Signature**:
```python
def get_changed_files() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "changed_files": [
        "src/main.py",
        "tests/test_main.py",
        "docs/README.md"
    ],
    "stats": {
        "total_files": 1250,
        "changed_files": 3,
        "last_check": "2025-01-15T10:30:00Z"
    }
}
```

#### full_rebuild_index

**Purpose**: Complete index rebuild.

**Signature**:
```python
def full_rebuild_index() -> Dict[str, Any]
```

**Response**:
```python
{
    "success": True,
    "files_indexed": 1250,
    "symbols_indexed": 8432,
    "rebuild_time": 2.456,
    "method": "full_rebuild"
}
```

## Data Models

### FileInfo

```python
@dataclass
class FileInfo:
    path: str
    language: str
    line_count: int
    symbol_count: int
    imports: List[str]
    exports: List[str]
    last_modified: float
    hash: str
```

### SymbolInfo

```python
@dataclass
class SymbolInfo:
    name: str
    type: str  # function, class, method, variable
    file: str
    line: int
    column: int
    signature: str
    documentation: Optional[str]
    symbol_id: Optional[str]  # SCIP ID
```

### SearchResult

```python
@dataclass
class SearchResult:
    file_path: str
    line: int
    column: int
    content: str
    context: str
    match_type: str
```

### SearchQuery

```python
@dataclass
class SearchQuery:
    pattern: str
    type: str  # text, regex, symbol, references
    file_pattern: Optional[str]
    case_sensitive: bool
    max_results: int = 100
```

## Error Handling

### Standard Error Responses

All errors follow the standard response format:

```python
{
    "success": False,
    "error": "Human-readable error message"
}
```

### Common Error Types

**File System Errors:**
- `"File not found: {path}"`
- `"Permission denied: {path}"`
- `"Directory does not exist: {path}"`

**Validation Errors:**
- `"Invalid value: {details}"`
- `"Required parameter missing: {param}"`

**Index Errors:**
- `"No project path set"`
- `"Symbol not found: {symbol}"`
- `"File not indexed: {path}"`

**System Errors:**
- `"Memory limit exceeded"`
- `"Index corrupted"`
- `"Operation timeout"`

## Performance Considerations

### Response Time Targets

- **File operations**: <50ms
- **Search operations**: <500ms
- **Symbol operations**: <200ms
- **Index updates**: <1s (incremental), <5s (full rebuild)

### Memory Usage

- **Base memory**: 50MB
- **Per 1K files**: +10MB
- **Per 10K symbols**: +5MB
- **Automatic cleanup**: 80% memory threshold

### Caching Strategy

- **File content**: LRU cache, 100MB limit
- **Search results**: 5-minute TTL
- **Symbol metadata**: Persistent cache
- **Index data**: Incremental updates only

## Integration Examples

### Basic Usage

```python
# Initialize project
result = unified_tool("set_project_path", path="/path/to/project")

# Search for code
result = unified_tool("search_code", pattern="def test_", search_type="text")

# Get file content
result = unified_tool("get_file_content", file_path="src/main.py", start_line=1, end_line=10)

# Extract symbol
result = unified_tool("get_symbol_body", symbol_name="main_function")
```

### Advanced Usage

```python
# Semantic search
result = unified_tool("find_references", symbol_name="MyClass")

# SCIP operations
result = unified_tool("generate_scip_symbol_id", 
                     symbol_name="method", 
                     file_path="src/class.py", 
                     language="python")

# Atomic edit
result = unified_tool("apply_edit", 
                     file_path="src/main.py",
                     old_content="old line",
                     new_content="new line")
```

This API specification provides a comprehensive reference for all Code Index MCP functionality, ensuring consistent behavior and clear interfaces for AI assistant integration.