"""Unit tests for SemanticEditService.

Tests the semantic editing functionality following Linus's principles:
"Good programmers worry about data structures."
"Never break userspace" - ensure edits don't corrupt existing code.

Each method is tested in isolation with mocked dependencies.
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Dict, Any, List

from src.code_index_mcp.services.semantic_edit_service import SemanticEditService
from src.code_index_mcp.indexing.models import EditResult
from src.code_index_mcp.utils import ResponseFormatter


class TestSemanticEditService:
    """Test the semantic editing service functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock()
        return ctx

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_service(self, mock_context, temp_dir):
        """Create a semantic edit service with mocked dependencies."""
        service = SemanticEditService.__new__(SemanticEditService)
        service.ctx = mock_context
        service.helper = Mock()
        service._require_project_setup = Mock()
        service._require_valid_file_path = Mock()
        service._backup_dir = None

        # Create a mock index manager
        mock_index_manager = Mock()

        # Patch the properties to return our mocks
        with patch.object(type(service), 'index_manager', new_callable=lambda: mock_index_manager), \
             patch.object(type(service), 'base_path', new_callable=lambda: temp_dir):
            yield service

    def test_validate_symbol_name(self, mock_service):
        """Test symbol name validation."""
        # Valid names
        assert mock_service._validate_symbol_name("valid_name") == True
        assert mock_service._validate_symbol_name("ValidName") == True
        assert mock_service._validate_symbol_name("_private") == True
        assert mock_service._validate_symbol_name("name123") == True

        # Invalid names
        assert mock_service._validate_symbol_name("") == False
        assert mock_service._validate_symbol_name("  ") == False
        assert mock_service._validate_symbol_name("123invalid") == False
        assert mock_service._validate_symbol_name("invalid-name") == False
        assert mock_service._validate_symbol_name("invalid.name") == False
        assert mock_service._validate_symbol_name(None) == False

    def test_generate_diff(self, mock_service):
        """Test diff generation between file contents."""
        original = "line1\nline2\nline3\n"
        modified = "line1\nmodified_line2\nline3\n"

        diff = mock_service._generate_diff(original, modified, "test.py")

        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-line2" in diff
        assert "+modified_line2" in diff

    @patch('builtins.open', new_callable=mock_open, read_data="def old_function():\n    pass\n")
    def test_find_symbol_references_in_file(self, mock_file, mock_service):
        """Test finding symbol references in a file."""
        file_path = "test.py"
        symbol_name = "old_function"

        references = mock_service._find_symbol_references_in_file(file_path, symbol_name)

        assert len(references) == 1
        assert references[0][0] == 1  # line number
        assert "old_function" in references[0][1]  # line content

    def test_rename_symbol_invalid_names(self, mock_service):
        """Test rename_symbol with invalid symbol names."""
        # Test invalid old name
        result = mock_service.rename_symbol("", "new_name")
        assert result["success"] == False
        assert "Invalid symbol name" in result["error"]

        # Test invalid new name
        result = mock_service.rename_symbol("old_name", "123invalid")
        assert result["success"] == False
        assert "Invalid new symbol name" in result["error"]

        # Test identical names
        result = mock_service.rename_symbol("same_name", "same_name")
        assert result["success"] == True
        assert "identical" in result["error"]

    def test_rename_symbol_symbol_not_found(self, mock_service):
        """Test rename_symbol when symbol doesn't exist."""
        # Mock index manager to return empty results
        mock_service.index_manager.search_symbols.return_value = []

        result = mock_service.rename_symbol("nonexistent", "new_name")

        assert result["success"] == False
        assert "not found" in result["error"]

    def test_rename_symbol_conflict_detection(self, mock_service):
        """Test rename_symbol detects naming conflicts."""
        # Mock index manager to find existing symbols
        mock_service.index_manager.search_symbols.side_effect = [
            [{"file": "test.py", "id": "old_name"}],  # First call - symbol exists
            [{"file": "test.py", "id": "new_name"}]   # Second call - conflict exists
        ]
        mock_service.index_manager.find_symbol_references.return_value = []

        result = mock_service.rename_symbol("old_name", "new_name")

        assert result["success"] == False
        assert "already exists" in result["error"]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_rename_symbol_success(self, mock_makedirs, mock_copy, mock_file, mock_exists, mock_service):
        """Test successful symbol rename operation."""
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = [
            "def old_name():\n    pass\n",  # Original content
            "def new_name():\n    pass\n"   # Modified content (for diff)
        ]

        # Mock index manager responses
        mock_service.index_manager.search_symbols.side_effect = [
            [{"file": "test.py", "id": "old_name", "line": 1}],  # Symbol exists
            []  # No conflict
        ]
        mock_service.index_manager.find_symbol_references.return_value = [
            {"file": "test.py", "line": 1}
        ]

        with patch.object(mock_service, '_replace_symbol_in_file', return_value=True):
            result = mock_service.rename_symbol("old_name", "new_name")

        assert result["success"] == True
        assert "modified 1 file(s)" in result["message"]
        assert len(result["modified_files"]) == 1

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_add_import_file_not_found(self, mock_file, mock_exists, mock_service):
        """Test add_import with non-existent file."""
        mock_exists.return_value = False

        result = mock_service.add_import("nonexistent.py", "os")

        assert result["success"] == False
        assert "not found" in result["error"]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="import os\nimport sys\n\ndef main():\n    pass\n")
    def test_add_import_already_exists(self, mock_file, mock_exists, mock_service):
        """Test add_import when import already exists."""
        mock_exists.return_value = True

        result = mock_service.add_import("test.py", "os")

        assert result["success"] == True
        assert "already exists" in result["error"]
        assert len(result["modified_files"]) == 0

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_add_import_success(self, mock_makedirs, mock_copy, mock_file, mock_exists, mock_service):
        """Test successful import addition."""
        mock_exists.return_value = True

        # Mock file content without the import we're adding
        original_content = "import sys\n\ndef main():\n    pass\n"
        mock_file.return_value.read.return_value = original_content

        with patch.object(mock_service, '_backup_file'), \
             patch.object(mock_service, '_generate_diff', return_value="+ import os\n"):
            result = mock_service.add_import("test.py", "os")

        assert result["success"] == True
        assert len(result["modified_files"]) == 1
        assert "test.py" in result["modified_files"]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_remove_unused_imports_no_unused(self, mock_file, mock_exists, mock_service):
        """Test remove_unused_imports when no unused imports exist."""
        mock_exists.return_value = True

        # Mock file with all imports being used
        content = "import os\nprint(os.getcwd())\n"
        mock_file.return_value.read.return_value = content
        mock_file.return_value.readlines.return_value = content.splitlines(True)

        result = mock_service.remove_unused_imports("test.py")

        assert result["success"] == True
        assert "No unused imports" in result["error"]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_remove_unused_imports_success(self, mock_makedirs, mock_copy, mock_file, mock_exists, mock_service):
        """Test successful removal of unused imports."""
        mock_exists.return_value = True

        # Mock file content with unused import
        original_content = "import os\nimport sys\nprint('hello')\n"
        mock_file.return_value.read.return_value = original_content
        mock_file.return_value.readlines.return_value = original_content.splitlines(True)

        with patch.object(mock_service, '_backup_file'), \
             patch.object(mock_service, '_generate_diff', return_value="- import os\n- import sys\n"):
            result = mock_service.remove_unused_imports("test.py")

        assert result["success"] == True
        assert len(result["modified_files"]) == 1
        assert len(result["affected_symbols"]) == 2

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_organize_imports_no_imports(self, mock_file, mock_exists, mock_service):
        """Test organize_imports when no imports exist."""
        mock_exists.return_value = True

        content = "def main():\n    pass\n"
        mock_file.return_value.read.return_value = content
        mock_file.return_value.readlines.return_value = content.splitlines(True)

        result = mock_service.organize_imports("test.py")

        assert result["success"] == True
        assert "No imports found" in result["error"]

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_organize_imports_success(self, mock_makedirs, mock_copy, mock_file, mock_exists, mock_service):
        """Test successful import organization."""
        mock_exists.return_value = True

        # Mock disorganized imports
        original_content = "from .local import something\nimport sys\nimport os\n\ndef main():\n    pass\n"
        mock_file.return_value.read.return_value = original_content
        mock_file.return_value.readlines.return_value = original_content.splitlines(True)

        with patch.object(mock_service, '_backup_file'), \
             patch.object(mock_service, '_generate_diff', return_value="organized imports diff"):
            result = mock_service.organize_imports("test.py")

        assert result["success"] == True
        assert len(result["modified_files"]) == 1

    @patch('os.path.exists')
    def test_rollback_operation_invalid_backup(self, mock_exists, mock_service):
        """Test rollback with invalid backup info."""
        mock_exists.return_value = False

        result = mock_service.rollback_operation("invalid_backup_path")

        assert result["success"] == False
        assert "Invalid or missing backup" in result["error"]

    @patch('os.path.exists')
    @patch('os.walk')
    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_rollback_operation_success(self, mock_makedirs, mock_copy, mock_walk, mock_exists, mock_service):
        """Test successful rollback operation."""
        mock_exists.return_value = True
        mock_walk.return_value = [
            ("/backup", [], ["test.py"]),
        ]

        result = mock_service.rollback_operation("/backup")

        assert result["success"] == True
        assert len(result["modified_files"]) == 1
        mock_copy.assert_called_once()

    def test_edit_result_creation(self, mock_service):
        """Test EditResult data model creation and usage."""
        edit_result = EditResult(
            success=True,
            modified_files=["test.py"],
            changes_preview={"test.py": "diff content"},
            rollback_info="/backup",
            operation_type="rename_symbol",
            affected_symbols=["old_name", "new_name"]
        )

        assert edit_result.success == True
        assert edit_result.has_changes() == True
        assert "Modified 1 file(s)" in edit_result.get_summary()
        assert len(edit_result.affected_symbols) == 2

    def test_backup_directory_creation(self, mock_service, temp_dir):
        """Test backup directory creation."""
        with patch('time.time', return_value=1234567890), \
             patch('os.makedirs') as mock_makedirs:
            backup_dir = mock_service._create_backup_directory()

            expected_path = os.path.join(temp_dir, ".semantic_backups", "semantic_edit_backup_1234567890")
            assert backup_dir == expected_path
            mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)

    @patch('shutil.copy2')
    @patch('os.makedirs')
    def test_backup_file(self, mock_makedirs, mock_copy, mock_service, temp_dir):
        """Test individual file backup."""
        test_file = os.path.join(temp_dir, "test.py")

        with patch.object(mock_service, '_create_backup_directory', return_value="/backup"):
            backup_path = mock_service._backup_file(test_file)

            # Use os.path.join for cross-platform compatibility
            expected_backup = os.path.join("/backup", "test.py")
            assert backup_path == expected_backup
            mock_copy.assert_called_once()

class TestSemanticEditServiceIntegration:
    """Integration tests for semantic edit service."""

    @pytest.fixture
    def real_temp_dir(self):
        """Create a real temporary directory with test files."""
        temp_dir = tempfile.mkdtemp()

        # Create test file
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("""import os
import sys

def old_function():
    return "hello"

def main():
    result = old_function()
    print(result)
""")

        yield temp_dir, test_file
        shutil.rmtree(temp_dir)

    def test_real_file_backup_and_modify(self, real_temp_dir):
        """Test real file backup and modification."""
        temp_dir, test_file = real_temp_dir

        # Create service with real context
        mock_ctx = Mock()
        service = SemanticEditService(mock_ctx)
        service._require_project_setup = Mock()
        service._require_valid_file_path = Mock()

        # Mock the base_path property
        with patch.object(type(service), 'base_path', new_callable=lambda: temp_dir):
            # Test backup creation
            backup_path = service._backup_file(test_file)
            assert os.path.exists(backup_path)

            # Verify backup content matches original
            with open(test_file, 'r') as original, open(backup_path, 'r') as backup:
                assert original.read() == backup.read()

    def test_real_symbol_replacement(self, real_temp_dir):
        """Test real symbol replacement in file."""
        temp_dir, test_file = real_temp_dir

        # Create service with real context
        mock_ctx = Mock()
        service = SemanticEditService(mock_ctx)

        # Mock the base_path property
        with patch.object(type(service), 'base_path', new_callable=lambda: temp_dir):
            # Read original content
            with open(test_file, 'r') as f:
                original_content = f.read()

            # Perform replacement
            success = service._replace_symbol_in_file(test_file, "old_function", "new_function")
            assert success == True

            # Verify replacement
            with open(test_file, 'r') as f:
                new_content = f.read()

            assert "old_function" not in new_content
            assert "new_function" in new_content
            assert new_content.count("new_function") == 2  # definition and call

    def test_real_import_addition(self, real_temp_dir):
        """Test real import addition to file."""
        temp_dir, test_file = real_temp_dir

        # Create service
        mock_ctx = Mock()
        service = SemanticEditService(mock_ctx)
        service._require_project_setup = Mock()
        service._require_valid_file_path = Mock()

        # Mock the base_path property
        with patch.object(type(service), 'base_path', new_callable=lambda: temp_dir):
            # Add import
            result = service.add_import(test_file, "json")

            assert result["success"] == True
            assert test_file in result["modified_files"]

            # Verify import was added
            with open(test_file, 'r') as f:
                content = f.read()

            assert "import json" in content