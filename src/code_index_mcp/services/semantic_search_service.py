"""
Semantic search service for the Code Index MCP server.

This service provides semantic search capabilities including symbol references,
definitions, callers, implementations, and hierarchical relationships.
"""

from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from .base_service import BaseService
from ..indexing.models import SymbolInfo
from ..utils import ResponseFormatter


class SemanticSearchService(BaseService):
    """
    Service for managing semantic search operations.

    This service provides advanced semantic search capabilities:
    - Find symbol references across the project
    - Find symbol definitions
    - Find callers of functions/methods
    - Find implementations of interfaces/classes
    - Find symbol hierarchical relationships
    """

    def find_references(self, symbol_name: str) -> Dict[str, Any]:
        """
        Find all references to a symbol across the project.

        Args:
            symbol_name: Name of the symbol to find references for

        Returns:
            Dictionary containing reference locations and metadata

        Raises:
            ValueError: If project is not set up or symbol_name is invalid
        """
        self._require_project_setup()

        if not symbol_name or not symbol_name.strip():
            raise ValueError("Symbol name cannot be empty")

        symbol_name = symbol_name.strip()

        # Use the index manager's find_symbol_references method
        if not self.index_manager:
            raise ValueError("Index manager not available")

        try:
            references = self.index_manager.find_symbol_references(symbol_name)

            # Format the results
            formatted_references = []
            for ref in references:
                formatted_references.append({
                    "file": ref.get("file", "unknown"),
                    "line": ref.get("line", 0),
                    "symbol_name": symbol_name,
                    "context_symbol": ref.get("type", "unknown"),
                    "signature": ref.get("signature", "")
                })

            return ResponseFormatter.semantic_search_response(
                query=symbol_name,
                results=formatted_references,
                search_type="references"
            )
        except Exception as e:
            raise ValueError(f"Failed to find references: {e}") from e

    def find_definition(self, symbol_name: str) -> Dict[str, Any]:
        """
        Find the definition of a symbol.

        Args:
            symbol_name: Name of the symbol to find definition for

        Returns:
            Dictionary containing definition location and metadata

        Raises:
            ValueError: If project is not set up or symbol_name is invalid
        """
        self._require_project_setup()

        if not symbol_name or not symbol_name.strip():
            raise ValueError("Symbol name cannot be empty")

        symbol_name = symbol_name.strip()

        if not self.index_manager:
            raise ValueError("Index manager not available")

        try:
            # Use the index manager's search_symbols method
            symbols = self.index_manager.search_symbols(symbol_name)

            definitions = []
            for symbol in symbols:
                # Look for exact matches
                symbol_id = symbol.get("id", "")
                if symbol_name in symbol_id:
                    definitions.append({
                        "file": symbol.get("file", "unknown"),
                        "line": symbol.get("line", 0),
                        "symbol_name": symbol_name,
                        "symbol_type": symbol.get("type", "unknown"),
                        "signature": symbol.get("signature", ""),
                        "docstring": symbol.get("docstring", "")
                    })

            return ResponseFormatter.semantic_search_response(
                query=symbol_name,
                results=definitions,
                search_type="definition"
            )
        except Exception as e:
            raise ValueError(f"Failed to find definition: {e}") from e

    def find_callers(self, function_name: str) -> Dict[str, Any]:
        """
        Find all symbols that call a specific function.

        Args:
            function_name: Name of the function to find callers for

        Returns:
            Dictionary containing caller locations and metadata

        Raises:
            ValueError: If project is not set up or function_name is invalid
        """
        self._require_project_setup()

        if not function_name or not function_name.strip():
            raise ValueError("Function name cannot be empty")

        function_name = function_name.strip()

        if not self.index_manager:
            raise ValueError("Index manager not available")

        try:
            # Use the index manager's get_symbol_callers method
            caller_names = self.index_manager.get_symbol_callers(function_name)

            callers = []
            for caller_name in caller_names:
                # Search for the caller symbol to get its details
                caller_symbols = self.index_manager.search_symbols(caller_name)
                for caller_symbol in caller_symbols:
                    callers.append({
                        "file": caller_symbol.get("file", "unknown"),
                        "line": caller_symbol.get("line", 0),
                        "caller_name": caller_name,
                        "caller_type": caller_symbol.get("type", "unknown"),
                        "signature": caller_symbol.get("signature", "")
                    })

            return ResponseFormatter.semantic_search_response(
                query=function_name,
                results=callers,
                search_type="callers"
            )
        except Exception as e:
            raise ValueError(f"Failed to find callers: {e}") from e

    def find_implementations(self, interface_name: str) -> Dict[str, Any]:
        """
        Find all implementations of an interface or base class.

        Args:
            interface_name: Name of the interface/base class

        Returns:
            Dictionary containing implementation locations and metadata

        Raises:
            ValueError: If project is not set up or interface_name is invalid
        """
        self._require_project_setup()

        if not interface_name or not interface_name.strip():
            raise ValueError("Interface name cannot be empty")

        interface_name = interface_name.strip()

        if not self.index_manager:
            raise ValueError("Index manager not available")

        try:
            # Search for classes that might implement this interface
            class_symbols = self.index_manager.search_symbols("", symbol_type="class")

            implementations = []
            for symbol in class_symbols:
                # Check if this class might implement the interface
                # This is a simplified implementation - in practice we'd need
                # semantic analysis to determine inheritance relationships
                signature = symbol.get("signature", "")
                if interface_name in signature:
                    implementations.append({
                        "file": symbol.get("file", "unknown"),
                        "line": symbol.get("line", 0),
                        "implementation_name": symbol.get("id", "").split(":")[-1],
                        "implementation_type": symbol.get("type", "class"),
                        "signature": signature
                    })

            return ResponseFormatter.semantic_search_response(
                query=interface_name,
                results=implementations,
                search_type="implementations"
            )
        except Exception as e:
            raise ValueError(f"Failed to find implementations: {e}") from e

    def find_symbol_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """
        Find the inheritance hierarchy of a class.

        Args:
            class_name: Name of the class to analyze

        Returns:
            Dictionary containing hierarchical structure

        Raises:
            ValueError: If project is not set up or class_name is invalid
        """
        self._require_project_setup()

        if not class_name or not class_name.strip():
            raise ValueError("Class name cannot be empty")

        class_name = class_name.strip()

        if not self.index_manager:
            raise ValueError("Index manager not available")

        try:
            hierarchy = {
                "root_class": class_name,
                "parents": [],
                "children": [],
                "related_classes": []
            }

            # Find the target class definition
            target_symbols = self.index_manager.search_symbols(class_name, symbol_type="class")

            if not target_symbols:
                return ResponseFormatter.semantic_search_response(
                    query=class_name,
                    results=hierarchy,
                    search_type="hierarchy",
                    message=f"Class '{class_name}' not found"
                )

            # For now, we'll provide a simplified hierarchy view
            # that shows related classes based on signature analysis
            all_classes = self.index_manager.search_symbols("", symbol_type="class")

            for symbol in all_classes:
                signature = symbol.get("signature", "")
                symbol_name = symbol.get("id", "").split(":")[-1]

                # Look for inheritance patterns in signatures
                if symbol_name != class_name and class_name in signature:
                    class_info = {
                        "name": symbol_name,
                        "file": symbol.get("file", "unknown"),
                        "line": symbol.get("line", 0),
                        "signature": signature
                    }
                    hierarchy["related_classes"].append(class_info)

            return ResponseFormatter.semantic_search_response(
                query=class_name,
                results=hierarchy,
                search_type="hierarchy"
            )
        except Exception as e:
            raise ValueError(f"Failed to find symbol hierarchy: {e}") from e

