"""Index building integration tests.

Tests the complete indexing workflow from file discovery to symbol extraction.
Following Linus's principle: "Never break userspace."
"""

import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any

from src.code_index_mcp.indexing.json_index_manager import JSONIndexManager
from src.code_index_mcp.indexing.unified_index_manager import UnifiedIndexManager
from src.code_index_mcp.tools.config.project_config_tool import ProjectConfigTool


@pytest.mark.integration
class TestIndexBuildingIntegration:
    """Test complete index building workflows."""

    @pytest.fixture
    def complex_project(self):
        """Create a complex project for thorough testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create Python files with various patterns
            (project_path / "core" / "main.py").parent.mkdir(exist_ok=True)
            (project_path / "core" / "main.py").write_text('''
#!/usr/bin/env python3
"""Main application module."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Application configuration."""
    host: str = "localhost"
    port: int = 8080
    debug: bool = False

class ServiceBase(ABC):
    """Abstract base for all services."""

    @abstractmethod
    def start(self) -> bool:
        """Start the service."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        pass

class ApplicationManager(ServiceBase):
    """Main application manager."""

    def __init__(self, config: Config):
        self.config = config
        self.services: List[ServiceBase] = []
        self._running = False

    def start(self) -> bool:
        """Start all services."""
        if self._running:
            return False

        logger.info(f"Starting application on {self.config.host}:{self.config.port}")
        self._running = True
        return True

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        if not self._running:
            return

        for service in reversed(self.services):
            await service.shutdown()

        self._running = False
        logger.info("Application shutdown complete")

def create_app(config: Optional[Config] = None) -> ApplicationManager:
    """Factory function for application."""
    if config is None:
        config = Config()
    return ApplicationManager(config)

async def main() -> int:
    """Application entry point."""
    app = create_app()

    try:
        if not app.start():
            return 1

        # Keep running until interrupted
        await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await app.shutdown()

    return 0

if __name__ == "__main__":
    asyncio.run(main())
''')

            # Create TypeScript files
            (project_path / "frontend" / "api.ts").parent.mkdir(exist_ok=True)
            (project_path / "frontend" / "api.ts").write_text('''
/**
 * API client for backend communication
 */

export interface ApiResponse<T> {
    data: T;
    success: boolean;
    message?: string;
    timestamp: number;
}

export interface User {
    id: number;
    username: string;
    email: string;
    active: boolean;
    roles: string[];
}

export interface CreateUserRequest {
    username: string;
    email: string;
    password: string;
}

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public response?: any
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

export class ApiClient {
    private baseUrl: string;
    private token: string | null = null;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\\/$/, '');
    }

    setAuthToken(token: string): void {
        this.token = token;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<ApiResponse<T>> {
        const url = `${this.baseUrl}${endpoint}`;

        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (!response.ok) {
            throw new ApiError(
                `HTTP ${response.status}: ${response.statusText}`,
                response.status,
                await response.text()
            );
        }

        return response.json();
    }

    async getUsers(): Promise<ApiResponse<User[]>> {
        return this.request<User[]>('/users');
    }

    async createUser(userData: CreateUserRequest): Promise<ApiResponse<User>> {
        return this.request<User>('/users', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    }

    async getUserById(id: number): Promise<ApiResponse<User>> {
        return this.request<User>(`/users/${id}`);
    }

    async updateUser(id: number, userData: Partial<User>): Promise<ApiResponse<User>> {
        return this.request<User>(`/users/${id}`, {
            method: 'PUT',
            body: JSON.stringify(userData),
        });
    }

    async deleteUser(id: number): Promise<ApiResponse<void>> {
        return this.request<void>(`/users/${id}`, {
            method: 'DELETE',
        });
    }
}

export function createApiClient(baseUrl: string): ApiClient {
    return new ApiClient(baseUrl);
}
''')

            # Create JavaScript files
            (project_path / "utils" / "helpers.js").parent.mkdir(exist_ok=True)
            (project_path / "utils" / "helpers.js").write_text('''
/**
 * Utility functions for common operations
 */

const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');

/**
 * Generate a random string of specified length
 * @param {number} length - Length of the string
 * @returns {string} Random string
 */
function generateRandomString(length = 32) {
    return crypto.randomBytes(length).toString('hex');
}

/**
 * Deep clone an object
 * @param {any} obj - Object to clone
 * @returns {any} Cloned object
 */
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }

    if (obj instanceof Date) {
        return new Date(obj.getTime());
    }

    if (obj instanceof Array) {
        return obj.map(item => deepClone(item));
    }

    const cloned = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            cloned[key] = deepClone(obj[key]);
        }
    }

    return cloned;
}

/**
 * Debounce function execution
 * @param {Function} func - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, delay) {
    let timeoutId;

    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * File utilities class
 */
class FileUtils {
    /**
     * Check if file exists
     * @param {string} filePath - Path to file
     * @returns {Promise<boolean>} True if file exists
     */
    static async exists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Read JSON file
     * @param {string} filePath - Path to JSON file
     * @returns {Promise<any>} Parsed JSON data
     */
    static async readJson(filePath) {
        const content = await fs.readFile(filePath, 'utf8');
        return JSON.parse(content);
    }

    /**
     * Write JSON file
     * @param {string} filePath - Path to JSON file
     * @param {any} data - Data to write
     * @returns {Promise<void>}
     */
    static async writeJson(filePath, data) {
        const content = JSON.stringify(data, null, 2);
        await fs.writeFile(filePath, content, 'utf8');
    }

    /**
     * Create directory if it doesn't exist
     * @param {string} dirPath - Directory path
     * @returns {Promise<void>}
     */
    static async ensureDir(dirPath) {
        try {
            await fs.mkdir(dirPath, { recursive: true });
        } catch (error) {
            if (error.code !== 'EEXIST') {
                throw error;
            }
        }
    }
}

module.exports = {
    generateRandomString,
    deepClone,
    debounce,
    FileUtils,
};
''')

            # Create configuration files
            (project_path / "package.json").write_text('''
{
  "name": "complex-test-project",
  "version": "1.0.0",
  "description": "Complex test project for comprehensive indexing",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js",
    "test": "jest",
    "build": "webpack --mode production",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit"
  },
  "keywords": ["test", "indexing", "mcp"],
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "nodemon": "^3.0.0",
    "eslint": "^8.0.0",
    "typescript": "^5.0.0",
    "webpack": "^5.0.0"
  }
}
''')

            yield project_path

    def test_empty_project_indexing(self):
        """Test indexing an empty project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_tool = ProjectConfigTool()
            config_tool.initialize_settings(temp_dir)

            index_manager = JSONIndexManager()
            index_manager.set_project_path(temp_dir)
            result = index_manager.build_index()

            assert result["status"] == "success", "Index build should succeed even for empty project"

            # Check that index was created (even if empty)
            index_data = config_tool.load_existing_index()
            if index_data:  # May be None for empty projects
                assert isinstance(index_data, dict)

    def test_simple_project_indexing(self, minimal_python_project):
        """Test indexing a simple project with basic files."""
        project_path = str(minimal_python_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        result = index_manager.build_index()

        assert result["status"] == "success"
        assert result["files_processed"] >= 1
        assert result["symbols_found"] >= 2  # function + class

        # Verify index data persistence
        index_data = config_tool.load_existing_index()
        assert index_data is not None
        assert "symbols" in index_data
        assert len(index_data["symbols"]) >= 2

    def test_complex_project_indexing(self, complex_project):
        """Test indexing a complex multi-language project."""
        project_path = str(complex_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        result = index_manager.build_index()

        assert result["status"] == "success"
        assert result["files_processed"] >= 4  # Python, TypeScript, JavaScript, JSON
        assert result["symbols_found"] >= 20   # Multiple classes, functions, interfaces

        # Verify symbol diversity
        index_data = config_tool.load_existing_index()
        symbols = index_data.get("symbols", [])

        # Check for Python symbols
        python_symbols = [s for s in symbols if s.get("file_path", "").endswith(".py")]
        assert len(python_symbols) >= 10

        # Check for TypeScript symbols
        ts_symbols = [s for s in symbols if s.get("file_path", "").endswith(".ts")]
        assert len(ts_symbols) >= 8

        # Check for JavaScript symbols
        js_symbols = [s for s in symbols if s.get("file_path", "").endswith(".js")]
        assert len(js_symbols) >= 5

        # Verify symbol types
        symbol_types = {s.get("type") for s in symbols}
        expected_types = {"function", "class", "interface", "method"}
        assert expected_types.issubset(symbol_types)

    def test_incremental_indexing(self, complex_project):
        """Test that incremental indexing works correctly."""
        project_path = str(complex_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)

        # First build
        result1 = index_manager.build_index()
        assert result1["status"] == "success"

        # Add a new file
        new_file = complex_project / "new_module.py"
        new_file.write_text('''
def new_function():
    """A new function."""
    return "new"

class NewClass:
    """A new class."""
    pass
''')

        # Second build should detect the new file
        result2 = index_manager.build_index()
        assert result2["status"] == "success"
        assert result2["files_processed"] >= result1["files_processed"]
        assert result2["symbols_found"] >= result1["symbols_found"] + 2

    def test_index_performance_baseline(self, complex_project):
        """Test indexing performance meets baseline requirements."""
        project_path = str(complex_project)

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)

        import time
        start_time = time.time()
        result = index_manager.build_index()
        end_time = time.time()

        build_time = end_time - start_time

        assert result["status"] == "success"
        # Should complete within reasonable time (adjust based on requirements)
        assert build_time < 10.0, f"Index build took {build_time:.2f}s, expected < 10s"

        # Verify build time is recorded
        assert "build_time" in result
        assert isinstance(result["build_time"], (int, float))

    def test_error_handling_invalid_files(self, complex_project):
        """Test error handling with invalid/corrupted files."""
        project_path = str(complex_project)

        # Create a file with syntax errors
        invalid_file = complex_project / "invalid.py"
        invalid_file.write_text('''
def broken_function(
    # Missing closing parenthesis and colon
    return "this will not parse"

class BrokenClass
    # Missing colon
    def method(self)
        # Missing colon
        pass
''')

        config_tool = ProjectConfigTool()
        config_tool.initialize_settings(project_path)

        index_manager = JSONIndexManager()
        index_manager.set_project_path(project_path)
        result = index_manager.build_index()

        # Should still succeed overall, but may skip invalid file
        assert result["status"] == "success"
        assert result["files_processed"] >= 4  # Should process valid files

    @pytest.mark.slow
    def test_large_project_scalability(self):
        """Test indexing performance with larger number of files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create many small Python files
            for i in range(50):
                module_dir = project_path / f"module_{i // 10}"
                module_dir.mkdir(exist_ok=True)

                file_path = module_dir / f"file_{i}.py"
                file_path.write_text(f'''
"""Module {i} - Auto-generated for testing."""

def function_{i}():
    """Function {i}."""
    return {i}

class Class_{i}:
    """Class {i}."""

    def method_{i}(self):
        """Method {i}."""
        return {i} * 2

# Variables and constants
VALUE_{i} = {i}
STRING_{i} = "value_{i}"
''')

            config_tool = ProjectConfigTool()
            config_tool.initialize_project(str(project_path))

            index_manager = UnifiedIndexManager(str(project_path))

            import time
            start_time = time.time()
            result = index_manager.build_index()
            end_time = time.time()

            build_time = end_time - start_time

            assert result["status"] == "success"
            assert result["files_processed"] == 50
            assert result["symbols_found"] >= 100  # At least 2 symbols per file
            # Should scale reasonably (adjust threshold as needed)
            assert build_time < 30.0, f"Large project indexing took {build_time:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])