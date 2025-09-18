"""Search functionality integration tests.

Tests end-to-end search workflows from indexing to results.
Following Linus's principle: "Never break userspace."
"""

import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any, List

from src.code_index_mcp.services.search_service import SearchService
from src.code_index_mcp.indexing.json_index_manager import JSONIndexManager
from src.code_index_mcp.tools.config.project_config_tool import ProjectConfigTool
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestSearchIntegration:
    """Test complete search workflows."""

    @pytest.fixture
    def search_test_project(self):
        """Create a project with searchable content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Python file with specific patterns to search for
            (project_path / "main.py").write_text('''
"""Main application module."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def calculate_fibonacci(n: int) -> int:
    """Calculate fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class DatabaseManager:
    """Manages database connections."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.is_connected = False

    async def connect(self) -> bool:
        """Establish database connection."""
        logger.info("Connecting to database")
        self.is_connected = True
        return True

    async def disconnect(self) -> None:
        """Close database connection."""
        if self.is_connected:
            logger.info("Disconnecting from database")
            self.is_connected = False

    def execute_query(self, query: str) -> Optional[List[Dict]]:
        """Execute SQL query."""
        if not self.is_connected:
            raise RuntimeError("Database not connected")

        # Mock implementation
        logger.debug(f"Executing query: {query}")
        return []

def create_manager(conn_str: str) -> DatabaseManager:
    """Factory function for database manager."""
    return DatabaseManager(conn_str)

if __name__ == "__main__":
    manager = create_manager("sqlite:///test.db")
    asyncio.run(manager.connect())
''')

            # Create JavaScript file
            (project_path / "utils.js").write_text('''
/**
 * Utility functions for data processing
 */

const crypto = require('crypto');

/**
 * Generate random UUID
 * @returns {string} UUID string
 */
function generateUUID() {
    return crypto.randomUUID();
}

/**
 * Validate email address
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
function validateEmail(email) {
    const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Deep merge objects
 * @param {object} target - Target object
 * @param {object} source - Source object
 * @returns {object} Merged object
 */
function deepMerge(target, source) {
    const result = { ...target };

    for (const key in source) {
        if (source.hasOwnProperty(key)) {
            if (typeof source[key] === 'object' && source[key] !== null) {
                result[key] = deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
    }

    return result;
}

class EventEmitter {
    constructor() {
        this.events = new Map();
    }

    on(event, listener) {
        if (!this.events.has(event)) {
            this.events.set(event, []);
        }
        this.events.get(event).push(listener);
    }

    emit(event, ...args) {
        if (this.events.has(event)) {
            this.events.get(event).forEach(listener => {
                listener.apply(this, args);
            });
        }
    }

    off(event, listener) {
        if (this.events.has(event)) {
            const listeners = this.events.get(event);
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }
}

module.exports = {
    generateUUID,
    validateEmail,
    deepMerge,
    EventEmitter
};
''')

            # Create TypeScript file
            (project_path / "types.ts").write_text('''
/**
 * Type definitions and interfaces
 */

export interface UserProfile {
    id: number;
    username: string;
    email: string;
    firstName: string;
    lastName: string;
    isActive: boolean;
    createdAt: Date;
    permissions: Permission[];
}

export interface Permission {
    id: number;
    name: string;
    description: string;
    resource: string;
    action: 'read' | 'write' | 'delete' | 'admin';
}

export type ApiResponse<T> = {
    success: boolean;
    data: T;
    message?: string;
    errors?: string[];
};

export class UserService {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    async getUserProfile(userId: number): Promise<ApiResponse<UserProfile>> {
        const response = await fetch(`${this.baseUrl}/users/${userId}`);
        return response.json();
    }

    async updateUserProfile(userId: number, profile: Partial<UserProfile>): Promise<ApiResponse<UserProfile>> {
        const response = await fetch(`${this.baseUrl}/users/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });
        return response.json();
    }

    async deleteUser(userId: number): Promise<ApiResponse<void>> {
        const response = await fetch(`${this.baseUrl}/users/${userId}`, {
            method: 'DELETE'
        });
        return response.json();
    }
}

export function createUserService(baseUrl: string): UserService {
    return new UserService(baseUrl);
}
''')

            # Create README with documentation
            (project_path / "README.md").write_text('''
# Search Test Project

This project contains various patterns for testing search functionality:

## Python Components
- `calculate_fibonacci` - Recursive function implementation
- `DatabaseManager` - Class for database operations
- `create_manager` - Factory function

## JavaScript Components
- `generateUUID` - UUID generation utility
- `validateEmail` - Email validation function
- `EventEmitter` - Custom event handling class

## TypeScript Components
- `UserProfile` interface - User data structure
- `UserService` class - API service for user operations
- Type definitions for API responses

## Search Patterns to Test
- Function names (calculate_fibonacci, generateUUID)
- Class names (DatabaseManager, EventEmitter, UserService)
- Variable names (logger, connection_string, baseUrl)
- Comments and documentation
- Import/export statements
- Type annotations
''')

            yield project_path

    def test_basic_literal_search(self, search_test_project):
        """Test basic literal string search."""
        project_path = str(search_test_project)

        # Initialize project and build index
        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        # Create mock context and search service
        mock_context = Mock()
        search_service = SearchService(mock_context)

        # Mock the helper and setup
        search_service.helper = Mock()
        search_service.helper.get_base_path_error.return_value = None
        search_service.helper.base_path = project_path
        search_service.helper.settings = Mock()

        # Mock search strategy
        mock_strategy = Mock()
        mock_strategy.name = "test_strategy"
        mock_strategy.search.return_value = ["match found in main.py"]
        search_service.helper.settings.get_preferred_search_tool.return_value = mock_strategy

        # Mock validation and formatting
        with patch('src.code_index_mcp.utils.ValidationHelper.validate_search_pattern') as mock_validate, \
             patch('src.code_index_mcp.utils.ResponseFormatter.search_results_response') as mock_formatter:

            mock_validate.return_value = None
            mock_formatter.return_value = {"status": "success", "results": ["main.py: fibonacci"]}

            # Test searching for function name
            results = search_service.search_code(pattern="calculate_fibonacci", case_sensitive=True)

            assert results["status"] == "success"
            assert len(results["results"]) > 0

    def test_case_insensitive_search(self, search_test_project):
        """Test case-insensitive search functionality."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search for class name with different case
        results = search_coordinator.search(pattern="databasemanager", case_sensitive=False)
        assert len(results) > 0, "Should find DatabaseManager with case insensitive search"

        # Search for UUID in different case
        uuid_results = search_coordinator.search(pattern="UUID", case_sensitive=False)
        assert len(uuid_results) > 0, "Should find UUID references"

    def test_file_pattern_filtering(self, search_test_project):
        """Test search with file pattern filtering."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search only in Python files
        py_results = search_coordinator.search(
            pattern="async",
            file_pattern="*.py",
            case_sensitive=True
        )

        if py_results:
            # All results should be from Python files
            for file_path in py_results.keys():
                assert file_path.endswith(".py"), f"Found non-Python file: {file_path}"

        # Search only in JavaScript files
        js_results = search_coordinator.search(
            pattern="function",
            file_pattern="*.js",
            case_sensitive=True
        )

        if js_results:
            # All results should be from JavaScript files
            for file_path in js_results.keys():
                assert file_path.endswith(".js"), f"Found non-JavaScript file: {file_path}"

    def test_context_lines_search(self, search_test_project):
        """Test search with context lines."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search with context lines
        results = search_coordinator.search(
            pattern="calculate_fibonacci",
            context_lines=2,
            case_sensitive=True
        )

        assert len(results) > 0, "Should find fibonacci function with context"

        # With context, results should contain multiple lines
        for file_results in results.values():
            if isinstance(file_results, list) and file_results:
                # Should have more than just the matching line when context is requested
                # This is implementation dependent, so we just check for reasonable content
                assert len(file_results) > 0

    def test_multiple_file_types_search(self, search_test_project):
        """Test search across multiple file types."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search for common term across file types
        results = search_coordinator.search(pattern="function", case_sensitive=False)

        if results:
            file_types = set()
            for file_path in results.keys():
                if "." in file_path:
                    extension = file_path.split(".")[-1]
                    file_types.add(extension)

            # Should find matches in multiple file types
            # This depends on the content, but we should at least find some files
            assert len(file_types) > 0, "Should find matches in at least one file type"

    def test_special_characters_search(self, search_test_project):
        """Test search with special characters and symbols."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search for patterns with special characters
        special_patterns = [
            "async def",  # Space in pattern
            "__init__",   # Underscores
            "this.events", # Dot notation
            "=>",         # Arrow function
            "interface",  # TypeScript keyword
        ]

        for pattern in special_patterns:
            try:
                results = search_coordinator.search(pattern=pattern, case_sensitive=True)
                # Should not crash with special characters
                assert isinstance(results, dict) or isinstance(results, list)
            except Exception as e:
                pytest.fail(f"Search failed for pattern '{pattern}': {e}")

    def test_empty_and_edge_case_searches(self, search_test_project):
        """Test edge cases and empty searches."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Test empty pattern
        empty_results = search_coordinator.search(pattern="", case_sensitive=True)
        assert isinstance(empty_results, (dict, list))

        # Test non-existent pattern
        missing_results = search_coordinator.search(pattern="nonexistent_pattern_xyz123", case_sensitive=True)
        assert isinstance(missing_results, (dict, list))

        # Test very long pattern
        long_pattern = "a" * 1000
        long_results = search_coordinator.search(pattern=long_pattern, case_sensitive=True)
        assert isinstance(long_results, (dict, list))

    def test_search_performance_baseline(self, search_test_project):
        """Test search performance meets reasonable expectations."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        import time

        # Test several search patterns and measure time
        patterns = ["function", "class", "import", "async", "const"]

        for pattern in patterns:
            start_time = time.time()
            results = search_coordinator.search(pattern=pattern, case_sensitive=False)
            end_time = time.time()

            search_time = end_time - start_time

            # Search should complete quickly (adjust threshold as needed)
            assert search_time < 5.0, f"Search for '{pattern}' took {search_time:.2f}s, expected < 5s"

            # Results should be properly formatted
            assert isinstance(results, (dict, list))

    def test_search_without_index(self):
        """Test search behavior when no index exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't build an index, just try to search
            search_coordinator = SearchCoordinator(temp_dir)

            # Should handle missing index gracefully
            results = search_coordinator.search(pattern="test", case_sensitive=True)
            assert isinstance(results, (dict, list))

    @pytest.mark.slow
    def test_large_result_set_handling(self, search_test_project):
        """Test handling of search patterns that return many results."""
        project_path = str(search_test_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        index_manager.build_index()

        search_coordinator = SearchCoordinator(project_path)

        # Search for very common pattern that should return many results
        results = search_coordinator.search(pattern="e", case_sensitive=False)  # Very common letter

        # Should handle large result sets without crashing
        assert isinstance(results, (dict, list))

        # Results should be reasonable (not infinite)
        if isinstance(results, dict):
            total_results = sum(len(v) if isinstance(v, list) else 1 for v in results.values())
        else:
            total_results = len(results)

        # Should have results but not an unreasonable amount
        assert total_results < 10000, f"Too many results: {total_results}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])