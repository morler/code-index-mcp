"""
Test semantic fields in SymbolInfo model.

Simple focused test of the semantic enhancements following Linus's "good taste" principle.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Direct import to avoid package-level imports
import importlib.util
import sys
spec = importlib.util.spec_from_file_location(
    "symbol_info",
    os.path.join(os.path.dirname(__file__), '..', 'src', 'code_index_mcp', 'indexing', 'models', 'symbol_info.py')
)
symbol_info_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(symbol_info_module)
SymbolInfo = symbol_info_module.SymbolInfo


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
        assert len(symbol.imports) == 2

        # Test adding dependencies
        symbol.dependencies.append("helper_function")
        symbol.dependencies.append("util_function")
        assert "helper_function" in symbol.dependencies
        assert "util_function" in symbol.dependencies
        assert len(symbol.dependencies) == 2

        # Test called_by relationships
        symbol.called_by.append("main")
        symbol.called_by.append("test_runner")
        assert "main" in symbol.called_by
        assert "test_runner" in symbol.called_by
        assert len(symbol.called_by) == 2

        # Test exports
        symbol.exports.append("default")
        symbol.exports.append("named_export")
        assert "default" in symbol.exports
        assert "named_export" in symbol.exports
        assert len(symbol.exports) == 2

        # Test references
        symbol.references.append("module1.py:15")
        symbol.references.append("module2.py:32")
        assert "module1.py:15" in symbol.references
        assert "module2.py:32" in symbol.references
        assert len(symbol.references) == 2

    def test_symbol_info_with_semantic_data(self):
        """Test creating SymbolInfo with semantic data."""
        symbol = SymbolInfo(
            type="function",
            file="test.py",
            line=1,
            signature="def test_function(arg1, arg2)",
            docstring="Test function for semantic analysis",
            imports=["os", "sys"],
            exports=["test_function"],
            dependencies=["helper"],
            called_by=["main"],
            references=["test.py:10"]
        )

        # Verify all fields are set correctly
        assert symbol.type == "function"
        assert symbol.file == "test.py"
        assert symbol.line == 1
        assert symbol.signature == "def test_function(arg1, arg2)"
        assert symbol.docstring == "Test function for semantic analysis"

        # Verify semantic fields
        assert "os" in symbol.imports
        assert "sys" in symbol.imports
        assert "test_function" in symbol.exports
        assert "helper" in symbol.dependencies
        assert "main" in symbol.called_by
        assert "test.py:10" in symbol.references

    def test_symbol_info_immutable_defaults(self):
        """Test that default empty lists are properly isolated."""
        symbol1 = SymbolInfo(type="function", file="test1.py", line=1)
        symbol2 = SymbolInfo(type="function", file="test2.py", line=1)

        # Modify symbol1's lists
        symbol1.imports.append("os")
        symbol1.dependencies.append("helper1")

        # Verify symbol2 is not affected
        assert len(symbol2.imports) == 0
        assert len(symbol2.dependencies) == 0
        assert "os" not in symbol2.imports
        assert "helper1" not in symbol2.dependencies

    def test_symbol_info_backwards_compatibility(self):
        """Test that existing functionality still works."""
        symbol = SymbolInfo(
            type="function",
            file="test.py",
            line=1,
            signature="def old_function()",
            docstring="Old style function"
        )

        # Test existing called_by functionality
        symbol.called_by.append("caller1")
        assert "caller1" in symbol.called_by

        # Test all original fields work
        assert symbol.type == "function"
        assert symbol.file == "test.py"
        assert symbol.line == 1
        assert symbol.signature == "def old_function()"
        assert symbol.docstring == "Old style function"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])