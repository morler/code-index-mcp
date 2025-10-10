"""
File information model for code indexing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class FileInfo:
    """Information about a source file."""

    path: str
    language: str
    size: int
    line_count: int
    symbols: Dict[str, List[str]]
    imports: List[str]
    last_modified: Optional[float] = None
