"""Core services unit tests.

Tests individual service classes following Linus's principle:
"Good programmers worry about data structures."

Each service is tested in isolation with mocked dependencies.
"""

import tempfile
import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Dict, Any

from src.code_index_mcp.services.base_service import BaseService
from src.code_index_mcp.services.project_management_service import ProjectManagementService
from src.code_index_mcp.services.search_service import SearchService
from src.code_index_mcp.services.file_discovery_service import FileDiscoveryService
from src.code_index_mcp.utils import ContextHelper


class TestBaseService:
    """Test the base service that all others inherit from."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock()
        return ctx

    @pytest.fixture
    def mock_helper(self, mock_context):
        """Create a base service with mocked helper."""
        with patch('src.code_index_mcp.services.base_service.ContextHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper_class.return_value = mock_helper
            service = BaseService(mock_context)
            service.helper = mock_helper
            return service, mock_helper

    def test_base_service_initialization(self, mock_context):
        """Test that BaseService initializes correctly."""
        service = BaseService(mock_context)
        assert service.ctx == mock_context
        assert hasattr(service, 'helper')

    def test_validate_project_setup_success(self, mock_helper):
        """Test project validation when properly set up."""
        service, helper = mock_helper
        helper.get_base_path_error.return_value = None

        result = service._validate_project_setup()
        assert result is None
        helper.get_base_path_error.assert_called_once()

    def test_validate_project_setup_failure(self, mock_helper):
        """Test project validation when not set up."""
        service, helper = mock_helper
        helper.get_base_path_error.return_value = "Project not initialized"

        result = service._validate_project_setup()
        assert result == "Project not initialized"

    def test_require_project_setup_success(self, mock_helper):
        """Test require project setup when valid."""
        service, helper = mock_helper
        helper.get_base_path_error.return_value = None

        # Should not raise
        service._require_project_setup()

    def test_require_project_setup_failure(self, mock_helper):
        """Test require project setup when invalid."""
        service, helper = mock_helper
        helper.get_base_path_error.return_value = "Project not initialized"

        with pytest.raises(ValueError, match="Project not initialized"):
            service._require_project_setup()

    def test_base_path_property(self, mock_helper):
        """Test base_path property access."""
        service, helper = mock_helper
        helper.base_path = "/test/path"

        assert service.base_path == "/test/path"

    def test_file_count_property(self, mock_helper):
        """Test file_count property access."""
        service, helper = mock_helper
        helper.file_count = 42

        assert service.file_count == 42


class TestProjectManagementService:
    """Test project management business logic."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        return Mock()

    @pytest.fixture
    def temp_project_path(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def service_with_mocks(self, mock_context):
        """Create ProjectManagementService with all dependencies mocked."""
        with patch('src.code_index_mcp.services.project_management_service.get_index_manager') as mock_get_manager, \
             patch('src.code_index_mcp.tools.config.ProjectConfigTool') as mock_config_tool, \
             patch('src.code_index_mcp.tools.monitoring.FileWatcherTool') as mock_watcher_tool, \
             patch('src.code_index_mcp.services.base_service.ContextHelper') as mock_helper_class:

            mock_index_manager = Mock()
            mock_get_manager.return_value = mock_index_manager

            mock_config = Mock()
            mock_config_tool.return_value = mock_config

            mock_watcher = Mock()
            mock_watcher_tool.return_value = mock_watcher

            mock_helper = Mock()
            mock_helper_class.return_value = mock_helper

            service = ProjectManagementService(mock_context)

            # Store mocks for easy access in tests
            service._test_mocks = {
                'index_manager': mock_index_manager,
                'config_tool': mock_config,
                'watcher_tool': mock_watcher,
                'helper': mock_helper
            }

            return service

    def test_initialization_with_mocks(self, service_with_mocks):
        """Test service initializes with all dependencies."""
        service = service_with_mocks
        mocks = service._test_mocks

        assert service._index_manager == mocks['index_manager']
        assert service._config_tool == mocks['config_tool']
        assert service._watcher_tool == mocks['watcher_tool']

    def test_initialize_project_new_setup(self, service_with_mocks, temp_project_path):
        """Test initializing a new project."""
        service = service_with_mocks
        mocks = service._test_mocks

        # Mock successful initialization - fix Mock return value
        mocks['config_tool'].validate_project_path.return_value = None  # No error
        mocks['config_tool'].normalize_project_path.return_value = temp_project_path  # Return actual path
        mocks['config_tool'].initialize_project.return_value = None
        mocks['config_tool'].get_search_tool_info.return_value = {"available": True, "tools": ["ugrep"], "name": "ugrep"}
        mocks['index_manager'].set_project_path.return_value = True  # Success
        mocks['index_manager'].get_file_count.return_value = 5
        mocks['helper'].get_search_tools_status.return_value = "ugrep available"
        mocks['watcher_tool'].get_status.return_value = {"enabled": True, "status": "running"}

        result = service.initialize_project(temp_project_path)

        # Verify method calls
        mocks['config_tool'].validate_project_path.assert_called_once_with(temp_project_path)
        mocks['config_tool'].initialize_project.assert_called_once_with(temp_project_path)
        mocks['index_manager'].set_project_path.assert_called_once_with(temp_project_path)

        # Verify result structure
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["project_path"] == temp_project_path


class TestSearchService:
    """Test search service business logic."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        return Mock()

    @pytest.fixture
    def service_with_mocks(self, mock_context):
        """Create SearchService with dependencies mocked."""
        with patch('src.code_index_mcp.services.base_service.ContextHelper') as mock_helper_class:
            mock_helper = Mock()
            mock_helper_class.return_value = mock_helper

            service = SearchService(mock_context)
            service.helper = mock_helper

            return service, mock_helper

    def test_search_service_initialization(self, mock_context):
        """Test SearchService initializes correctly."""
        service = SearchService(mock_context)
        assert hasattr(service, 'helper')

    def test_search_code_parameter_validation(self, service_with_mocks):
        """Test search_code validates its parameters."""
        service, mock_helper = service_with_mocks

        # Mock project setup validation
        mock_helper.get_base_path_error.return_value = None
        mock_helper.base_path = "/test/path"

        # Mock settings and search strategy
        mock_settings = Mock()
        mock_strategy = Mock()
        mock_strategy.name = "test_strategy"
        mock_strategy.search.return_value = []
        mock_settings.get_preferred_search_tool.return_value = mock_strategy
        service.helper.settings = mock_settings

        with patch('src.code_index_mcp.search.base.is_safe_regex_pattern') as mock_safe_check, \
             patch('src.code_index_mcp.utils.ValidationHelper.validate_search_pattern') as mock_validate_pattern, \
             patch('src.code_index_mcp.utils.ResponseFormatter.search_results_response') as mock_formatter:

            mock_safe_check.return_value = True
            mock_validate_pattern.return_value = None  # No error
            mock_formatter.return_value = {"status": "success", "results": []}

            # Test basic call
            result = service.search_code("test_pattern")

            # Verify the search was executed
            mock_strategy.search.assert_called_once()
            assert isinstance(result, dict)
            assert result["status"] == "success"

    def test_search_code_unsafe_pattern_rejection(self, service_with_mocks):
        """Test that unsafe regex patterns are rejected."""
        service, mock_helper = service_with_mocks

        mock_helper.get_base_path_error.return_value = None

        with patch('src.code_index_mcp.utils.ValidationHelper.validate_search_pattern') as mock_validate_pattern:
            mock_validate_pattern.return_value = "Unsafe regex pattern detected"

            # This should raise ValueError due to unsafe pattern
            with pytest.raises(ValueError, match="Unsafe regex pattern detected"):
                service.search_code("(a+)+b")  # Potential ReDoS pattern


class TestFileDiscoveryService:
    """Test file discovery service logic."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        return Mock()

    @pytest.fixture
    def service_with_mocks(self, mock_context):
        """Create FileDiscoveryService with dependencies mocked."""
        with patch('src.code_index_mcp.services.base_service.ContextHelper') as mock_helper_class, \
             patch('src.code_index_mcp.services.file_discovery_service.get_index_manager') as mock_get_index:

            mock_helper = Mock()
            mock_helper_class.return_value = mock_helper

            mock_index_manager = Mock()
            mock_get_index.return_value = mock_index_manager

            service = FileDiscoveryService(mock_context)
            service.helper = mock_helper

            return service, mock_helper

    def test_find_files_basic_pattern(self, service_with_mocks):
        """Test basic file pattern matching."""
        service, mock_helper = service_with_mocks

        mock_helper.get_base_path_error.return_value = None

        # Mock the index manager's find_files method
        service._index_manager.find_files.return_value = ["/path/test.py", "/path/module.py"]

        result = service.find_files("*.py")

        # find_files returns a list directly, not a dict
        assert isinstance(result, list)
        assert len(result) == 2
        assert "/path/test.py" in result
        assert "/path/module.py" in result
        service._index_manager.find_files.assert_called_once_with("*.py")

    def test_find_files_project_not_setup(self, service_with_mocks):
        """Test file discovery when project not set up."""
        service, mock_helper = service_with_mocks

        mock_helper.get_base_path_error.return_value = "No project path set"

        # This should raise ValueError due to project not set up
        with pytest.raises(ValueError, match="No project path set"):
            service.find_files("*.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])