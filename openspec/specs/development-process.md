# Development Process Specification

## Overview

This document defines the standardized development workflow for Code Index MCP, ensuring consistency, quality, and efficiency across all development activities. The process follows Linus-style pragmatism with emphasis on simplicity and directness.

## Development Environment Setup

### Prerequisites

**System Requirements:**
- Python 3.10+ (required)
- Git (for version control)
- uv package manager (recommended)
- 4GB+ RAM (for development)
- 2GB+ disk space

### Initial Setup

**1. Repository Clone:**
```bash
git clone https://github.com/johnhuang316/code-index-mcp
cd code-index-mcp
```

**2. Environment Setup:**
```bash
# Using uv (recommended)
uv sync --dev

# Alternative: Using pip
pip install -e ".[dev]"
```

**3. Verification:**
```bash
# Run tests to verify setup
pytest tests/ -m unit

# Check type checking
uv run python scripts/check_types.py

# Verify code quality
make quality
```

### Development Tools Configuration

**IDE Configuration:**
- Configure Python interpreter to use virtual environment
- Enable type checking (MyPy integration)
- Set up code formatting (Black, Ruff)
- Configure test discovery (pytest)

**Pre-commit Setup:**
```bash
# Install pre-commit hooks
pre-commit install

# Manual run
pre-commit run --all-files
```

## Development Workflow

### Branch Strategy

**Main Branches:**
- `main`: Stable releases, production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature development branches
- `hotfix/*`: Critical fixes for production

**Branch Naming Conventions:**
```
feature/description-of-feature
bugfix/description-of-bug
hotfix/critical-fix-description
refactor/code-improvement
docs/documentation-updates
```

### Feature Development Process

**1. Feature Planning:**
- Create issue in GitHub with detailed description
- Define acceptance criteria
- Estimate complexity and effort
- Assign to appropriate milestone

**2. Branch Creation:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/new-feature-name
```

**3. Development Cycle:**
- Implement following coding standards
- Write tests concurrently with code
- Run quality checks frequently
- Commit small, logical changes

**4. Quality Assurance:**
```bash
# Run full test suite
pytest tests/ --cov=src/code_index_mcp

# Type checking
uv run python scripts/check_types.py

# Code formatting
black src/ tests/
ruff check src/ tests/
ruff format src/ tests/

# Linting
pylint src/
```

**5. Pull Request Process:**
- Create PR from feature branch to develop
- Include comprehensive description
- Link to relevant issues
- Request code review
- Ensure CI passes

### Commit Guidelines

**Commit Message Format:**
```
type(scope): brief description

Detailed explanation of changes, including:
- What was changed and why
- Breaking changes (if any)
- Performance implications
- Testing approach

Closes #issue-number
```

**Commit Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code improvement without functional change
- `perf`: Performance optimization
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Examples:**
```
feat(search): add regex pattern support for code search

Implements regex pattern matching in search_code function.
Supports Python regex syntax with proper error handling.
Performance impact: minimal for simple patterns.

Closes #123

fix(backup): resolve file lock timeout issues

Reduced retry interval from 1s to 100ms in file_lock.py.
Fixes 30-second delays in edit operations.
All edit tests now pass baseline.

Closes #145
```

## Testing Strategy

### Test Organization

**Test Structure:**
```
tests/
├── unit/                   # Unit tests (@pytest.mark.unit)
│   ├── test_core/
│   ├── test_indexing/
│   └── test_tools/
├── integration/            # Integration tests (@pytest.mark.integration)
│   ├── test_workflows/
│   └── test_api/
├── performance/            # Performance tests (@pytest.mark.slow)
│   ├── test_memory/
│   └── test_speed/
├── contract/              # Contract tests
└── sample-projects/       # Test data
```

### Test Writing Guidelines

**Unit Tests:**
```python
import pytest
from unittest.mock import Mock, patch
from core.search import search_code

@pytest.mark.unit
def test_search_code_with_text_pattern():
    """Test basic text search functionality."""
    # Arrange
    pattern = "test_function"
    expected_files = ["file1.py", "file2.py"]
    
    # Act
    result = search_code(pattern, search_type="text")
    
    # Assert
    assert result["success"] is True
    assert len(result["files"]) > 0
    assert all(pattern in file_content for file_content in result["files"])
```

**Integration Tests:**
```python
import pytest
from tempfile import TemporaryDirectory
from core.index import IndexManager

@pytest.mark.integration
def test_full_index_workflow():
    """Test complete indexing workflow."""
    with TemporaryDirectory() as temp_dir:
        # Setup test files
        # Run indexing
        # Verify results
        pass
```

**Performance Tests:**
```python
import pytest
import time
from core.search import search_code

@pytest.mark.slow
def test_search_performance_large_codebase():
    """Test search performance with large codebase."""
    start_time = time.time()
    result = search_code("function", search_type="text")
    end_time = time.time()
    
    assert result["success"] is True
    assert end_time - start_time < 1.0  # Should complete within 1 second
```

### Test Execution

**Running Tests:**
```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/ -m unit

# Integration tests only
pytest tests/ -m integration

# Performance tests
pytest tests/ -m slow

# Specific test file
pytest tests/unit/test_search.py

# With coverage
pytest tests/ --cov=src/code_index_mcp --cov-report=html

# Verbose output
pytest tests/ -v
```

**Test Categories:**
- **Unit Tests**: Fast (<1s each), isolated components
- **Integration Tests**: Medium speed, component interaction
- **Performance Tests**: Slow, benchmarks and limits
- **Contract Tests**: API compatibility verification

## Code Review Process

### Review Guidelines

**Review Checklist:**
- [ ] Code follows project standards
- [ ] Functions under 30 lines
- [ ] Files under 200 lines
- [ ] Proper error handling
- [ ] Tests included and passing
- [ ] Documentation updated
- [ ] Performance considered
- [ ] Security implications assessed

**Review Process:**
1. **Self-Review**: Author reviews own changes first
2. **Peer Review**: At least one other developer review
3. **Automated Checks**: CI/CD pipeline validation
4. **Approval**: Merge approval after all checks pass

### Review Comments

**Constructive Feedback:**
- Be specific and actionable
- Explain reasoning for suggestions
- Provide code examples when helpful
- Focus on code, not author

**Response Guidelines:**
- Address all comments systematically
- Explain decisions when disagreeing
- Update code promptly
- Mark resolved comments

## Quality Assurance

### Automated Quality Checks

**Pre-commit Hooks:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/charliermarsh/ruff
    rev: v0.14.0
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run tests
        run: |
          pytest tests/ --cov=src/code_index_mcp
      
      - name: Type checking
        run: |
          uv run python scripts/check_types.py
      
      - name: Code quality
        run: |
          make quality
```

### Quality Metrics

**Code Quality Targets:**
- **Test Coverage**: 95%+ for core functionality
- **Type Coverage**: 90%+ type hints
- **Code Complexity**: Maximum 3 indentation levels
- **Function Length**: Maximum 30 lines
- **File Length**: Maximum 200 lines

**Performance Targets:**
- **Test Execution**: <2 minutes for full suite
- **Type Checking**: <30 seconds
- **Linting**: <15 seconds
- **Build Time**: <1 minute

## Release Process

### Version Management

**Semantic Versioning:**
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Version Examples:**
- `2.3.2` - Patch release (bug fixes)
- `2.4.0` - Minor release (new features)
- `3.0.0` - Major release (breaking changes)

### Release Checklist

**Pre-Release:**
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number incremented
- [ ] Performance benchmarks run
- [ ] Security review completed

**Release Process:**
```bash
# 1. Update version
# Edit pyproject.toml and __init__.py

# 2. Update changelog
# Edit CHANGELOG.md

# 3. Create release tag
git tag -a v2.3.2 -m "Release version 2.3.2"
git push origin v2.3.2

# 4. Build and publish
python -m build
twine upload dist/*

# 5. Create GitHub release
gh release create v2.3.2 --generate-notes
```

**Post-Release:**
- [ ] Monitor for issues
- [ ] Update documentation website
- [ ] Announce release
- [ ] Plan next version

## Documentation Standards

### Code Documentation

**Requirements:**
- Module-level docstrings
- Function documentation with parameters
- Type hints for all public APIs
- Usage examples for complex operations

**Documentation Format:**
```python
def search_code(pattern: str, search_type: str = "text") -> Dict[str, Any]:
    """
    Search for code patterns across the project.
    
    This function provides unified search capabilities supporting multiple
    search types including text matching, regex patterns, and symbol search.
    
    Args:
        pattern: Search pattern (regex or text)
        search_type: Type of search ("text", "regex", "symbol")
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - files: List of matching file paths
        - matches: List of match details with line numbers
        - error: Error message if success is False
        
    Raises:
        ValueError: If search_type is invalid
        FileNotFoundError: If project path doesn't exist
        
    Example:
        >>> result = search_code("def test_", "text")
        >>> print(result["files"])
        ['test_module.py', 'another_test.py']
    """
```

### API Documentation

**Documentation Requirements:**
- Complete API reference
- Usage examples for each tool
- Error handling documentation
- Performance characteristics
- Integration guides

## Troubleshooting Guide

### Common Issues

**Environment Setup:**
```bash
# Python version issues
python --version  # Should be 3.10+

# Dependency conflicts
uv sync --dev  # Fresh install

# Permission issues
pip install --user -e ".[dev]"
```

**Test Failures:**
```bash
# Isolate failing test
pytest tests/unit/test_specific.py -v

# Run with debugging
pytest tests/ -s --pdb

# Check coverage gaps
pytest tests/ --cov=src/code_index_mcp --cov-report=term-missing
```

**Performance Issues:**
```bash
# Profile test execution
pytest tests/ --profile

# Memory usage
python -m memory_profiler script.py

# Identify bottlenecks
python -m cProfile script.py
```

### Debugging Tools

**Logging Configuration:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Development Mode:**
```python
# Enable debug features
export DEBUG=1
export CODE_INDEX_DEV=1
```

This development process specification ensures consistent, high-quality development practices across the Code Index MCP project while maintaining the Linus-style emphasis on simplicity and directness.