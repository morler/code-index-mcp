"""Simple unit tests for SemanticSearchService.

Basic tests that verify the core functionality without complex mocking.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.code_index_mcp.services.semantic_search_service import SemanticSearchService


class TestSemanticSearchBasics:
    """Test basic functionality of semantic search service."""

    def test_service_creation(self):
        """Test that service can be created."""
        mock_context = Mock()
        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            assert service is not None

    def test_empty_symbol_name_validation(self):
        """Test validation of empty symbol names."""
        mock_context = Mock()
        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            with pytest.raises(ValueError, match="Symbol name cannot be empty"):
                service.find_references("")

    def test_whitespace_symbol_name_validation(self):
        """Test validation of whitespace-only symbol names."""
        mock_context = Mock()
        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            with pytest.raises(ValueError, match="Symbol name cannot be empty"):
                service.find_references("   ")

    @patch('src.code_index_mcp.services.semantic_search_service.ResponseFormatter.semantic_search_response')
    def test_find_references_calls_formatter(self, mock_formatter):
        """Test that find_references calls the response formatter."""
        mock_context = Mock()
        mock_formatter.return_value = {"test": "response"}

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            # Mock the index_manager property
            mock_index_manager = Mock()
            mock_index_manager.find_symbol_references.return_value = []

            with patch.object(type(service), 'index_manager', mock_index_manager):
                result = service.find_references("test_symbol")

                assert result == {"test": "response"}
                mock_formatter.assert_called_once_with(
                    query="test_symbol",
                    results=[],
                    search_type="references"
                )

    @patch('src.code_index_mcp.services.semantic_search_service.ResponseFormatter.semantic_search_response')
    def test_find_definition_calls_formatter(self, mock_formatter):
        """Test that find_definition calls the response formatter."""
        mock_context = Mock()
        mock_formatter.return_value = {"test": "response"}

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            # Mock the index_manager property
            mock_index_manager = Mock()
            mock_index_manager.search_symbols.return_value = []

            with patch.object(type(service), 'index_manager', mock_index_manager):
                result = service.find_definition("test_symbol")

                assert result == {"test": "response"}
                mock_formatter.assert_called_once_with(
                    query="test_symbol",
                    results=[],
                    search_type="definition"
                )

    def test_no_index_manager_error(self):
        """Test error when index manager is not available."""
        mock_context = Mock()

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            # Mock the index_manager property to return None
            with patch.object(type(service), 'index_manager', None):
                with pytest.raises(ValueError, match="Index manager not available"):
                    service.find_references("test_symbol")

    def test_symbol_name_trimming(self):
        """Test that symbol names are properly trimmed."""
        mock_context = Mock()

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            mock_index_manager = Mock()
            mock_index_manager.find_symbol_references.return_value = []

            with patch.object(type(service), 'index_manager', mock_index_manager):
                with patch('src.code_index_mcp.services.semantic_search_service.ResponseFormatter.semantic_search_response'):
                    service.find_references("  test_symbol  ")

                    # Verify the trimmed name was used
                    mock_index_manager.find_symbol_references.assert_called_once_with("test_symbol")


class TestSemanticSearchResponseFormat:
    """Test the response format from semantic search operations."""

    def test_response_format_structure(self):
        """Test that responses have the correct structure using real ResponseFormatter."""
        mock_context = Mock()

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            mock_index_manager = Mock()
            mock_index_manager.find_symbol_references.return_value = [
                {"file": "test.py", "line": 5, "type": "function", "signature": "def test()"}
            ]

            with patch.object(type(service), 'index_manager', mock_index_manager):
                result = service.find_references("test_symbol")

                # Verify response structure
                assert "query" in result
                assert "search_type" in result
                assert "results" in result
                assert result["query"] == "test_symbol"
                assert result["search_type"] == "references"
                assert isinstance(result["results"], list)

    def test_definition_response_includes_metadata(self):
        """Test that definition responses include all expected metadata."""
        mock_context = Mock()

        with patch('src.code_index_mcp.services.semantic_search_service.BaseService.__init__', return_value=None):
            service = SemanticSearchService(mock_context)
            service._require_project_setup = Mock()

            mock_index_manager = Mock()
            mock_index_manager.search_symbols.return_value = [
                {
                    "id": "test.py:TestClass",
                    "file": "test.py",
                    "line": 10,
                    "type": "class",
                    "signature": "class TestClass:",
                    "docstring": "A test class"
                }
            ]

            with patch.object(type(service), 'index_manager', mock_index_manager):
                result = service.find_definition("TestClass")

                # Verify response contains expected fields
                assert len(result["results"]) == 1
                definition = result["results"][0]
                assert "file" in definition
                assert "line" in definition
                assert "symbol_type" in definition
                assert "signature" in definition
                assert "docstring" in definition