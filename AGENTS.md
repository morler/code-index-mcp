# Agent Development Guide

## Build/Test Commands

**Setup:**
```bash
uv sync --dev                    # Install dependencies
make install                     # Alternative setup
```

**Testing:**
```bash
pytest tests/                    # Run all tests
pytest tests/test_specific.py    # Run single test file
pytest tests/ -m unit            # Unit tests only
pytest tests/ -m integration     # Integration tests only
pytest tests/ -m "not slow"      # Skip slow tests
make test-coverage               # With coverage report
```

**Quality:**
```bash
uv run python scripts/check_types.py    # Type checking (MyPy)
make typecheck                          # Alternative type check
make quality                            # All quality checks
```

## Code Style Guidelines

**Architecture:** Linus-style direct data manipulation - no service abstractions, unified data structures only.

**Imports:** Group stdlib, third-party, local imports. Use TYPE_CHECKING for type hints.

**Formatting:** Max 100 chars line length, max 3 indentation levels, functions under 30 lines.

**Naming:** snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants.

**Types:** Use dataclasses for data structures, Optional[T] for nullable fields, Dict[str, Any] for generic mappings.

**Error Handling:** Direct error raising, no wrapper exceptions, validate inputs early.

**Files:** Keep under 200 lines, single responsibility, direct data access patterns.

**Testing:** Use pytest markers (@pytest.mark.unit, @pytest.mark.integration), mock external dependencies.
