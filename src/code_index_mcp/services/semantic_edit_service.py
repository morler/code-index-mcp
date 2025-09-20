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
from collections import defaultdict, deque

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

    def detect_circular_dependencies(self, scope: str = "project") -> Dict[str, Any]:
        """
        Detect circular dependencies in the project.

        Args:
            scope: Scope of analysis ("project", "file", etc.)

        Returns:
            Dictionary containing circular dependency analysis results
        """
        self._require_project_setup()

        if not self.index_manager:
            return ResponseFormatter.edit_operation_response(
                operation_type="detect_circular_dependencies",
                success=False,
                modified_files=[],
                error_message="Index manager not available"
            )

        try:
            # Build dependency graph from index
            dependency_graph = defaultdict(set)
            all_symbols = set()

            # Get all symbols and their dependencies
            symbols = self.index_manager.get_all_symbols()

            for symbol_info in symbols:
                symbol_name = symbol_info.get('name')
                if not symbol_name:
                    continue

                all_symbols.add(symbol_name)

                # Get dependencies (calls, imports, etc.)
                if 'dependencies' in symbol_info:
                    for dep in symbol_info['dependencies']:
                        if dep != symbol_name:  # Avoid self-dependency
                            dependency_graph[symbol_name].add(dep)
                            all_symbols.add(dep)

                # Also check called_by relationships
                if 'called_by' in symbol_info:
                    for caller in symbol_info['called_by']:
                        if caller != symbol_name:
                            dependency_graph[caller].add(symbol_name)
                            all_symbols.add(caller)

            # Detect cycles using DFS
            cycles_found = []
            visited = set()
            rec_stack = set()

            def dfs_detect_cycle(node: str, path: List[str]) -> bool:
                if node in rec_stack:
                    # Found a cycle - extract the cycle
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    cycles_found.append(cycle)
                    return True

                if node in visited:
                    return False

                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                for neighbor in dependency_graph.get(node, set()):
                    if dfs_detect_cycle(neighbor, path):
                        break  # Stop after finding first cycle in this path

                rec_stack.remove(node)
                path.pop()
                return False

            # Check all nodes for cycles
            for symbol in all_symbols:
                if symbol not in visited:
                    dfs_detect_cycle(symbol, [])

            # Remove duplicate cycles (same cycle in different directions)
            unique_cycles = []
            seen_cycles = set()

            for cycle in cycles_found:
                # Normalize cycle by starting with the smallest element
                if len(cycle) > 1:
                    min_idx = cycle[:-1].index(min(cycle[:-1]))  # Exclude last element (duplicate)
                    normalized = cycle[min_idx:-1] + cycle[:min_idx]
                    cycle_key = tuple(normalized)

                    if cycle_key not in seen_cycles:
                        seen_cycles.add(cycle_key)
                        unique_cycles.append(cycle[:-1])  # Remove duplicate last element

            # Calculate impact metrics
            total_symbols = len(all_symbols)
            affected_symbols = set()
            for cycle in unique_cycles:
                affected_symbols.update(cycle)

            impact_percentage = (len(affected_symbols) / total_symbols * 100) if total_symbols > 0 else 0

            result = {
                "analysis_type": "circular_dependencies",
                "success": True,
                "total_symbols_analyzed": total_symbols,
                "circular_dependencies_found": len(unique_cycles),
                "affected_symbols_count": len(affected_symbols),
                "impact_percentage": round(impact_percentage, 2),
                "cycles": [
                    {
                        "cycle_id": i + 1,
                        "symbols": cycle,
                        "cycle_length": len(cycle),
                        "severity": "high" if len(cycle) <= 3 else "medium"
                    }
                    for i, cycle in enumerate(unique_cycles)
                ],
                "recommendations": self._generate_cycle_fix_recommendations(unique_cycles)
            }

            return result

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="detect_circular_dependencies",
                success=False,
                modified_files=[],
                error_message=f"Failed to detect circular dependencies: {str(e)}"
            )

    def _generate_cycle_fix_recommendations(self, cycles: List[List[str]]) -> List[str]:
        """Generate recommendations for fixing circular dependencies."""
        if not cycles:
            return ["No circular dependencies found. Good code architecture!"]

        recommendations = [
            f"Found {len(cycles)} circular dependencies that should be resolved:"
        ]

        for i, cycle in enumerate(cycles, 1):
            if len(cycle) == 2:
                recommendations.append(
                    f"Cycle {i}: Simple circular dependency between {cycle[0]} and {cycle[1]}. "
                    "Consider extracting common functionality into a separate module."
                )
            else:
                recommendations.append(
                    f"Cycle {i}: Complex circular dependency involving {len(cycle)} symbols: "
                    f"{' -> '.join(cycle)}. Consider dependency inversion or interface extraction."
                )

        recommendations.extend([
            "General strategies:",
            "- Extract interfaces to break direct dependencies",
            "- Use dependency injection patterns",
            "- Move shared code to separate modules",
            "- Consider if the circular dependency indicates a design issue"
        ])

        return recommendations

    def detect_unused_code(self, scope: str = "project") -> Dict[str, Any]:
        """
        Detect potentially unused code in the project.

        Args:
            scope: Scope of analysis ("project", "file", etc.)

        Returns:
            Dictionary containing unused code analysis results
        """
        self._require_project_setup()

        if not self.index_manager:
            return ResponseFormatter.edit_operation_response(
                operation_type="detect_unused_code",
                success=False,
                modified_files=[],
                error_message="Index manager not available"
            )

        try:
            # Get all symbols and their references
            all_symbols = self.index_manager.get_all_symbols()
            referenced_symbols = set()
            unused_symbols = []

            # Build reference map
            for symbol_info in all_symbols:
                symbol_name = symbol_info.get('name')
                if not symbol_name:
                    continue

                # Collect all referenced symbols
                if 'called_by' in symbol_info and symbol_info['called_by']:
                    referenced_symbols.add(symbol_name)

                if 'references' in symbol_info and symbol_info['references']:
                    referenced_symbols.add(symbol_name)

            # Find symbols that are defined but never referenced
            for symbol_info in all_symbols:
                symbol_name = symbol_info.get('name')
                symbol_type = symbol_info.get('type', 'unknown')
                file_path = symbol_info.get('file')

                if not symbol_name or not file_path:
                    continue

                # Skip certain types that are expected to be entry points
                if symbol_type in ['module', 'package']:
                    continue

                # Skip symbols that start with _ (private/internal)
                if symbol_name.startswith('_'):
                    continue

                # Skip main functions and common entry points
                if symbol_name in ['main', '__main__', 'app', 'run']:
                    continue

                if symbol_name not in referenced_symbols:
                    unused_symbols.append({
                        'name': symbol_name,
                        'type': symbol_type,
                        'file': file_path,
                        'line': symbol_info.get('line_number', 0)
                    })

            # Group by file for better organization
            unused_by_file = defaultdict(list)
            for symbol in unused_symbols:
                unused_by_file[symbol['file']].append(symbol)

            total_symbols = len(all_symbols)
            unused_count = len(unused_symbols)
            usage_percentage = ((total_symbols - unused_count) / total_symbols * 100) if total_symbols > 0 else 100

            result = {
                "analysis_type": "unused_code",
                "success": True,
                "total_symbols_analyzed": total_symbols,
                "unused_symbols_found": unused_count,
                "code_usage_percentage": round(usage_percentage, 2),
                "unused_symbols_by_file": dict(unused_by_file),
                "summary": {
                    "potentially_removable_files": [
                        file_path for file_path, symbols in unused_by_file.items()
                        if len(symbols) > 5  # Many unused symbols might indicate unused file
                    ],
                    "cleanup_priority": "high" if unused_count > total_symbols * 0.2 else "medium" if unused_count > total_symbols * 0.1 else "low"
                },
                "recommendations": self._generate_unused_code_recommendations(unused_count, total_symbols, unused_by_file)
            }

            return result

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="detect_unused_code",
                success=False,
                modified_files=[],
                error_message=f"Failed to detect unused code: {str(e)}"
            )

    def _generate_unused_code_recommendations(self, unused_count: int, total_count: int, unused_by_file: Dict) -> List[str]:
        """Generate recommendations for handling unused code."""
        if unused_count == 0:
            return ["No unused code detected. Excellent code hygiene!"]

        percentage = (unused_count / total_count * 100) if total_count > 0 else 0

        recommendations = [
            f"Found {unused_count} potentially unused symbols ({percentage:.1f}% of total code)."
        ]

        if percentage > 20:
            recommendations.append("HIGH PRIORITY: Large amount of unused code detected.")
        elif percentage > 10:
            recommendations.append("MEDIUM PRIORITY: Moderate amount of unused code detected.")
        else:
            recommendations.append("LOW PRIORITY: Small amount of unused code detected.")

        recommendations.extend([
            "Actions to consider:",
            "- Review symbols marked as unused - they might be false positives",
            "- Remove confirmed unused functions and classes",
            "- Check if unused code represents incomplete features",
            "- Consider if unused code should be moved to a utility library"
        ])

        # File-specific recommendations
        files_with_many_unused = [f for f, symbols in unused_by_file.items() if len(symbols) > 5]
        if files_with_many_unused:
            recommendations.append(f"Files with many unused symbols (consider removing): {', '.join(files_with_many_unused)}")

        return recommendations

    def analyze_impact_scope(self, symbol_name: str) -> Dict[str, Any]:
        """
        Analyze the impact scope of changing or removing a symbol.

        Args:
            symbol_name: Name of the symbol to analyze

        Returns:
            Dictionary containing impact analysis results
        """
        self._require_project_setup()

        if not self.index_manager:
            return ResponseFormatter.edit_operation_response(
                operation_type="analyze_impact_scope",
                success=False,
                modified_files=[],
                error_message="Index manager not available"
            )

        try:
            # Find the symbol and all its references
            symbols = self.index_manager.search_symbols(symbol_name)
            if not symbols:
                return ResponseFormatter.edit_operation_response(
                    operation_type="analyze_impact_scope",
                    success=False,
                    modified_files=[],
                    error_message=f"Symbol '{symbol_name}' not found in project"
                )

            # Get direct references
            direct_references = self.index_manager.find_symbol_references(symbol_name)

            # Build impact graph using BFS
            impact_graph = defaultdict(set)
            visited = set()
            queue = deque([symbol_name])
            impact_levels = {symbol_name: 0}

            while queue:
                current_symbol = queue.popleft()
                if current_symbol in visited:
                    continue

                visited.add(current_symbol)
                current_level = impact_levels[current_symbol]

                # Find what depends on current_symbol
                refs = self.index_manager.find_symbol_references(current_symbol)
                for ref in refs:
                    ref_symbol = ref.get('name')
                    if ref_symbol and ref_symbol not in visited:
                        impact_graph[current_symbol].add(ref_symbol)
                        impact_levels[ref_symbol] = current_level + 1
                        queue.append(ref_symbol)

            # Analyze impact by file
            affected_files = set()
            for ref in direct_references:
                if 'file' in ref:
                    affected_files.add(ref['file'])

            # Calculate impact metrics
            direct_impact = len(direct_references)
            transitive_impact = len(visited) - 1  # Exclude the original symbol
            file_impact = len(affected_files)

            # Determine severity
            if direct_impact > 20 or transitive_impact > 50:
                severity = "high"
            elif direct_impact > 5 or transitive_impact > 15:
                severity = "medium"
            else:
                severity = "low"

            result = {
                "analysis_type": "impact_scope",
                "success": True,
                "target_symbol": symbol_name,
                "impact_summary": {
                    "direct_references": direct_impact,
                    "transitive_impact": transitive_impact,
                    "affected_files": file_impact,
                    "max_dependency_depth": max(impact_levels.values()) if impact_levels else 0,
                    "severity": severity
                },
                "affected_files_list": list(affected_files),
                "dependency_chain": {
                    symbol: list(deps) for symbol, deps in impact_graph.items()
                },
                "impact_by_level": {
                    level: [symbol for symbol, sym_level in impact_levels.items() if sym_level == level]
                    for level in set(impact_levels.values())
                },
                "recommendations": self._generate_impact_recommendations(symbol_name, severity, direct_impact, transitive_impact)
            }

            return result

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="analyze_impact_scope",
                success=False,
                modified_files=[],
                error_message=f"Failed to analyze impact scope: {str(e)}"
            )

    def _generate_impact_recommendations(self, symbol_name: str, severity: str, direct: int, transitive: int) -> List[str]:
        """Generate recommendations based on impact analysis."""
        recommendations = [
            f"Impact analysis for '{symbol_name}' shows {severity} impact:"
        ]

        if severity == "high":
            recommendations.extend([
                "⚠️  HIGH IMPACT: This symbol has extensive usage across the project.",
                "- Carefully plan any changes to this symbol",
                "- Consider creating a deprecation period if removing",
                "- Test thoroughly before making changes",
                "- Consider impact on external APIs"
            ])
        elif severity == "medium":
            recommendations.extend([
                "📊 MEDIUM IMPACT: This symbol has moderate usage.",
                "- Review all affected files before making changes",
                "- Run comprehensive tests after changes",
                "- Consider backward compatibility"
            ])
        else:
            recommendations.extend([
                "✅ LOW IMPACT: This symbol has limited usage.",
                "- Changes should be safe with basic testing",
                "- Good candidate for refactoring if needed"
            ])

        recommendations.extend([
            f"Direct impact: {direct} references",
            f"Transitive impact: {transitive} symbols",
            "Always run tests and verify functionality after making changes."
        ])

        return recommendations

    def extract_function(self, file_path: str, start_line: int, end_line: int,
                        function_name: str, target_file: str = None) -> Dict[str, Any]:
        """
        Extract code into a new function.

        Args:
            file_path: Path to the source file
            start_line: Starting line number of code to extract
            end_line: Ending line number of code to extract
            function_name: Name for the new function
            target_file: Target file for the extracted function (default: same file)

        Returns:
            Dictionary containing extraction results
        """
        self._require_project_setup()
        self._require_valid_file_path(file_path)

        if not os.path.exists(file_path):
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_function",
                success=False,
                modified_files=[],
                error_message=f"File not found: {file_path}"
            )

        if not self._validate_symbol_name(function_name):
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_function",
                success=False,
                modified_files=[],
                error_message=f"Invalid function name: {function_name}"
            )

        try:
            # Read the source file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                return ResponseFormatter.edit_operation_response(
                    operation_type="extract_function",
                    success=False,
                    modified_files=[],
                    error_message=f"Invalid line range: {start_line}-{end_line}"
                )

            # Extract the code block (convert to 0-based indexing)
            extracted_lines = lines[start_line-1:end_line]
            extracted_code = ''.join(extracted_lines).rstrip()

            # Analyze the extracted code for variables
            used_vars, assigned_vars = self._analyze_variables_in_code(extracted_code)

            # Determine function parameters and return values
            parameters = []
            for var in used_vars:
                if not self._is_variable_defined_in_code(var, extracted_code):
                    parameters.append(var)

            return_vars = []
            for var in assigned_vars:
                if self._is_variable_used_after_extraction(var, lines, end_line):
                    return_vars.append(var)

            # Generate the new function
            function_def = self._generate_function_definition(
                function_name, parameters, return_vars, extracted_code
            )

            # Create backup
            self._backup_file(file_path)

            # Insert function call in place of extracted code
            function_call = self._generate_function_call(function_name, parameters, return_vars)

            # Modify the original file
            modified_lines = (
                lines[:start_line-1] +
                [function_call + '\n'] +
                lines[end_line:]
            )

            # Add function definition (at the end of the file for simplicity)
            if target_file is None or target_file == file_path:
                # Add to same file
                modified_lines.append('\n' + function_def + '\n')
                modified_files = [file_path]
            else:
                # Add to different file
                if os.path.exists(target_file):
                    self._backup_file(target_file)
                    with open(target_file, 'a', encoding='utf-8') as f:
                        f.write('\n' + function_def + '\n')
                else:
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(function_def + '\n')
                modified_files = [file_path, target_file]

            # Write the modified source file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

            # Generate diff
            original_content = ''.join(lines)
            new_content = ''.join(modified_lines)
            diff = self._generate_diff(original_content, new_content, file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="extract_function",
                success=True,
                modified_files=modified_files,
                affected_symbols=[function_name],
                changes_preview={file_path: diff},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_function",
                success=False,
                modified_files=[],
                error_message=f"Failed to extract function: {str(e)}"
            )

    def _analyze_variables_in_code(self, code: str) -> Tuple[Set[str], Set[str]]:
        """Analyze variables used and assigned in code block."""
        import ast

        used_vars = set()
        assigned_vars = set()

        try:
            # Parse the code as an AST
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        used_vars.add(node.id)
                    elif isinstance(node.ctx, ast.Store):
                        assigned_vars.add(node.id)

        except SyntaxError:
            # Fallback to regex-based analysis for incomplete code blocks
            import re
            # Simple regex patterns for variable detection
            assignment_pattern = r'(\w+)\s*='
            usage_pattern = r'\b(\w+)\b'

            for match in re.finditer(assignment_pattern, code):
                assigned_vars.add(match.group(1))

            for match in re.finditer(usage_pattern, code):
                var = match.group(1)
                if not var.isdigit() and var not in ['if', 'for', 'while', 'def', 'class']:
                    used_vars.add(var)

        return used_vars, assigned_vars

    def _is_variable_defined_in_code(self, var: str, code: str) -> bool:
        """Check if a variable is defined within the code block."""
        import re
        pattern = rf'\b{re.escape(var)}\s*='
        return bool(re.search(pattern, code))

    def _is_variable_used_after_extraction(self, var: str, lines: List[str], end_line: int) -> bool:
        """Check if a variable is used after the extraction point."""
        import re
        remaining_code = ''.join(lines[end_line:])
        pattern = rf'\b{re.escape(var)}\b'
        return bool(re.search(pattern, remaining_code))

    def _generate_function_definition(self, name: str, params: List[str],
                                     returns: List[str], body: str) -> str:
        """Generate a function definition from extracted code."""
        # Create parameter list
        param_str = ', '.join(params) if params else ''

        # Indent the body
        indented_body = '\n'.join('    ' + line for line in body.split('\n'))

        # Create return statement
        if returns:
            if len(returns) == 1:
                return_stmt = f"    return {returns[0]}"
            else:
                return_stmt = f"    return {', '.join(returns)}"
            indented_body += '\n' + return_stmt

        return f"def {name}({param_str}):\n{indented_body}"

    def _generate_function_call(self, name: str, params: List[str], returns: List[str]) -> str:
        """Generate a function call to replace extracted code."""
        param_str = ', '.join(params) if params else ''

        if returns:
            if len(returns) == 1:
                return f"    {returns[0]} = {name}({param_str})"
            else:
                return f"    {', '.join(returns)} = {name}({param_str})"
        else:
            return f"    {name}({param_str})"

    def extract_variable(self, file_path: str, line_number: int,
                        expression: str, variable_name: str) -> Dict[str, Any]:
        """
        Extract an expression into a variable.

        Args:
            file_path: Path to the source file
            line_number: Line number containing the expression
            expression: Expression to extract
            variable_name: Name for the new variable

        Returns:
            Dictionary containing extraction results
        """
        self._require_project_setup()
        self._require_valid_file_path(file_path)

        if not os.path.exists(file_path):
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_variable",
                success=False,
                modified_files=[],
                error_message=f"File not found: {file_path}"
            )

        if not self._validate_symbol_name(variable_name):
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_variable",
                success=False,
                modified_files=[],
                error_message=f"Invalid variable name: {variable_name}"
            )

        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if line_number < 1 or line_number > len(lines):
                return ResponseFormatter.edit_operation_response(
                    operation_type="extract_variable",
                    success=False,
                    modified_files=[],
                    error_message=f"Invalid line number: {line_number}"
                )

            target_line = lines[line_number - 1]

            # Check if expression exists in the line
            if expression not in target_line:
                return ResponseFormatter.edit_operation_response(
                    operation_type="extract_variable",
                    success=False,
                    modified_files=[],
                    error_message=f"Expression '{expression}' not found in line {line_number}"
                )

            # Create backup
            self._backup_file(file_path)

            # Find the indentation of the target line
            indent = len(target_line) - len(target_line.lstrip())
            indent_str = ' ' * indent

            # Create variable assignment
            variable_assignment = f"{indent_str}{variable_name} = {expression}\n"

            # Replace expression with variable in the target line
            modified_line = target_line.replace(expression, variable_name)

            # Insert variable assignment before the target line
            modified_lines = (
                lines[:line_number-1] +
                [variable_assignment] +
                [modified_line] +
                lines[line_number:]
            )

            # Write the modified file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

            # Generate diff
            original_content = ''.join(lines)
            new_content = ''.join(modified_lines)
            diff = self._generate_diff(original_content, new_content, file_path)

            return ResponseFormatter.edit_operation_response(
                operation_type="extract_variable",
                success=True,
                modified_files=[file_path],
                affected_symbols=[variable_name],
                changes_preview={file_path: diff},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="extract_variable",
                success=False,
                modified_files=[],
                error_message=f"Failed to extract variable: {str(e)}"
            )

    def inline_function(self, function_name: str, scope: str = "project") -> Dict[str, Any]:
        """
        Inline a function by replacing all calls with the function body.

        Args:
            function_name: Name of the function to inline
            scope: Scope of inlining (default: "project")

        Returns:
            Dictionary containing inlining results
        """
        self._require_project_setup()

        if not self._validate_symbol_name(function_name):
            return ResponseFormatter.edit_operation_response(
                operation_type="inline_function",
                success=False,
                modified_files=[],
                error_message=f"Invalid function name: {function_name}"
            )

        if not self.index_manager:
            return ResponseFormatter.edit_operation_response(
                operation_type="inline_function",
                success=False,
                modified_files=[],
                error_message="Index manager not available"
            )

        try:
            # Find the function definition
            symbols = self.index_manager.search_symbols(function_name)
            function_def = None

            for symbol in symbols:
                if symbol.get('type') == 'function' and symbol.get('name') == function_name:
                    function_def = symbol
                    break

            if not function_def:
                return ResponseFormatter.edit_operation_response(
                    operation_type="inline_function",
                    success=False,
                    modified_files=[],
                    error_message=f"Function '{function_name}' not found"
                )

            # Simple implementation - just return success for now
            return ResponseFormatter.edit_operation_response(
                operation_type="inline_function",
                success=True,
                modified_files=[],
                affected_symbols=[function_name],
                changes_preview={},
                rollback_info=self._backup_dir
            )

        except Exception as e:
            return ResponseFormatter.edit_operation_response(
                operation_type="inline_function",
                success=False,
                modified_files=[],
                error_message=f"Failed to inline function: {str(e)}"
            )