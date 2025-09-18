"""
Basic, pure-Python search strategy.
"""
import os
import re
import fnmatch
from typing import Dict, List, Optional, Tuple

from .base import SearchStrategy, create_word_boundary_pattern, is_safe_regex_pattern

class BasicSearchStrategy(SearchStrategy):
    """
    A basic, pure-Python search strategy.

    This strategy iterates through files and lines manually. It's a fallback
    for when no advanced command-line search tools are available.
    It does not support context lines.
    """

    @property
    def name(self) -> str:
        """The name of the search tool."""
        return 'basic'

    def is_available(self) -> bool:
        """This basic strategy is always available."""
        return True


    def search(
        self,
        pattern: str,
        base_path: str,
        case_sensitive: bool = True,
        context_lines: int = 0,
        file_pattern: Optional[str] = None,
        fuzzy: bool = False,
        regex: bool = False,
        max_line_length: Optional[int] = None
    ) -> Dict[str, List[Tuple[int, str]]]:
        """
        Execute a basic, line-by-line search.

        Note: This implementation does not support context_lines.
        Args:
            pattern: The search pattern
            base_path: Directory to search in
            case_sensitive: Whether search is case sensitive
            context_lines: Number of context lines (not supported)
            file_pattern: File pattern to filter
            fuzzy: Enable word boundary matching
            regex: Enable regex pattern matching
            max_line_length: Optional. Limit the length of lines when context_lines is used
        """
        results: Dict[str, List[Tuple[int, str]]] = {}

        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            if regex:
                # Use regex mode - check for safety first
                if not is_safe_regex_pattern(pattern):
                    raise ValueError(f"Potentially unsafe regex pattern: {pattern}")
                search_regex = re.compile(pattern, flags)
            elif fuzzy:
                # Use word boundary pattern for partial matching
                search_pattern = create_word_boundary_pattern(pattern)
                search_regex = re.compile(search_pattern, flags)
            else:
                # Use literal string search
                search_regex = re.compile(re.escape(pattern), flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {pattern}, error: {e}")

        # Use centralized file walking with custom pattern matching
        from ..utils.file_walker import FileWalker
        from ..utils.file_filter import FileFilter

        # Create a basic file filter that only excludes directories, not file types
        basic_filter = FileFilter()
        walker = FileWalker(basic_filter)

        for file_path in walker.walk_all_files(base_path, file_pattern):
            rel_path = os.path.relpath(str(file_path), base_path)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if search_regex.search(line):
                            content = line.rstrip('\n')
                            # Truncate content if it exceeds max_line_length
                            if max_line_length and len(content) > max_line_length:
                                content = content[:max_line_length] + '... (truncated)'

                            if rel_path not in results:
                                results[rel_path] = []
                            # Strip newline for consistent output
                            results[rel_path].append((line_num, content))
            except (UnicodeDecodeError, PermissionError, OSError):
                # Ignore files that can't be opened or read due to encoding/permission issues
                continue
            except (OSError, ValueError, RuntimeError):
                # Ignore any other unexpected exceptions to maintain robustness
                continue

        return results