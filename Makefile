# Makefile for Code Index MCP project
# Following Linus's principle: "Good programmers worry about data structures."

.PHONY: help install test test-unit test-integration test-coverage lint typecheck clean dev

# Default target
help:
	@echo "Code Index MCP - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  install      Install development dependencies"
	@echo "  dev          Install in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  test         Run all tests"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-coverage Run tests with coverage report"
	@echo "  test-fast    Run tests, skip slow ones"
	@echo ""
	@echo "Quality:"
	@echo "  lint         Run linting checks"
	@echo "  typecheck    Run type checking with MyPy"
	@echo "  quality      Run all quality checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean        Clean build artifacts"
	@echo "  clean-test   Clean test artifacts"

# Development setup
install:
	@echo "🔧 Installing development dependencies..."
	uv sync --dev

dev: install
	@echo "🚀 Setting up development environment..."
	uv run pip install -e .

# Testing
test:
	@echo "🧪 Running all tests..."
	uv run python -m pytest tests/ -v

test-unit:
	@echo "🔬 Running unit tests..."
	uv run python -m pytest tests/ -m unit -v

test-integration:
	@echo "🔗 Running integration tests..."
	uv run python -m pytest tests/ -m integration -v

test-coverage:
	@echo "📊 Running tests with coverage..."
	uv run python -m pytest tests/ --cov=src/code_index_mcp --cov-report=html --cov-report=term-missing -v

test-fast:
	@echo "⚡ Running fast tests..."
	uv run python -m pytest tests/ -m "not slow" -v

# Quality checks
lint:
	@echo "🔍 Running linting checks..."
	@echo "Note: Add pylint/flake8/ruff when ready"

typecheck:
	@echo "🔍 Running type checks..."
	uv run python scripts/check_types.py

quality: typecheck
	@echo "✅ All quality checks completed"

# Maintenance
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .tox/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-test:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Convenience targets
all: clean install test quality
ci: install test-coverage quality

# Special targets for different test scenarios
test-core-services:
	@echo "🧪 Testing core services..."
	uv run python -m pytest tests/test_core_services.py -v

test-functionality:
	@echo "🧪 Testing core functionality..."
	uv run python -m pytest tests/test_core_functionality.py -v

test-search:
	@echo "🔍 Testing search functionality..."
	uv run python -m pytest tests/test_search_basics.py -v