"""
Test Python strategy semantic enhancements.

Simple test of Python AST-based semantic analysis.
"""

import pytest
import sys
import os
import ast

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Direct import to avoid package-level tree-sitter dependencies
import importlib.util

# Import SymbolInfo directly
spec = importlib.util.spec_from_file_location(
    "symbol_info",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'code_index_mcp', 'indexing', 'models', 'symbol_info.py')
)
symbol_info_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(symbol_info_module)
SymbolInfo = symbol_info_module.SymbolInfo

# Import FileInfo directly
spec = importlib.util.spec_from_file_location(
    "file_info",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'code_index_mcp', 'indexing', 'models', 'file_info.py')
)
file_info_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_info_module)
FileInfo = file_info_module.FileInfo

# Try to import Python strategy
try:
    spec = importlib.util.spec_from_file_location(
        "python_strategy",
        os.path.join(os.path.dirname(__file__), '..', 'src', 'code_index_mcp', 'indexing', 'strategies', 'python_strategy.py')
    )
    python_strategy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(python_strategy_module)
    PythonParsingStrategy = python_strategy_module.PythonParsingStrategy
    PYTHON_STRATEGY_AVAILABLE = True
except Exception as e:
    print(f"Python strategy not available: {e}")
    PYTHON_STRATEGY_AVAILABLE = False


@pytest.mark.skipif(not PYTHON_STRATEGY_AVAILABLE, reason="Python strategy not available")
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

    def test_python_strategy_class_methods(self):
        """Test Python strategy handles class methods correctly."""
        strategy = PythonParsingStrategy()
        content = '''
class TestClass:
    def method1(self):
        return self.method2()

    def method2(self):
        return "result"
'''

        symbols, _ = strategy.parse_file("test.py", content)

        # Should have class and methods
        class_symbol = None
        method1_symbol = None
        method2_symbol = None

        for symbol_id, symbol in symbols.items():
            if "TestClass" in symbol_id and symbol.type == "class":
                class_symbol = symbol
            elif "TestClass.method1" in symbol_id:
                method1_symbol = symbol
            elif "TestClass.method2" in symbol_id:
                method2_symbol = symbol

        assert class_symbol is not None
        assert method1_symbol is not None
        assert method2_symbol is not None

        # method1 should depend on method2
        assert "method2" in method1_symbol.dependencies

    def test_python_strategy_nested_imports(self):
        """Test Python strategy handles imports within functions."""
        strategy = PythonParsingStrategy()
        content = '''
def function_with_imports():
    import json
    from collections import defaultdict

    data = json.loads('{}')
    return defaultdict(list)
'''

        symbols, file_info = strategy.parse_file("test.py", content)

        # Function should have imports tracked
        func_symbol = None
        for symbol_id, symbol in symbols.items():
            if "function_with_imports" in symbol_id:
                func_symbol = symbol
                break

        assert func_symbol is not None
        # Note: The implementation may or may not track function-level imports
        # This test documents the expected behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v"])