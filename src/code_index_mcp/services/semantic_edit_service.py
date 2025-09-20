"""
Semantic editing service for the Code Index MCP server.

This service provides semantic code editing capabilities including symbol renaming,
import management, and other safe refactoring operations.
"""

import os
import re
import shutil
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
import difflib
import time

from .base_service import BaseService
from ..indexing.models import EditResult
from ..utils import ResponseFormatter


class SemanticEditService(BaseService):
    """
    Service for managing semantic code editing operations.

    This service provides safe semantic editing capabilities:
    - Rename symbols across the project while maintaining consistency
    - Add import statements intelligently
    - Remove unused imports
    - Organize import statements
    - Create backup and rollback mechanisms
    """

    def __init__(self, ctx):
        """Initialize the semantic edit service."""
        super().__init__(ctx)
        self._backup_dir = None

    def _create_backup_directory(self) -> str:
        """Create a backup directory for rollback purposes."""
        if not self._backup_dir:
            timestamp = str(int(time.time()))
            backup_name = f"semantic_edit_backup_{timestamp}"
            self._backup_dir = os.path.join(self.base_path, ".semantic_backups", backup_name)
            os.makedirs(self._backup_dir, exist_ok=True)
        return self._backup_dir

    def _backup_file(self, file_path: str) -> str:
        """Create backup of a file before modification."""
        backup_dir = self._create_backup_directory()
        rel_path = os.path.relpath(file_path, self.base_path)
        backup_path = os.path.join(backup_dir, rel_path)

        # Create backup directories
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        # Copy the file
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _generate_diff(self, original_content: str, new_content: str, file_path: str) -> str:
        """Generate a unified diff between original and new content."""
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
            lineterm=""
        )
        return "".join(diff)

    def _validate_symbol_name(self, symbol_name: str) -> bool:
        """Validate that a symbol name is valid for renaming."""
        if not symbol_name or not symbol_name.strip():
            return False

        # Basic validation - must be valid identifier
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', symbol_name.strip()) is not None

    def _find_symbol_references_in_file(self, file_path: str, symbol_name: str) -> List[Tuple[int, str]]:
        """Find all references to a symbol in a specific file."""
        references = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Simple regex-based detection - could be enhanced with AST parsing
                pattern = r'\b' + re.escape(symbol_name) + r'\b'
                if re.search(pattern, line):
                    references.append((line_num, line.strip()))

        except Exception:
            # Skip files that can't be read
            pass

        return references

    def _replace_symbol_in_file(self, file_path: str, old_name: str, new_name: str) -> bool:
        """Replace all occurrences of a symbol in a file."""
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Create backup
            self._backup_file(file_path)

            # Replace using word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(old_name) + r'\b'
            new_content = re.sub(pattern, new_name, original_content)

            # Write back if there were changes
            if new_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True

        except Exception:
            return False

        return False

    def rename_symbol(self, old_name: str, new_name: str, scope: str = "project") -> Dict[str, Any]:
        """
        Safely rename a symbol across the project.

        Args:
            old_name: Current name of the symbol
            new_name: New name for the symbol
            scope: Scope of the rename operation ("project", "file", etc.)

        Returns:
            Dictionary containing operation results
        """
        self._require_project_setup()

        # Validate input
        if not self._validate_symbol_name(old_name):
            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=False,
                modified_files=[],
                error_message=f"Invalid symbol name: {old_name}"
            )

        if not self._validate_symbol_name(new_name):
            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=False,
                modified_files=[],
                error_message=f"Invalid new symbol name: {new_name}"
            )

        if old_name == new_name:
            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=True,
                modified_files=[],
                error_message="Symbol names are identical, no changes needed"
            )

        # Check if symbol exists in the project
        if not self.index_manager:
            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=False,
                modified_files=[],
                error_message="Index manager not available"
            )

        try:
            # Find symbol definition
            symbols = self.index_manager.search_symbols(old_name)
            if not symbols:
                return ResponseFormatter.edit_operation_response(
                    operation_type="rename_symbol",
                    success=False,
                    modified_files=[],
                    error_message=f"Symbol '{old_name}' not found in project"
                )

            # Find all references
            references = self.index_manager.find_symbol_references(old_name)

            # Collect all files that need modification
            files_to_modify = set()
            for symbol in symbols:
                if 'file' in symbol:
                    files_to_modify.add(symbol['file'])

            for ref in references:
                if 'file' in ref:
                    files_to_modify.add(ref['file'])

            # Check for conflicts - ensure new name doesn't already exist
            existing_symbols = self.index_manager.search_symbols(new_name)
            if existing_symbols:
                return ResponseFormatter.edit_operation_response(
                    operation_type="rename_symbol",
                    success=False,
                    modified_files=[],
                    error_message=f"Symbol '{new_name}' already exists in the project"
                )

            # Perform the rename operation
            modified_files = []
            changes_preview = {}

            for file_path in files_to_modify:
                if not os.path.exists(file_path):
                    continue

                # Read original content for diff generation
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()

                # Perform replacement
                if self._replace_symbol_in_file(file_path, old_name, new_name):
                    modified_files.append(file_path)

                    # Generate diff for preview
                    with open(file_path, 'r', encoding='utf-8') as f:
                        new_content = f.read()

                    diff = self._generate_diff(original_content, new_content, file_path)
                    if diff:
                        changes_preview[file_path] = diff

            # Create EditResult
            edit_result = EditResult(
                success=True,
                modified_files=modified_files,
                changes_preview=changes_preview,
                rollback_info=self._backup_dir,
                operation_type="rename_symbol",
                affected_symbols=[old_name, new_name],
                backup_created=bool(self._backup_dir)
            )

            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=True,
                modified_files=modified_files,
                affected_symbols=[old_name, new_name],
                changes_preview=changes_preview,
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="rename_symbol",
                success=False,
                modified_files=[],
                error_message=f"Failed to rename symbol: {str(e)}"
            )

    def add_import(self, file_path: str, module_name: str, symbol_name: str = None) -> Dict[str, Any]:
        """
        Intelligently add an import statement to a file.

        Args:
            file_path: Path to the file
            module_name: Name of the module to import
            symbol_name: Specific symbol to import (for 'from X import Y')

        Returns:
            Dictionary containing operation results
        """
        self._require_project_setup()
        self._require_valid_file_path(file_path)

        if not os.path.exists(file_path):
            return ResponseFormatter.edit_operation_response(
                operation_type="add_import",
                success=False,
                modified_files=[],
                error_message=f"File not found: {file_path}"
            )

        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                lines = original_content.splitlines()

            # Check if import already exists
            if symbol_name:
                import_pattern = rf'from\s+{re.escape(module_name)}\s+import\s+.*\b{re.escape(symbol_name)}\b'
            else:
                import_pattern = rf'import\s+{re.escape(module_name)}(\s+as\s+\w+)?$'

            for line in lines:
                if re.search(import_pattern, line.strip()):
                    return ResponseFormatter.edit_operation_response(
                        operation_type="add_import",
                        success=True,
                        modified_files=[],
                        error_message="Import already exists"
                    )

            # Find the right place to insert the import
            insert_line = 0
            in_imports = False
            last_import_line = -1

            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    in_imports = True
                    last_import_line = i
                elif in_imports and stripped and not stripped.startswith('#'):
                    # Found first non-import, non-comment line after imports
                    insert_line = i
                    break

            if last_import_line >= 0:
                insert_line = last_import_line + 1

            # Create the import statement
            if symbol_name:
                import_statement = f"from {module_name} import {symbol_name}"
            else:
                import_statement = f"import {module_name}"

            # Insert the import
            self._backup_file(file_path)
            lines.insert(insert_line, import_statement)
            new_content = '\n'.join(lines)

            # Write the modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Generate diff
            diff = self._generate_diff(original_content, new_content, file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="add_import",
                success=True,
                modified_files=[file_path],
                affected_symbols=[symbol_name] if symbol_name else [module_name],
                changes_preview={file_path: diff},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="add_import",
                success=False,
                modified_files=[],
                error_message=f"Failed to add import: {str(e)}"
            )

    def remove_unused_imports(self, file_path: str) -> Dict[str, Any]:
        """
        Remove unused import statements from a file.

        Args:
            file_path: Path to the file to clean up

        Returns:
            Dictionary containing operation results
        """
        self._require_project_setup()
        self._require_valid_file_path(file_path)

        if not os.path.exists(file_path):
            return ResponseFormatter.edit_operation_response(
                operation_type="remove_unused_imports",
                success=False,
                modified_files=[],
                error_message=f"File not found: {file_path}"
            )

        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                lines = original_content.splitlines()

            # Simple unused import detection
            # This is a basic implementation - a full implementation would need AST parsing
            imports_to_remove = []
            new_lines = []

            for i, line in enumerate(lines):
                stripped = line.strip()

                # Check if it's an import line
                if stripped.startswith('import ') or stripped.startswith('from '):
                    # Extract imported symbols
                    if stripped.startswith('from '):
                        # from module import symbol1, symbol2
                        match = re.match(r'from\s+(\S+)\s+import\s+(.+)', stripped)
                        if match:
                            symbols = [s.strip() for s in match.group(2).split(',')]
                            # Check if any symbol is used in the file
                            used = False
                            for symbol in symbols:
                                if symbol != '*':  # Skip wildcard imports
                                    symbol_clean = symbol.split(' as ')[0].strip()
                                    if any(re.search(r'\b' + re.escape(symbol_clean) + r'\b', other_line)
                                           for j, other_line in enumerate(lines) if j != i):
                                        used = True
                                        break
                            if not used:
                                imports_to_remove.append(stripped)
                                continue
                    else:
                        # import module
                        match = re.match(r'import\s+(\S+)(\s+as\s+(\S+))?', stripped)
                        if match:
                            module = match.group(3) if match.group(3) else match.group(1)
                            # Check if module is used
                            if not any(re.search(r'\b' + re.escape(module) + r'\b', other_line)
                                      for j, other_line in enumerate(lines) if j != i):
                                imports_to_remove.append(stripped)
                                continue

                new_lines.append(line)

            if not imports_to_remove:
                return ResponseFormatter.edit_operation_response(
                    operation_type="remove_unused_imports",
                    success=True,
                    modified_files=[],
                    error_message="No unused imports found"
                )

            # Create backup and write new content
            self._backup_file(file_path)
            new_content = '\n'.join(new_lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Generate diff
            diff = self._generate_diff(original_content, new_content, file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="remove_unused_imports",
                success=True,
                modified_files=[file_path],
                affected_symbols=imports_to_remove,
                changes_preview={file_path: diff},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="remove_unused_imports",
                success=False,
                modified_files=[],
                error_message=f"Failed to remove unused imports: {str(e)}"
            )

    def organize_imports(self, file_path: str) -> Dict[str, Any]:
        """
        Organize and sort import statements in a file.

        Args:
            file_path: Path to the file to organize

        Returns:
            Dictionary containing operation results
        """
        self._require_project_setup()
        self._require_valid_file_path(file_path)

        if not os.path.exists(file_path):
            return ResponseFormatter.edit_operation_response(
                operation_type="organize_imports",
                success=False,
                modified_files=[],
                error_message=f"File not found: {file_path}"
            )

        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                lines = original_content.splitlines()

            # Extract imports and other content
            imports = []
            other_lines = []
            in_imports_section = True

            for line in lines:
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    if in_imports_section:
                        imports.append(line)
                    else:
                        # Import found after other code - leave it alone
                        other_lines.append(line)
                elif stripped == '' or stripped.startswith('#'):
                    # Empty line or comment - could be in imports section
                    if in_imports_section and imports:
                        imports.append(line)
                    else:
                        other_lines.append(line)
                else:
                    # First non-import line - end of imports section
                    in_imports_section = False
                    other_lines.append(line)

            if not imports:
                return ResponseFormatter.edit_operation_response(
                    operation_type="organize_imports",
                    success=True,
                    modified_files=[],
                    error_message="No imports found to organize"
                )

            # Sort imports: standard library, third-party, local imports
            stdlib_imports = []
            thirdparty_imports = []
            local_imports = []

            for imp in imports:
                stripped = imp.strip()
                if not stripped or stripped.startswith('#'):
                    continue

                # Simple classification - this could be enhanced
                if stripped.startswith('from .') or stripped.startswith('import .'):
                    local_imports.append(imp)
                elif any(stdlib in stripped for stdlib in ['os', 'sys', 're', 'json', 'time']):
                    stdlib_imports.append(imp)
                else:
                    thirdparty_imports.append(imp)

            # Sort each category
            stdlib_imports.sort()
            thirdparty_imports.sort()
            local_imports.sort()

            # Combine organized imports
            organized_imports = []
            if stdlib_imports:
                organized_imports.extend(stdlib_imports)
                organized_imports.append('')  # Blank line separator
            if thirdparty_imports:
                organized_imports.extend(thirdparty_imports)
                organized_imports.append('')  # Blank line separator
            if local_imports:
                organized_imports.extend(local_imports)
                organized_imports.append('')  # Blank line separator

            # Remove trailing empty line if it exists
            if organized_imports and organized_imports[-1] == '':
                organized_imports.pop()

            # Create backup and write new content
            self._backup_file(file_path)
            new_lines = organized_imports + other_lines
            new_content = '\n'.join(new_lines)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Generate diff
            diff = self._generate_diff(original_content, new_content, file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="organize_imports",
                success=True,
                modified_files=[file_path],
                affected_symbols=[],
                changes_preview={file_path: diff},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="organize_imports",
                success=False,
                modified_files=[],
                error_message=f"Failed to organize imports: {str(e)}"
            )

    def rollback_operation(self, rollback_info: str) -> Dict[str, Any]:
        """
        Rollback a previous edit operation using backup information.

        Args:
            rollback_info: Backup directory path from previous operation

        Returns:
            Dictionary containing rollback results
        """
        self._require_project_setup()

        if not rollback_info or not os.path.exists(rollback_info):
            return ResponseFormatter.edit_operation_response(
                operation_type="rollback",
                success=False,
                modified_files=[],
                error_message="Invalid or missing backup information"
            )

        try:
            restored_files = []

            # Walk through backup directory and restore files
            for root, dirs, files in os.walk(rollback_info):
                for file in files:
                    backup_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(backup_file_path, rollback_info)
                    original_file_path = os.path.join(self.base_path, relative_path)

                    # Restore the file
                    os.makedirs(os.path.dirname(original_file_path), exist_ok=True)
                    shutil.copy2(backup_file_path, original_file_path)
                    restored_files.append(original_file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="rollback",
                success=True,
                modified_files=restored_files,
                affected_symbols=[],
                error_message=f"Successfully restored {len(restored_files)} files from backup"
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="rollback",
                success=False,
                modified_files=[],
                error_message=f"Failed to rollback operation: {str(e)}"
            )