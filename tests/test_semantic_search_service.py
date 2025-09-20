"""Unit tests for SemanticSearchService.

Tests the semantic search functionality following Linus's principles:
"Good programmers worry about data structures."

Each method is tested in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

from src.code_index_mcp.services.semantic_search_service import SemanticSearchService
from src.code_index_mcp.utils import ResponseFormatter


class TestSemanticSearchService:
    """Test the semantic search service functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock()
        return ctx

    @pytest.fixture
    def mock_service(self, mock_context):
        """Create a semantic search service with mocked dependencies."""
        service = SemanticSearchService.__new__(SemanticSearchService)
        service.ctx = mock_context
        service.helper = Mock()
        service._require_project_setup = Mock()

        # Create a mock that will be returned by the index_manager property
        mock_index_manager = Mock()

        # Patch the property to return our mock
        with patch.object(type(service), 'index_manager', new_callable=lambda: mock_index_manager):
            yield service

    def test_find_references_success(self, mock_service):
        """Test successful reference finding."""
        # Arrange
        symbol_name = "test_function"
        mock_references = [
            {
                "file": "test.py",
                "line": 10,
                "type": "function",
                "signature": "def test_function():"
            }
        ]

        mock_service.index_manager.find_symbol_references.return_value = mock_references

        # Act
        result = mock_service.find_references(symbol_name)

        # Assert
        mock_service._require_project_setup.assert_called_once()
        mock_service.index_manager.find_symbol_references.assert_called_once_with(symbol_name)

        assert result["query"] == symbol_name
        assert result["search_type"] == "references"
        assert len(result["results"]) == 1
        assert result["results"][0]["file"] == "test.py"
        assert result["results"][0]["symbol_name"] == symbol_name

    def test_find_references_empty_symbol_name(self, mock_service):
        """Test that empty symbol name raises ValueError."""
        with pytest.raises(ValueError, match="Symbol name cannot be empty"):
            mock_service.find_references("")

    def test_find_references_whitespace_symbol_name(self, mock_service):
        """Test that whitespace-only symbol name raises ValueError."""
        with pytest.raises(ValueError, match="Symbol name cannot be empty"):
            mock_service.find_references("   ")

    def test_find_references_no_index_manager(self, mock_service):
        """Test that missing index manager raises ValueError."""
        mock_service.index_manager = None

        with pytest.raises(ValueError, match="Index manager not available"):
            mock_service.find_references("test_symbol")

    def test_find_definition_success(self, mock_service):
        """Test successful definition finding."""
        # Arrange
        symbol_name = "TestClass"
        mock_symbols = [
            {
                "id": "test.py:TestClass",
                "file": "test.py",
                "line": 5,
                "type": "class",
                "signature": "class TestClass:",
                "docstring": "A test class"
            }
        ]

        mock_service.index_manager.search_symbols.return_value = mock_symbols

        # Act
        result = mock_service.find_definition(symbol_name)

        # Assert
        mock_service._require_project_setup.assert_called_once()
        mock_service.index_manager.search_symbols.assert_called_once_with(symbol_name)

        assert result["query"] == symbol_name
        assert result["search_type"] == "definition"
        assert len(result["results"]) == 1
        assert result["results"][0]["symbol_type"] == "class"
        assert result["results"][0]["signature"] == "class TestClass:"

    def test_find_callers_success(self, mock_service):
        """Test successful caller finding."""
        # Arrange
        function_name = "helper_function"
        mock_caller_names = ["main_function", "another_function"]
        mock_caller_symbols = [
            {
                "file": "main.py",
                "line": 15,
                "type": "function",
                "signature": "def main_function():"
            }
        ]

        mock_service.index_manager.get_symbol_callers.return_value = mock_caller_names
        mock_service.index_manager.search_symbols.return_value = mock_caller_symbols

        # Act
        result = mock_service.find_callers(function_name)

        # Assert
        mock_service._require_project_setup.assert_called_once()
        mock_service.index_manager.get_symbol_callers.assert_called_once_with(function_name)

        assert result["query"] == function_name
        assert result["search_type"] == "callers"
        # We expect 2 results (one for each caller name)
        assert len(result["results"]) == 2

    def test_find_implementations_success(self, mock_service):
        """Test successful implementation finding."""
        # Arrange
        interface_name = "IRepository"
        mock_class_symbols = [
            {
                "id": "repo.py:UserRepository",
                "file": "repo.py",
                "line": 20,
                "type": "class",
                "signature": "class UserRepository implements IRepository"
            },
            {
                "id": "other.py:OtherClass",
                "file": "other.py",
                "line": 30,
                "type": "class",
                "signature": "class OtherClass"
            }
        ]

        mock_service.index_manager.search_symbols.return_value = mock_class_symbols

        # Act
        result = mock_service.find_implementations(interface_name)

        # Assert
        mock_service._require_project_setup.assert_called_once()
        mock_service.index_manager.search_symbols.assert_called_once_with("", symbol_type="class")

        assert result["query"] == interface_name
        assert result["search_type"] == "implementations"
        # Only one implementation should be found (the one containing "IRepository" in signature)
        assert len(result["results"]) == 1
        assert result["results"][0]["implementation_name"] == "UserRepository"

    def test_find_symbol_hierarchy_success(self, mock_service):
        """Test successful symbol hierarchy finding."""
        # Arrange
        class_name = "BaseClass"
        mock_target_symbols = [
            {
                "id": "base.py:BaseClass",
                "file": "base.py",
                "line": 10,
                "type": "class",
                "signature": "class BaseClass"
            }
        ]
        mock_all_classes = [
            {
                "id": "child.py:ChildClass",
                "file": "child.py",
                "line": 20,
                "type": "class",
                "signature": "class ChildClass extends BaseClass"
            }
        ]

        mock_service.index_manager.search_symbols.side_effect = [
            mock_target_symbols,  # First call for target class
            mock_all_classes      # Second call for all classes
        ]

        # Act
        result = mock_service.find_symbol_hierarchy(class_name)

        # Assert
        mock_service._require_project_setup.assert_called_once()

        assert result["query"] == class_name
        assert result["search_type"] == "hierarchy"
        assert "root_class" in result["results"]
        assert result["results"]["root_class"] == class_name
        assert "related_classes" in result["results"]
        assert len(result["results"]["related_classes"]) == 1

    def test_find_symbol_hierarchy_class_not_found(self, mock_service):
        """Test hierarchy finding when class is not found."""
        # Arrange
        class_name = "NonExistentClass"
        mock_service.index_manager.search_symbols.return_value = []

        # Act
        result = mock_service.find_symbol_hierarchy(class_name)

        # Assert
        assert result["query"] == class_name
        assert result["search_type"] == "hierarchy"
        assert "message" in result
        assert "not found" in result["message"]

    def test_exception_handling_in_find_references(self, mock_service):
        """Test that exceptions in find_references are properly handled."""
        # Arrange
        mock_service.index_manager.find_symbol_references.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to find references"):
            mock_service.find_references("test_symbol")

    def test_exception_handling_in_find_definition(self, mock_service):
        """Test that exceptions in find_definition are properly handled."""
        # Arrange
        mock_service.index_manager.search_symbols.side_effect = Exception("Search error")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to find definition"):
            mock_service.find_definition("test_symbol")

    def test_exception_handling_in_find_callers(self, mock_service):
        """Test that exceptions in find_callers are properly handled."""
        # Arrange
        mock_service.index_manager.get_symbol_callers.side_effect = Exception("Caller error")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to find callers"):
            mock_service.find_callers("test_function")

    def test_symbol_name_stripped(self, mock_service):
        """Test that symbol names are properly stripped of whitespace."""
        # Arrange
        symbol_name_with_spaces = "  test_function  "
        mock_service.index_manager.find_symbol_references.return_value = []

        # Act
        mock_service.find_references(symbol_name_with_spaces)

        # Assert - should be called with stripped name
        mock_service.index_manager.find_symbol_references.assert_called_once_with("test_function")

    @patch('src.code_index_mcp.services.semantic_search_service.ResponseFormatter.semantic_search_response')
    def test_response_formatter_called(self, mock_formatter, mock_service):
        """Test that ResponseFormatter is called with correct parameters."""
        # Arrange
        mock_service.index_manager.find_symbol_references.return_value = []
        mock_formatter.return_value = {"formatted": "response"}

        # Act
        result = mock_service.find_references("test_symbol")

        # Assert
        mock_formatter.assert_called_once_with(
            query="test_symbol",
            results=[],
            search_type="references"
        )
        assert result == {"formatted": "response"}


class TestSemanticSearchIntegration:
    """Integration tests that test the service with actual ResponseFormatter."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock()
        return ctx

    @pytest.fixture
    def service_with_real_formatter(self, mock_context):
        """Create service with real ResponseFormatter but mocked index manager."""
        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service.ctx = mock_context
            service.helper = Mock()
            service.index_manager = Mock()
            service._require_project_setup = Mock()
            return service

    def test_response_format_structure(self, service_with_real_formatter):
        """Test that the response has the correct structure."""
        # Arrange
        service = service_with_real_formatter
        service.index_manager.find_symbol_references.return_value = [
            {"file": "test.py", "line": 5, "type": "function", "signature": "def test()"}
        ]

        # Act
        result = service.find_references("test_symbol")

        # Assert
        assert "query" in result
        assert "search_type" in result
        assert "results" in result
        assert result["query"] == "test_symbol"
        assert result["search_type"] == "references"
        assert isinstance(result["results"], list)