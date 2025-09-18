"""
JSON Index Builder - Clean implementation using Strategy pattern.

This replaces the monolithic parser implementation with a clean,
maintainable Strategy pattern architecture.
"""

import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .strategies import StrategyFactory
from .models import SymbolInfo, FileInfo

logger = logging.getLogger(__name__)


@dataclass
class IndexMetadata:
    """Metadata for the JSON index."""
    project_path: str
    indexed_files: int
    index_version: str
    timestamp: str
    languages: List[str]
    total_symbols: int = 0
    specialized_parsers: int = 0
    fallback_files: int = 0


class JSONIndexBuilder:
    """
    Main index builder using Strategy pattern for language parsing.

    This class orchestrates the index building process by:
    1. Discovering files in the project
    2. Using StrategyFactory to get appropriate parsers
    3. Extracting symbols and metadata
    4. Assembling the final JSON index
    """

    def __init__(self, project_path: str, additional_excludes: Optional[List[str]] = None):
        from ..utils import FileFilter

        # Input validation
        if not isinstance(project_path, str):
            raise ValueError(f"Project path must be a string, got {type(project_path)}")

        project_path = project_path.strip()
        if not project_path:
            raise ValueError("Project path cannot be empty")

        if not os.path.isdir(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        self.project_path = project_path
        self.in_memory_index: Optional[Dict[str, Any]] = None
        self.strategy_factory = StrategyFactory()
        self.file_filter = FileFilter(additional_excludes)

        logger.info(f"Initialized JSON index builder for {project_path}")
        strategy_info = self.strategy_factory.get_strategy_info()
        logger.info(f"Available parsing strategies: {len(strategy_info)} types")

        # Log specialized vs fallback coverage
        specialized = len(self.strategy_factory.get_specialized_extensions())
        fallback = len(self.strategy_factory.get_fallback_extensions())
        logger.info(f"Specialized parsers: {specialized} extensions, Fallback coverage: {fallback} extensions")

    def _process_file(self, file_path: str, specialized_extensions: set) -> Optional[Tuple[Dict, Dict, str, bool]]:
        """
        Process a single file - designed for parallel execution.

        Args:
            file_path: Path to the file to process
            specialized_extensions: Set of extensions with specialized parsers

        Returns:
            Tuple of (symbols, file_info, language, is_specialized) or None on error
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            ext = Path(file_path).suffix.lower()
            rel_path = os.path.relpath(file_path, self.project_path).replace('\\', '/')

            # Get appropriate strategy
            strategy = self.strategy_factory.get_strategy(ext)

            # Track strategy usage
            is_specialized = ext in specialized_extensions

            # Parse file using strategy
            symbols, file_info = strategy.parse_file(rel_path, content)

            logger.debug(f"Parsed {rel_path}: {len(symbols)} symbols ({file_info.language})")

            return (symbols, {rel_path: file_info}, file_info.language, is_specialized)

        except (OSError, ValueError, RuntimeError, SyntaxError) as e:
            logger.warning(f"Error processing {file_path}: {e}")
            return None

    def build_index(self, parallel: bool = True, max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        Build the complete index using Strategy pattern with parallel processing.

        Args:
            parallel: Whether to use parallel processing (default: True)
            max_workers: Maximum number of worker processes/threads (default: CPU count)

        Returns:
            Complete JSON index with metadata, symbols, and file information
        """
        logger.info(f"Building JSON index using Strategy pattern (parallel={parallel})...")
        start_time = time.time()

        # Get list of files to process
        files_to_process = self._get_supported_files()
        total_files = len(files_to_process)

        if total_files == 0:
            logger.warning("No files to process")
            return self._create_empty_index()

        logger.info(f"Processing {total_files} files...")
        
        # Process files and collect results
        all_symbols, all_files, languages, specialized_count, fallback_count = self._process_files(
            files_to_process, parallel, max_workers
        )

        # Build and return final index
        return self._build_final_index(all_symbols, all_files, languages, 
                                     specialized_count, fallback_count, start_time)

    def _process_files(self, files_to_process: List[str], parallel: bool, 
                    max_workers: Optional[int]) -> tuple[Dict[str, Any], Dict[str, Any], 
                    set[str], int, int]:
        """Process files either in parallel or sequentially.
        
        Returns:
            Tuple of (all_symbols, all_files, languages, specialized_count, fallback_count)
        """
        all_symbols = {}
        all_files = {}
        languages = set()
        specialized_count = 0
        fallback_count = 0
        
        # Get specialized extensions for tracking
        specialized_extensions = set(self.strategy_factory.get_specialized_extensions())

        if parallel and len(files_to_process) > 1:
            specialized_count, fallback_count = self._process_files_parallel(
                files_to_process, specialized_extensions, max_workers,
                all_symbols, all_files, languages
            )
        else:
            specialized_count, fallback_count = self._process_files_sequential(
                files_to_process, specialized_extensions,
                all_symbols, all_files, languages
            )

        return all_symbols, all_files, languages, specialized_count, fallback_count

    def _get_optimal_workers(self, max_workers: Optional[int], file_count: int) -> int:
        """Calculate optimal number of workers for processing."""
        if max_workers is not None:
            return max_workers
        # Use ThreadPoolExecutor for I/O-bound file reading
        return min(os.cpu_count() or 4, file_count)

    def _process_file_result(self, result: tuple, all_symbols: Dict[str, Any],
                           all_files: Dict[str, Any], languages: set[str]) -> tuple[int, int]:
        """Process a single file result and update collections.

        Returns:
            Tuple of (specialized_increment, fallback_increment)
        """
        symbols, file_info_dict, language, is_specialized = result
        all_symbols.update(symbols)
        all_files.update(file_info_dict)
        languages.add(language)

        return (1, 0) if is_specialized else (0, 1)

    def _process_files_parallel(self, files_to_process: List[str], specialized_extensions: set[str],
                               max_workers: Optional[int], all_symbols: Dict[str, Any],
                               all_files: Dict[str, Any], languages: set[str]) -> tuple[int, int]:
        """Process files in parallel using ThreadPoolExecutor."""
        max_workers = self._get_optimal_workers(max_workers, len(files_to_process))
        logger.info(f"Using parallel processing with {max_workers} workers")

        specialized_count = 0
        fallback_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_file, file_path, specialized_extensions): file_path
                for file_path in files_to_process
            }

            # Process completed tasks
            processed = 0
            for future in as_completed(future_to_file):
                result = future.result()

                if result:
                    spec_inc, fall_inc = self._process_file_result(result, all_symbols, all_files, languages)
                    specialized_count += spec_inc
                    fallback_count += fall_inc

                processed += 1
                if processed % 100 == 0:
                    logger.debug(f"Processed {processed}/{len(files_to_process)} files")

        return specialized_count, fallback_count

    def _process_files_sequential(self, files_to_process: List[str], specialized_extensions: set[str],
                                  all_symbols: Dict[str, Any], all_files: Dict[str, Any],
                                  languages: set[str]) -> tuple[int, int]:
        """Process files sequentially."""
        logger.info("Using sequential processing")

        specialized_count = 0
        fallback_count = 0

        for file_path in files_to_process:
            result = self._process_file(file_path, specialized_extensions)
            if result:
                spec_inc, fall_inc = self._process_file_result(result, all_symbols, all_files, languages)
                specialized_count += spec_inc
                fallback_count += fall_inc

        return specialized_count, fallback_count

    def _build_final_index(self, all_symbols: Dict[str, Any], all_files: Dict[str, Any],
                          languages: set[str], specialized_count: int, fallback_count: int,
                          start_time: float) -> Dict[str, Any]:
        """Build the final index structure with metadata."""
        # Build index metadata
        metadata = IndexMetadata(
            project_path=self.project_path,
            indexed_files=len(all_files),
            index_version="2.0.0-strategy",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            languages=sorted(list(languages)),
            total_symbols=len(all_symbols),
            specialized_parsers=specialized_count,
            fallback_files=fallback_count
        )

        # Assemble final index
        index = {
            "metadata": asdict(metadata),
            "symbols": {k: asdict(v) for k, v in all_symbols.items()},
            "files": {k: asdict(v) for k, v in all_files.items()}
        }

        # Cache in memory
        self.in_memory_index = index

        elapsed = time.time() - start_time
        logger.info(f"Built index with {len(all_symbols)} symbols from {len(all_files)} files in {elapsed:.2f}s")
        logger.info(f"Languages detected: {sorted(languages)}")
        logger.info(f"Strategy usage: {specialized_count} specialized, {fallback_count} fallback")

        return index

    def _create_empty_index(self) -> Dict[str, Any]:
        """Create an empty index structure."""
        metadata = IndexMetadata(
            project_path=self.project_path,
            indexed_files=0,
            index_version="2.0.0-strategy",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            languages=[],
            total_symbols=0,
            specialized_parsers=0,
            fallback_files=0
        )

        return {
            "metadata": asdict(metadata),
            "symbols": {},
            "files": {}
        }

    def get_index(self) -> Optional[Dict[str, Any]]:
        """Get the current in-memory index."""
        return self.in_memory_index

    def clear_index(self):
        """Clear the in-memory index."""
        self.in_memory_index = None
        logger.debug("Cleared in-memory index")

    def _get_supported_files(self) -> List[str]:
        """
        Get all supported files in the project using centralized filtering.

        Returns:
            List of file paths that can be parsed
        """
        supported_files = []
        base_path = Path(self.project_path)

        try:
            for root, dirs, files in os.walk(self.project_path):
                # Filter directories in-place using centralized logic
                dirs[:] = [d for d in dirs if not self.file_filter.should_exclude_directory(d)]

                # Filter files using centralized logic
                for file in files:
                    file_path = Path(root) / file
                    if self.file_filter.should_process_path(file_path, base_path):
                        supported_files.append(str(file_path))

        except (OSError, RuntimeError) as e:
            logger.error(f"Error scanning directory {self.project_path}: {e}")

        logger.debug(f"Found {len(supported_files)} supported files")
        return supported_files

    def save_index(self, index: Dict[str, Any], index_path: str) -> bool:
        """
        Save index to disk.

        Args:
            index: Index data to save
            index_path: Path where to save the index

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved index to {index_path}")
            return True
        except (OSError, ValueError, TypeError) as e:
            logger.error(f"Failed to save index to {index_path}: {e}")
            return False

    def load_index(self, index_path: str) -> Optional[Dict[str, Any]]:
        """
        Load index from disk.

        Args:
            index_path: Path to the index file

        Returns:
            Index data if successful, None otherwise
        """
        try:
            if not os.path.exists(index_path):
                logger.debug(f"Index file not found: {index_path}")
                return None

            import json
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)

            # Cache in memory
            self.in_memory_index = index
            logger.info(f"Loaded index from {index_path}")
            return index

        except (OSError, ValueError, TypeError) as e:
            logger.error(f"Failed to load index from {index_path}: {e}")
            return None

    def get_parsing_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about parsing capabilities.

        Returns:
            Dictionary with parsing statistics and strategy information
        """
        strategy_info = self.strategy_factory.get_strategy_info()

        return {
            "total_strategies": len(strategy_info),
            "specialized_languages": [lang for lang in strategy_info.keys() if not lang.startswith('fallback_')],
            "fallback_languages": [lang.replace('fallback_', '') for lang in strategy_info.keys() if lang.startswith('fallback_')],
            "total_extensions": len(self.strategy_factory.get_all_supported_extensions()),
            "specialized_extensions": len(self.strategy_factory.get_specialized_extensions()),
            "fallback_extensions": len(self.strategy_factory.get_fallback_extensions()),
            "strategy_details": strategy_info
        }

    def get_file_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get symbols for a specific file.

        Args:
            file_path: Relative path to the file

        Returns:
            List of symbols in the file
        """
        if not self.in_memory_index:
            logger.warning("Index not loaded")
            return []

        try:
            # Normalize file path
            file_path = file_path.replace('\\', '/')
            if file_path.startswith('./'):
                file_path = file_path[2:]

            # Get file info
            file_info = self.in_memory_index["files"].get(file_path)
            if not file_info:
                logger.warning(f"File not found in index: {file_path}")
                return []

            # Work directly with global symbols for this file
            global_symbols = self.in_memory_index.get("symbols", {})
            result = []

            # Find all symbols for this file directly from global symbols
            for symbol_id, symbol_data in global_symbols.items():
                symbol_file = symbol_data.get("file", "").replace("\\", "/")

                # Check if this symbol belongs to our file
                if symbol_file == file_path:
                    symbol_type = symbol_data.get("type", "unknown")
                    symbol_name = symbol_id.split("::")[-1]  # Extract symbol name from ID

                    # Create symbol info
                    symbol_info = {
                        "name": symbol_name,
                        "called_by": symbol_data.get("called_by", []),
                        "line": symbol_data.get("line"),
                        "signature": symbol_data.get("signature")
                    }

                    # Categorize by type
                    if symbol_type in ["function", "method"]:
                        result.append(symbol_info)
                    elif symbol_type == "class":
                        result.append(symbol_info)

            # Sort by line number for consistent ordering
            result.sort(key=lambda x: x.get("line", 0))

            return result

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error getting file symbols for {file_path}: {e}")
            return []
