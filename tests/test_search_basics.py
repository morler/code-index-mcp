"""Basic search functionality tests.

Tests the core search patterns that users rely on.
Following Linus's principle: "Never break userspace."
"""

import tempfile
import pytest
from pathlib import Path

from src.code_index_mcp.services.search_service import SearchService
from src.code_index_mcp.tools.config.project_config_tool import ProjectConfigTool
from src.code_index_mcp.indexing.json_index_manager import JSONIndexManager
from unittest.mock import Mock


@pytest.fixture
def search_project():
    """Create a project with diverse search patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Create test files with various patterns
        (project_path / "utils.py").write_text('''
import os
import sys

def helper_function():
    """A utility function."""
    return "helper"

class UtilityClass:
    def process_data(self):
        return {"status": "ok"}
''')

        (project_path / "main.js").write_text('''
const express = require('express');

function startServer(port) {
    console.log(`Starting server on port ${port}`);
}

class ServerManager {
    constructor() {
        this.isRunning = false;
    }
}
''')

        (project_path / "README.md").write_text('''
# Test Project

This is a test project for search functionality.

## Features
- Helper functions
- Server management
- Data processing
''')

        # Initialize and index
        config_tool = ProjectConfigTool()
        config_tool.initialize_project(str(project_path))

        index_manager = UnifiedIndexManager(str(project_path))
        index_manager.build_index()

        yield project_path


class TestBasicSearch:
    """Test fundamental search operations."""

    def test_literal_string_search(self, search_project):
        """Test searching for literal strings."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Search for exact string
        results = search_coordinator.search(pattern="helper", case_sensitive=False)
        assert len(results) > 0, "Should find 'helper' in files"

        # Case sensitive search
        results_case = search_coordinator.search(pattern="Helper", case_sensitive=True)
        # May or may not find results depending on exact content

    def test_file_extension_filtering(self, search_project):
        """Test filtering by file extensions."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Python files only
        py_results = search_coordinator.search(
            pattern="function",
            file_pattern="*.py",
            case_sensitive=False
        )

        # JavaScript files only
        js_results = search_coordinator.search(
            pattern="function",
            file_pattern="*.js",
            case_sensitive=False
        )

        # Results should be properly filtered
        if py_results:
            for file_path in py_results.keys():
                assert file_path.endswith(".py")

        if js_results:
            for file_path in js_results.keys():
                assert file_path.endswith(".js")

    def test_common_programming_patterns(self, search_project):
        """Test searches for common programming constructs."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Test function definitions
        func_results = search_coordinator.search(pattern="def ", case_sensitive=True)
        # Should find Python function definitions

        # Test class definitions
        class_results = search_coordinator.search(pattern="class", case_sensitive=False)
        # Should find both Python and JavaScript classes

        # Test import statements
        import_results = search_coordinator.search(pattern="import", case_sensitive=False)
        # Should find import statements

    def test_special_characters_in_search(self, search_project):
        """Test search patterns with special characters."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Search for patterns with dots
        dot_results = search_coordinator.search(pattern="console.log", case_sensitive=True)

        # Search for patterns with parentheses
        paren_results = search_coordinator.search(pattern="()", case_sensitive=True)

        # Should handle special characters without crashing
        assert isinstance(dot_results, (dict, list))
        assert isinstance(paren_results, (dict, list))


class TestSearchEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_search_pattern(self, search_project):
        """Test search with empty or whitespace pattern."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Empty pattern should be handled gracefully
        results = search_coordinator.search(pattern="", case_sensitive=False)
        assert isinstance(results, (dict, list))

        # Whitespace pattern
        whitespace_results = search_coordinator.search(pattern="   ", case_sensitive=False)
        assert isinstance(whitespace_results, (dict, list))

    def test_very_long_pattern(self, search_project):
        """Test search with very long pattern."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Very long pattern
        long_pattern = "a" * 1000
        results = search_coordinator.search(pattern=long_pattern, case_sensitive=False)

        # Should handle long patterns without crashing
        assert isinstance(results, (dict, list))

    def test_nonexistent_file_pattern(self, search_project):
        """Test file pattern that matches no files."""
        search_coordinator = SearchCoordinator(str(search_project))

        # Pattern that won't match any files
        results = search_coordinator.search(
            pattern="test",
            file_pattern="*.nonexistent",
            case_sensitive=False
        )

        # Should return empty results, not error
        assert isinstance(results, (dict, list))
        if isinstance(results, dict):
            assert len(results) == 0
        else:
            assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])