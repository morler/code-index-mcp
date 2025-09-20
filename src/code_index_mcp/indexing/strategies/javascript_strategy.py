"""
JavaScript parsing strategy using tree-sitter.
"""

import logging
from typing import Dict, List, Tuple, Optional
import tree_sitter
from tree_sitter_javascript import language
from .base_strategy import ParsingStrategy
from ..models import SymbolInfo, FileInfo

logger = logging.getLogger(__name__)


class JavaScriptParsingStrategy(ParsingStrategy):
    """JavaScript-specific parsing strategy using tree-sitter."""

    def __init__(self):
        self.js_language = tree_sitter.Language(language())

    def get_language_name(self) -> str:
        return "javascript"

    def get_supported_extensions(self) -> List[str]:
        return ['.js', '.jsx', '.mjs', '.cjs']

    def parse_file(self, file_path: str, content: str) -> Tuple[Dict[str, SymbolInfo], FileInfo]:
        """Parse JavaScript file using tree-sitter."""
        symbols: Dict[str, SymbolInfo] = {}
        functions: List[SymbolInfo] = []
        classes: List[SymbolInfo] = []
        imports: List[str] = []
        exports: List[str] = []

        parser = tree_sitter.Parser(self.js_language)
        tree = parser.parse(content.encode('utf8'))
        self._traverse_js_node(tree.root_node, content, file_path, symbols, list(symbols.keys()), [], imports, exports, [])

        file_info = FileInfo(
            language=self.get_language_name(),
            line_count=len(content.splitlines()),
            symbols={"functions": list(symbols.keys()), "classes": []},
            imports=imports,
            exports=exports
        )

        return symbols, file_info

    def _traverse_js_node(self, node, content: str, file_path: str, symbols: Dict[str, SymbolInfo],
                         functions: List[str], classes: List[str], imports: List[str], exports: List[str],
                         current_function_stack: Optional[List[str]] = None):
        """Traverse JavaScript AST node."""
        if current_function_stack is None:
            current_function_stack = []

        if node.type == 'function_declaration':
            name = self._get_function_name(node, content)
            if name:
                symbol_id = self._create_symbol_id(file_path, name)
                signature = self._get_js_function_signature(node, content)
                symbols[symbol_id] = SymbolInfo(
                    type="function",
                    file=file_path,
                    line=node.start_point[0] + 1,
                    signature=signature
                )
                functions.append(name)

                # Add to function stack for call analysis
                current_function_stack.append(symbol_id)
                # Process function body
                for child in node.children:
                    if child.type == 'statement_block':
                        self._traverse_js_node(child, content, file_path, symbols, functions, classes, imports, exports, current_function_stack)
                # Remove from stack
                current_function_stack.pop()
                return  # Skip generic traversal

        # Handle arrow functions and function expressions in lexical declarations (const/let)
        elif node.type in ['lexical_declaration', 'variable_declaration']:
            # Look for const/let/var name = arrow_function or function_expression
            for child in node.children:
                if child.type == 'variable_declarator':
                    name_node = None
                    value_node = None
                    for declarator_child in child.children:
                        if declarator_child.type == 'identifier':
                            name_node = declarator_child
                        elif declarator_child.type in ['arrow_function', 'function_expression', 'function']:
                            value_node = declarator_child

                    if name_node and value_node:
                        name = content[name_node.start_byte:name_node.end_byte]
                        symbol_id = self._create_symbol_id(file_path, name)
                        # Create signature from the declaration
                        signature = content[child.start_byte:child.end_byte].split('\n')[0].strip()
                        symbols[symbol_id] = SymbolInfo(
                            type="function",
                            file=file_path,
                            line=child.start_point[0] + 1,  # Use child position, not parent
                            signature=signature
                        )
                        functions.append(name)

        elif node.type == 'class_declaration':
            name = self._get_class_name(node, content)
            if name:
                symbol_id = self._create_symbol_id(file_path, name)
                symbols[symbol_id] = SymbolInfo(
                    type="class",
                    file=file_path,
                    line=node.start_point[0] + 1
                )
                classes.append(name)

        elif node.type == 'method_definition':
            method_name = self._get_method_name(node, content)
            class_name = self._find_parent_class(node, content)
            if method_name and class_name:
                full_name = f"{class_name}.{method_name}"
                symbol_id = self._create_symbol_id(file_path, full_name)
                signature = self._get_js_function_signature(node, content)
                symbols[symbol_id] = SymbolInfo(
                    type="method",
                    file=file_path,
                    line=node.start_point[0] + 1,
                    signature=signature
                )
                # Add method to functions list for consistency
                functions.append(full_name)

        # Handle import statements
        elif node.type == 'import_statement':
            self._handle_import_statement(node, content, imports, symbols, current_function_stack)

        # Handle export statements
        elif node.type in ['export_statement', 'export_default_declaration']:
            self._handle_export_statement(node, content, exports, symbols, current_function_stack)

        # Handle function calls
        elif node.type == 'call_expression':
            self._handle_function_call(node, content, symbols, current_function_stack)

        # Continue traversing children
        for child in node.children:
            self._traverse_js_node(child, content, file_path, symbols, functions, classes, imports, exports, current_function_stack)

    def _get_function_name(self, node, content: str) -> Optional[str]:
        """Extract function name from tree-sitter node."""
        for child in node.children:
            if child.type == 'identifier':
                return content[child.start_byte:child.end_byte]
        return None

    def _get_class_name(self, node, content: str) -> Optional[str]:
        """Extract class name from tree-sitter node."""
        for child in node.children:
            if child.type == 'identifier':
                return content[child.start_byte:child.end_byte]
        return None

    def _get_method_name(self, node, content: str) -> Optional[str]:
        """Extract method name from tree-sitter node."""
        for child in node.children:
            if child.type == 'property_identifier':
                return content[child.start_byte:child.end_byte]
        return None

    def _find_parent_class(self, node, content: str) -> Optional[str]:
        """Find the parent class of a method."""
        parent = node.parent
        while parent:
            if parent.type == 'class_declaration':
                return self._get_class_name(parent, content)
            parent = parent.parent
        return None

    def _get_js_function_signature(self, node, content: str) -> str:
        """Extract JavaScript function signature."""
        return content[node.start_byte:node.end_byte].split('\n')[0].strip()

    def _create_symbol_id(self, file_path: str, symbol_name: str) -> str:
        """Create a unique symbol ID."""
        return f"{file_path}::{symbol_name}"

    def _handle_import_statement(self, node, content: str, imports: List[str],
                                symbols: Dict[str, SymbolInfo], current_function_stack: List[str]):
        """Handle import statements and add to semantic fields."""
        # Extract imported names
        imported_names = []
        for child in node.children:
            if child.type == 'import_clause':
                for import_child in child.children:
                    if import_child.type == 'identifier':
                        imported_names.append(content[import_child.start_byte:import_child.end_byte])
                    elif import_child.type == 'named_imports':
                        for spec_child in import_child.children:
                            if spec_child.type == 'import_specifier':
                                for spec_grandchild in spec_child.children:
                                    if spec_grandchild.type == 'identifier':
                                        imported_names.append(content[spec_grandchild.start_byte:spec_grandchild.end_byte])

        # Add to global imports
        imports.extend(imported_names)

        # Add to current function's imports if in function context
        if current_function_stack and imported_names:
            current_symbol_id = current_function_stack[-1]
            if current_symbol_id in symbols:
                symbol = symbols[current_symbol_id]
                for name in imported_names:
                    if name not in symbol.imports:
                        symbol.imports.append(name)

    def _handle_export_statement(self, node, content: str, exports: List[str],
                                symbols: Dict[str, SymbolInfo], current_function_stack: List[str]):
        """Handle export statements and add to semantic fields."""
        exported_names = []

        # Handle different export patterns
        if node.type == 'export_default_declaration':
            # export default ...
            exported_names.append('default')
        else:
            # Named exports
            for child in node.children:
                if child.type == 'identifier':
                    exported_names.append(content[child.start_byte:child.end_byte])
                elif child.type == 'function_declaration':
                    name = self._get_function_name(child, content)
                    if name:
                        exported_names.append(name)

        # Add to global exports
        exports.extend(exported_names)

        # Add to current function's exports if in function context
        if current_function_stack and exported_names:
            current_symbol_id = current_function_stack[-1]
            if current_symbol_id in symbols:
                symbol = symbols[current_symbol_id]
                for name in exported_names:
                    if name not in symbol.exports:
                        symbol.exports.append(name)

    def _handle_function_call(self, node, content: str, symbols: Dict[str, SymbolInfo],
                             current_function_stack: List[str]):
        """Handle function calls and track dependencies."""
        if not current_function_stack:
            return

        # Extract called function name
        called_function = None
        for child in node.children:
            if child.type == 'identifier':
                called_function = content[child.start_byte:child.end_byte]
                break
            elif child.type == 'member_expression':
                # Handle obj.method() calls
                for member_child in child.children:
                    if member_child.type == 'property_identifier':
                        called_function = content[member_child.start_byte:member_child.end_byte]
                        break

        if called_function:
            current_symbol_id = current_function_stack[-1]
            if current_symbol_id in symbols:
                current_symbol = symbols[current_symbol_id]

                # Add to dependencies
                if called_function not in current_symbol.dependencies:
                    current_symbol.dependencies.append(called_function)

                # Find the called symbol and update its called_by list
                for symbol_id, symbol in symbols.items():
                    if symbol_id.endswith(f"::{called_function}") or symbol.type in ["function", "method"]:
                        # Check if this is the function being called
                        symbol_name = symbol_id.split("::")[-1]
                        if symbol_name == called_function or symbol_name.endswith(f".{called_function}"):
                            caller_id = current_symbol_id
                            if caller_id not in symbol.called_by:
                                symbol.called_by.append(caller_id)
