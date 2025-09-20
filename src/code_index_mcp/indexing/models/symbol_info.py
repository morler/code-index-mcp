"""
SymbolInfo model for representing code symbols.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SymbolInfo:
    """Information about a code symbol (function, class, method, etc.)."""

    type: str  # function, class, method, interface, etc.
    file: str  # file path where symbol is defined
    line: int  # line number where symbol starts
    signature: Optional[str] = None  # function/method signature
    docstring: Optional[str] = None  # documentation string
    called_by: Optional[List[str]] = None  # list of symbols that call this symbol

    # Semantic relationship fields
    imports: Optional[List[str]] = None      # imported symbols
    exports: Optional[List[str]] = None      # exported symbols
    references: Optional[List[str]] = None   # locations referencing this symbol
    dependencies: Optional[List[str]] = None # symbols this depends on

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.called_by is None:
            self.called_by = []
        if self.imports is None:
            self.imports = []
        if self.exports is None:
            self.exports = []
        if self.references is None:
            self.references = []
        if self.dependencies is None:
            self.dependencies = []