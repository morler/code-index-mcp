"""Pytest configuration and shared fixtures.

Following Linus's principle: "Simplicity is the ultimate sophistication."
Provides minimal, focused test fixtures and configuration.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def sample_project_structure():
    """Create a reusable sample project for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Create Python files
        (project_path / "main.py").write_text('''
#!/usr/bin/env python3
"""Main module for the application."""

import sys
from typing import List, Optional

def main() -> int:
    """Entry point of the application."""
    print("Hello, World!")
    return 0

class ApplicationManager:
    """Manages application lifecycle."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.is_running = False

    def start(self) -> bool:
        """Start the application."""
        self.is_running = True
        return True

    def stop(self) -> None:
        """Stop the application."""
        self.is_running = False

if __name__ == "__main__":
    sys.exit(main())
''')

        (project_path / "utils.py").write_text('''
"""Utility functions."""

from typing import Any, Dict, List

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get a value from dictionary."""
    return data.get(key, default)

def filter_none(items: List[Any]) -> List[Any]:
    """Filter out None values from list."""
    return [item for item in items if item is not None]

class Logger:
    """Simple logging utility."""

    def __init__(self, name: str):
        self.name = name

    def info(self, message: str) -> None:
        """Log info message."""
        print(f"[INFO] {self.name}: {message}")

    def error(self, message: str) -> None:
        """Log error message."""
        print(f"[ERROR] {self.name}: {message}")
''')

        # Create JavaScript files
        (project_path / "app.js").write_text('''
/**
 * Main application module
 */

const express = require('express');
const path = require('path');

function createApp() {
    const app = express();

    app.get('/', (req, res) => {
        res.send('Hello World!');
    });

    return app;
}

class Server {
    constructor(port = 3000) {
        this.port = port;
        this.app = createApp();
        this.server = null;
    }

    start() {
        this.server = this.app.listen(this.port, () => {
            console.log(`Server running on port ${this.port}`);
        });
    }

    stop() {
        if (this.server) {
            this.server.close();
        }
    }
}

module.exports = { createApp, Server };
''')

        # Create TypeScript files
        (project_path / "types.ts").write_text('''
/**
 * Type definitions for the application
 */

export interface User {
    id: number;
    name: string;
    email: string;
    active: boolean;
}

export interface ApiResponse<T> {
    data: T;
    success: boolean;
    message?: string;
}

export class UserManager {
    private users: User[] = [];

    constructor() {
        this.users = [];
    }

    addUser(user: User): void {
        this.users.push(user);
    }

    getUser(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }

    getAllUsers(): User[] {
        return [...this.users];
    }
}

export function createApiResponse<T>(data: T, success: boolean = true): ApiResponse<T> {
    return { data, success };
}
''')

        # Create config files
        (project_path / "package.json").write_text('''
{
  "name": "test-project",
  "version": "1.0.0",
  "description": "Test project for code indexing",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.0"
  }
}
''')

        (project_path / "README.md").write_text('''
# Test Project

This is a sample project for testing the code indexing functionality.

## Features

- Python modules with classes and functions
- JavaScript/Node.js server application
- TypeScript type definitions
- Configuration files

## Structure

- `main.py` - Main application entry point
- `utils.py` - Utility functions and classes
- `app.js` - Express.js server
- `types.ts` - TypeScript type definitions
''')

        yield project_path


@pytest.fixture
def mock_mcp_context():
    """Create a mock MCP context for testing."""
    context = Mock()
    context.request = Mock()
    context.lifespan = Mock()
    return context


@pytest.fixture
def mock_context_helper():
    """Create a mock ContextHelper for testing."""
    helper = Mock()
    helper.base_path = "/test/project"
    helper.file_count = 10
    helper.settings = Mock()
    helper.index_manager = Mock()
    helper.get_base_path_error.return_value = None
    helper.get_search_tools_status.return_value = "ugrep available"
    return helper


@pytest.fixture
def empty_project():
    """Create an empty temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def minimal_python_project():
    """Create a minimal Python project for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Single Python file
        (project_path / "simple.py").write_text('''
def hello():
    return "Hello"

class Simple:
    def method(self):
        return 42
''')

        yield project_path


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location/name."""
    for item in items:
        # Mark tests in test_core_functionality as integration
        if "test_core_functionality" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Mark tests in test_core_services as unit
        if "test_core_services" in item.nodeid:
            item.add_marker(pytest.mark.unit)

        # Mark any test containing "integration" or "end_to_end" as integration
        if "integration" in item.name or "end_to_end" in item.name:
            item.add_marker(pytest.mark.integration)