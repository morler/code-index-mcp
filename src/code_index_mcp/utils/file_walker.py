"""
Centralized file walking utilities for the Code Index MCP server.

This module provides unified file traversal capabilities that integrate with
the FileFilter system, eliminating duplicate walking logic across components.
"""

import os
from pathlib import Path
from typing import Iterator, Tuple, List, Optional, Callable, Any

from .file_filter import FileFilter


class FileWalker:
    """Centralized file walking with integrated filtering."""

    def __init__(self, file_filter: Optional[FileFilter] = None):
        """
        Initialize the file walker.

        Args:
            file_filter: FileFilter instance, creates default if None
        """
        self.file_filter = file_filter or FileFilter()

    def walk_files(self, project_path: str) -> Iterator[Path]:
        """
        Walk through all supported files in a project directory.

        Args:
            project_path: Root directory to walk

        Yields:
            Path objects for files that should be processed
        """
        base_path = Path(project_path)

        for root, dirs, files in os.walk(project_path):
            # Filter directories in-place to avoid descending into excluded dirs
            dirs[:] = [d for d in dirs if not self.file_filter.should_exclude_directory(d)]

            # Process files in this directory
            for file in files:
                file_path = Path(root) / file
                if not self.file_filter.should_exclude_file(file_path):
                    yield file_path

    def walk_with_callback(self, project_path: str, callback: Callable[[Path], Any]) -> List[Any]:
        """
        Walk files and apply a callback to each valid file.

        Args:
            project_path: Root directory to walk
            callback: Function to call for each valid file

        Returns:
            List of callback results for processed files
        """
        results = []
        for file_path in self.walk_files(project_path):
            result = callback(file_path)
            if result is not None:
                results.append(result)
        return results

    def walk_files_with_stats(self, project_path: str) -> Iterator[Tuple[Path, os.stat_result]]:
        """
        Walk files and yield both path and stat information.

        Args:
            project_path: Root directory to walk

        Yields:
            Tuples of (file_path, stat_result) for files that should be processed
        """
        for file_path in self.walk_files(project_path):
            try:
                stat_result = file_path.stat()
                yield file_path, stat_result
            except (OSError, FileNotFoundError):
                # Skip files that can't be stat'd (broken symlinks, permission issues)
                continue

    def find_newer_files(self, project_path: str, reference_time: float) -> List[Path]:
        """
        Find all supported files newer than a reference timestamp.

        Args:
            project_path: Root directory to search
            reference_time: Reference timestamp (from os.path.getmtime())

        Returns:
            List of file paths that are newer than reference_time
        """
        newer_files = []
        for file_path, stat_result in self.walk_files_with_stats(project_path):
            if stat_result.st_mtime > reference_time:
                newer_files.append(file_path)
        return newer_files

    def count_supported_files(self, project_path: str) -> int:
        """
        Count total number of supported files in the project.

        Args:
            project_path: Root directory to count

        Returns:
            Number of files that would be processed
        """
        count = 0
        for _ in self.walk_files(project_path):
            count += 1
        return count

    def walk_all_files(self, project_path: str, file_pattern: Optional[str] = None) -> Iterator[Path]:
        """
        Walk through ALL files in a project directory (not just supported ones).

        This is useful for search engines that need to search all text files,
        not just the ones we typically index.

        Args:
            project_path: Root directory to walk
            file_pattern: Optional glob pattern to filter files

        Yields:
            Path objects for all files matching the criteria
        """
        import fnmatch

        for root, dirs, files in os.walk(project_path):
            # Still filter directories to avoid descending into excluded dirs
            dirs[:] = [d for d in dirs if not self.file_filter.should_exclude_directory(d)]

            # Process all files in this directory
            for file in files:
                file_path = Path(root) / file

                # Skip temporary and system files even for broad searches
                if self.file_filter.is_temporary_file(file_path):
                    continue

                # Apply custom file pattern if provided
                if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                    continue

                yield file_path

    def get_file_summary(self, project_path: str) -> dict:
        """
        Get summary statistics about files in the project.

        Args:
            project_path: Root directory to analyze

        Returns:
            Dictionary with file statistics
        """
        total_files = 0
        total_size = 0
        extensions: dict[str, int] = {}

        for file_path, stat_result in self.walk_files_with_stats(project_path):
            total_files += 1
            total_size += stat_result.st_size

            ext = file_path.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "extensions": extensions,
            "filter_summary": self.file_filter.get_exclude_summary()
        }


def create_file_walker(additional_excludes: Optional[List[str]] = None) -> FileWalker:
    """
    Factory function to create a FileWalker with custom exclusions.

    Args:
        additional_excludes: Additional patterns to exclude

    Returns:
        Configured FileWalker instance
    """
    file_filter = FileFilter(additional_excludes)
    return FileWalker(file_filter)