"""
EditResult model for representing code editing operation results.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class EditResult:
    """Result of a semantic code editing operation."""

    success: bool
    modified_files: List[str]
    changes_preview: Dict[str, str]  # file_path -> diff
    rollback_info: Optional[str]
    error_message: Optional[str] = None

    # Additional metadata
    operation_type: Optional[str] = None  # rename, add_import, remove_import, etc.
    affected_symbols: Optional[List[str]] = None  # symbols that were modified
    backup_created: bool = False  # whether backup was created for rollback

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.modified_files is None:
            self.modified_files = []
        if self.changes_preview is None:
            self.changes_preview = {}
        if self.affected_symbols is None:
            self.affected_symbols = []

    def add_modified_file(self, file_path: str, diff: str = "") -> None:
        """Add a modified file to the result."""
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)
        if diff:
            self.changes_preview[file_path] = diff

    def add_affected_symbol(self, symbol_name: str) -> None:
        """Add an affected symbol to the result."""
        if symbol_name not in self.affected_symbols:
            self.affected_symbols.append(symbol_name)

    def has_changes(self) -> bool:
        """Check if any files were modified."""
        return len(self.modified_files) > 0

    def get_summary(self) -> str:
        """Get a human-readable summary of the edit operation."""
        if not self.success:
            return f"Failed: {self.error_message or 'Unknown error'}"

        if not self.has_changes():
            return "No changes made"

        file_count = len(self.modified_files)
        symbol_count = len(self.affected_symbols) if self.affected_symbols else 0

        summary = f"Modified {file_count} file(s)"
        if symbol_count > 0:
            summary += f", affected {symbol_count} symbol(s)"
        if self.operation_type:
            summary += f" ({self.operation_type})"

        return summary