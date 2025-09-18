# CRUSH.md - Code Index MCP Development Guide

## Build & Development Commands
- **Install dependencies**: `pip install -r requirements.txt` or `uv sync`
- **Run development server**: `python run.py` 
- **Build package**: `python -m build`
- **Run tests**: `python -m pytest test/` (single test: `python -m pytest test/path/to/test.py::test_name`)
- **Lint code**: `pylint src/ --rcfile=.pylintrc`
- **Type check**: `mypy src/`

## Code Style Guidelines

### Python Conventions
- **Imports**: Standard library → Third-party → Local imports (separated by blank lines)
- **Line length**: 100 characters max (configured in .pylintrc)
- **Naming**: 
  - Classes: PascalCase (e.g., `SearchService`)
  - Functions/Methods: snake_case (e.g., `search_files`)
  - Variables: snake_case (e.g., `project_path`)
  - Constants: UPPER_SNAKE_CASE (e.g., `MAX_RESULTS`)

### Architecture Patterns
- **Service Layer**: All business logic in `/services/` classes inheriting from `BaseService`
- **Error Handling**: Use `@handle_mcp_errors(return_type='str')` decorators for MCP entry points
- **Type Hints**: Required for all function signatures and returns
- **Docstrings**: Google-style docstrings for all public methods and classes
- **Validation**: Use `ValidationHelper` for all input validation and security checks

### File Organization
- **Services**: Domain-specific logic in `/services/`
- **Tools**: MCP tool implementations in `/tools/` 
- **Utils**: Shared utilities in `/utils/`
- **Indexing**: Code analysis logic in `/indexing/` with language-specific strategies

### Error Handling
- Use structured error handling with custom exceptions
- Log errors using standard logging (stderr only)
- Return user-friendly error messages from MCP tools
- Validate all inputs using ValidationHelper
- Decorate all MCP entry points with `@handle_mcp_errors`

### Testing
- Test projects located in `/test/sample-projects/`
- Each language has a complete user management system
- Use these projects for integration testing and validation

- **Proactively use CodeIndex tools** for code analysis and search efforts
