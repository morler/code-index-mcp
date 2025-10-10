"""
Symbol information model for code indexing.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SymbolInfo:
    """Information about a code symbol."""

    name: str
    type: str
    file_path: str
    line: int
    column: int
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
