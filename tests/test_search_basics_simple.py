"""Simplified basic search functionality tests.

Tests the core search patterns that users rely on.
Following Linus's principle: "Never break userspace."
"""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.code_index_mcp.services.search_service import SearchService
from src.code_index_mcp.tools.config.project_config_tool import ProjectConfigTool
from src.code_index_mcp.indexing.json_index_manager import JSONIndexManager


@pytest.mark.unit
class TestBasicSearchService:
    """Test fundamental search service operations."""

    def test_search_service_initialization(self):
        """Test SearchService initializes correctly."""
        mock_context = Mock()
        service = SearchService(mock_context)
        assert hasattr(service, 'helper')

    def test_search_code_basic_validation(self):
        """Test search_code validates basic parameters."""
        mock_context = Mock()
        service = SearchService(mock_context)

        # Mock helper and required dependencies
        service.helper = Mock()
        service.helper.get_base_path_error.return_value = None
        service.helper.base_path = "/test/path"
        service.helper.settings = Mock()

        # Mock search strategy
        mock_strategy = Mock()
        mock_strategy.name = "test_strategy"
        mock_strategy.search.return_value = []
        service.helper.settings.get_preferred_search_tool.return_value = mock_strategy

        with patch('src.code_index_mcp.utils.ValidationHelper.validate_search_pattern') as mock_validate, \
             patch('src.code_index_mcp.utils.ResponseFormatter.search_results_response') as mock_formatter:

            mock_validate.return_value = None
            mock_formatter.return_value = {"status": "success", "results": []}

            # Test basic search
            result = service.search_code(pattern="test")

            assert result["status"] == "success"
            mock_validate.assert_called_once()

    def test_search_code_project_not_setup(self):
        """Test search_code when project not set up."""
        mock_context = Mock()
        service = SearchService(mock_context)

        service.helper = Mock()
        service.helper.get_base_path_error.return_value = "No project path set"

        # Should raise ValueError
        with pytest.raises(ValueError, match="No project path set"):
            service.search_code(pattern="test")

    def test_search_code_invalid_pattern(self):
        """Test search_code with invalid pattern."""
        mock_context = Mock()
        service = SearchService(mock_context)

        service.helper = Mock()
        service.helper.get_base_path_error.return_value = None

        with patch('src.code_index_mcp.utils.ValidationHelper.validate_search_pattern') as mock_validate:
            mock_validate.return_value = "Invalid pattern"

            # Should raise ValueError
            with pytest.raises(ValueError, match="Invalid pattern"):
                service.search_code(pattern="[invalid")


@pytest.mark.unit
class TestIndexManagerBasics:
    """Test basic index manager functionality."""

    def test_json_index_manager_initialization(self):
        """Test JSONIndexManager initializes correctly."""
        manager = JSONIndexManager()
        assert manager.project_path is None
        assert manager.index_builder is None

    def test_set_project_path_valid(self):
        """Test setting valid project path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = JSONIndexManager()
            success = manager.set_project_path(temp_dir)
            assert success == True
            assert manager.project_path == temp_dir

    def test_set_project_path_invalid(self):
        """Test setting invalid project path."""
        manager = JSONIndexManager()
        success = manager.set_project_path("/nonexistent/path")
        assert success == False
        assert manager.project_path is None


@pytest.mark.unit
class TestProjectConfigTool:
    """Test project configuration tool basics."""

    def test_project_config_tool_initialization(self):
        """Test ProjectConfigTool initializes correctly."""
        tool = ProjectConfigTool()
        assert tool._settings is None
        assert tool._project_path is None

    def test_initialize_settings_valid_path(self):
        """Test initializing settings with valid path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = ProjectConfigTool()
            settings = tool.initialize_settings(temp_dir)
            assert settings is not None
            assert tool._project_path == temp_dir

    def test_initialize_settings_invalid_path(self):
        """Test initializing settings with invalid path."""
        tool = ProjectConfigTool()

        with pytest.raises(ValueError, match="Project path does not exist"):
            tool.initialize_settings("/nonexistent/path")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])