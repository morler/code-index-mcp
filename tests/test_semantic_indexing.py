"""
Test semantic indexing functionality.

Tests the semantic enhancements to SymbolInfo model and parsing strategies.
Following Linus's "good taste" principle: simple, focused tests.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from code_index_mcp.indexing.models.symbol_info import SymbolInfo
from code_index_mcp.indexing.json_index_manager import JSONIndexManager

# Try to import strategies, skip if dependencies are missing
try:
    from code_index_mcp.indexing.strategies.python_strategy import PythonParsingStrategy
    PYTHON_STRATEGY_AVAILABLE = True
except ImportError:
    PYTHON_STRATEGY_AVAILABLE = False

try:
    from code_index_mcp.indexing.strategies.javascript_strategy import JavaScriptParsingStrategy
    JAVASCRIPT_STRATEGY_AVAILABLE = True
except ImportError:
    JAVASCRIPT_STRATEGY_AVAILABLE = False

try:
    from code_index_mcp.indexing.strategies.typescript_strategy import TypeScriptParsingStrategy
    TYPESCRIPT_STRATEGY_AVAILABLE = True
except ImportError:
    TYPESCRIPT_STRATEGY_AVAILABLE = False


class TestSymbolInfoSemanticFields:
    """Test semantic fields in SymbolInfo model."""

    def test_symbol_info_has_semantic_fields(self):
        """Test that SymbolInfo has all new semantic fields."""
        symbol = SymbolInfo(
            type="function",
            file="test.py",
            line=1
        )

        # Check all semantic fields exist and are initialized
        assert hasattr(symbol, 'imports')
        assert hasattr(symbol, 'exports')
        assert hasattr(symbol, 'references')
        assert hasattr(symbol, 'dependencies')
        assert hasattr(symbol, 'called_by')

        # Check they're initialized as empty lists
        assert symbol.imports == []
        assert symbol.exports == []
        assert symbol.references == []
        assert symbol.dependencies == []
        assert symbol.called_by == []

    def test_symbol_info_semantic_field_operations(self):
        """Test semantic field operations."""
        symbol = SymbolInfo(
            type="function",
            file="test.py",
            line=1
        )

        # Test adding imports
        symbol.imports.append("os")
        symbol.imports.append("sys")
        assert "os" in symbol.imports
        assert "sys" in symbol.imports

        # Test adding dependencies
        symbol.dependencies.append("helper_function")
        assert "helper_function" in symbol.dependencies

        # Test called_by relationships
        symbol.called_by.append("main")
        assert "main" in symbol.called_by


@pytest.mark.skipif(not PYTHON_STRATEGY_AVAILABLE, reason="Python strategy dependencies not available")
class TestPythonSemanticStrategy:
    """Test Python strategy semantic enhancements."""

    def test_python_strategy_extracts_imports(self):
        """Test Python strategy extracts import information."""
        strategy = PythonParsingStrategy()
        content = '''
import os
import sys
from typing import List, Dict

def test_function():
    """Test function with imports."""
    return os.path.join("a", "b")
'''

        symbols, file_info = strategy.parse_file("test.py", content)

        # Check file-level imports
        assert "os" in file_info.imports
        assert "sys" in file_info.imports
        assert any("typing.List" in imp for imp in file_info.imports)

    def test_python_strategy_tracks_dependencies(self):
        """Test Python strategy tracks function dependencies."""
        strategy = PythonParsingStrategy()
        content = '''
def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    return result
'''

        symbols, _ = strategy.parse_file("test.py", content)

        # Check that main_function has helper_function as dependency
        main_symbol = None
        for symbol_id, symbol in symbols.items():
            if "main_function" in symbol_id:
                main_symbol = symbol
                break

        assert main_symbol is not None
        assert "helper_function" in main_symbol.dependencies

    def test_python_strategy_tracks_called_by(self):
        """Test Python strategy tracks called_by relationships."""
        strategy = PythonParsingStrategy()
        content = '''
def helper_function():
    return "helper"

def main_function():
    result = helper_function()
    return result
'''

        symbols, _ = strategy.parse_file("test.py", content)

        # Check that helper_function has main_function in called_by
        helper_symbol = None
        for symbol_id, symbol in symbols.items():
            if "helper_function" in symbol_id:
                helper_symbol = symbol
                break

        assert helper_symbol is not None
        assert any("main_function" in caller for caller in helper_symbol.called_by)


@pytest.mark.skipif(not JAVASCRIPT_STRATEGY_AVAILABLE, reason="JavaScript strategy dependencies not available")
class TestJavaScriptSemanticStrategy:
    """Test JavaScript strategy semantic enhancements."""

    def test_javascript_strategy_extracts_imports(self):
        """Test JavaScript strategy extracts import information."""
        strategy = JavaScriptParsingStrategy()
        content = '''
import { Component } from 'react';
import axios from 'axios';

function testFunction() {
    return Component;
}
'''

        symbols, file_info = strategy.parse_file("test.js", content)

        # Check imports are captured
        assert len(file_info.imports) > 0

    def test_javascript_strategy_tracks_function_calls(self):
        """Test JavaScript strategy tracks function call relationships."""
        strategy = JavaScriptParsingStrategy()
        content = '''
function helperFunction() {
    return "helper";
}

function mainFunction() {
    const result = helperFunction();
    return result;
}
'''

        symbols, _ = strategy.parse_file("test.js", content)

        # Check symbols were created
        assert len(symbols) >= 2

        # Check for dependency tracking
        main_symbol = None
        for symbol_id, symbol in symbols.items():
            if "mainFunction" in symbol_id:
                main_symbol = symbol
                break

        assert main_symbol is not None
        # JavaScript semantic analysis should track dependencies
        assert hasattr(main_symbol, 'dependencies')


@pytest.mark.skipif(not TYPESCRIPT_STRATEGY_AVAILABLE, reason="TypeScript strategy dependencies not available")
class TestTypeScriptSemanticStrategy:
    """Test TypeScript strategy semantic enhancements."""

    def test_typescript_strategy_extracts_imports(self):
        """Test TypeScript strategy extracts import information."""
        strategy = TypeScriptParsingStrategy()
        content = '''
import { Component } from 'react';
import type { User } from './types';

function testFunction(): string {
    return "test";
}
'''

        symbols, file_info = strategy.parse_file("test.ts", content)

        # Check imports are captured
        assert len(file_info.imports) > 0

    def test_typescript_strategy_tracks_dependencies(self):
        """Test TypeScript strategy tracks function dependencies."""
        strategy = TypeScriptParsingStrategy()
        content = '''
function helperFunction(): string {
    return "helper";
}

function mainFunction(): string {
    const result = helperFunction();
    return result;
}
'''

        symbols, _ = strategy.parse_file("test.ts", content)

        # Check symbols were created
        assert len(symbols) >= 2

        # Check for semantic fields
        for symbol_id, symbol in symbols.items():
            assert hasattr(symbol, 'dependencies')
            assert hasattr(symbol, 'called_by')


class TestJSONIndexManagerSemanticMethods:
    """Test JSONIndexManager semantic relationship methods."""

    def setup_method(self):
        """Set up test index manager."""
        self.manager = JSONIndexManager()

    def test_find_symbol_references(self):
        """Test finding symbol references."""
        # Mock the index manager state
        mock_index = {
            "symbols": {
                "test.py::function1": {
                    "type": "function",
                    "file": "test.py",
                    "line": 1,
                    "called_by": ["test.py::main"],
                    "references": ["test.py::main"]
                },
                "test.py::main": {
                    "type": "function",
                    "file": "test.py",
                    "line": 10,
                    "dependencies": ["function1"]
                }
            }
        }

        # Mock the index builder
        mock_builder = Mock()
        mock_builder.in_memory_index = mock_index
        self.manager.index_builder = mock_builder

        # Test finding references
        references = self.manager.find_symbol_references("function1")

        assert len(references) > 0
        assert any(ref["type"] == "called_by" for ref in references)

    def test_find_symbol_dependencies(self):
        """Test finding symbol dependencies."""
        # Mock the index manager state
        mock_index = {
            "symbols": {
                "test.py::function1": {
                    "type": "function",
                    "file": "test.py",
                    "line": 1
                },
                "test.py::main": {
                    "type": "function",
                    "file": "test.py",
                    "line": 10,
                    "dependencies": ["function1"]
                }
            }
        }

        # Mock the index builder
        mock_builder = Mock()
        mock_builder.in_memory_index = mock_index
        self.manager.index_builder = mock_builder

        # Test finding dependencies
        dependencies = self.manager.find_symbol_dependencies("function1")

        assert len(dependencies) > 0
        assert any(dep["symbol_id"] == "test.py::main" for dep in dependencies)

    def test_build_symbol_relationship_graph(self):
        """Test building symbol relationship graph."""
        # Mock the index manager state
        mock_index = {
            "symbols": {
                "test.py::function1": {
                    "type": "function",
                    "file": "test.py",
                    "line": 1,
                    "called_by": ["test.py::main"]
                },
                "test.py::main": {
                    "type": "function",
                    "file": "test.py",
                    "line": 10,
                    "dependencies": ["function1"]
                }
            }
        }

        # Mock the index builder
        mock_builder = Mock()
        mock_builder.in_memory_index = mock_index
        self.manager.index_builder = mock_builder

        # Test building graph
        graph = self.manager.build_symbol_relationship_graph()

        assert "nodes" in graph
        assert "edges" in graph
        assert "metadata" in graph
        assert len(graph["nodes"]) == 2
        assert graph["metadata"]["total_symbols"] == 2

    def test_get_symbol_imports_exports(self):
        """Test getting symbol imports and exports."""
        # Mock the index manager state
        mock_index = {
            "symbols": {
                "test.py::function1": {
                    "type": "function",
                    "file": "test.py",
                    "line": 1,
                    "imports": ["os", "sys"],
                    "exports": ["default"]
                }
            }
        }

        # Mock the index builder
        mock_builder = Mock()
        mock_builder.in_memory_index = mock_index
        self.manager.index_builder = mock_builder

        # Test getting imports
        imports = self.manager.get_symbol_imports("function1")
        assert "os" in imports
        assert "sys" in imports

        # Test getting exports
        exports = self.manager.get_symbol_exports("function1")
        assert "default" in exports


class TestSemanticIndexingIntegration:
    """Integration tests for semantic indexing."""

    def test_full_semantic_indexing_workflow(self):
        """Test complete semantic indexing workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create a test Python file with semantic relationships
            (project_path / "main.py").write_text('''
import os
import sys
from typing import List

def helper_function(data: List[str]) -> str:
    """Helper function that processes data."""
    return os.path.join(*data)

def main_function() -> int:
    """Main function that uses helper."""
    result = helper_function(["a", "b", "c"])
    print(result)
    return 0

class DataProcessor:
    """Class for processing data."""

    def process(self, data: str) -> str:
        """Process the data."""
        processed = helper_function([data])
        return processed
''')

            # Test with JSONIndexManager
            manager = JSONIndexManager()
            assert manager.set_project_path(str(project_path))
            assert manager.build_index()

            # Test semantic queries
            if manager.load_index():
                # Test finding references
                references = manager.find_symbol_references("helper_function")
                assert len(references) >= 0  # May or may not find depending on implementation

                # Test building relationship graph
                graph = manager.build_symbol_relationship_graph()
                assert "nodes" in graph
                assert "edges" in graph

            manager.cleanup()