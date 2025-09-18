"""
TypeScript parsing strategy using tree-sitter - Optimized single-pass version.
"""

import logging
from typing import Dict, List, Tuple, Optional, Set, NamedTuple, Callable
from .base_strategy import ParsingStrategy
from ..models import SymbolInfo, FileInfo

logger = logging.getLogger(__name__)

import tree_sitter
from tree_sitter_typescript import language_typescript


class NodeHandler(NamedTuple):
    symbol_type: str
    identifier_type: str
    target_list: str  # 'functions' or 'classes'
    requires_context: bool = False


class TypeScriptParsingStrategy(ParsingStrategy):
    """TypeScript-specific parsing strategy using tree-sitter - Single Pass Optimized."""

    def __init__(self):
        self.ts_language = tree_sitter.Language(language_typescript())
        self._node_handlers = {
            'function_declaration': NodeHandler('function', 'identifier', 'functions'),
            'class_declaration': NodeHandler('class', 'type_identifier', 'classes'),
            'interface_declaration': NodeHandler('interface', 'type_identifier', 'classes'),
            'method_definition': NodeHandler('method', 'property_identifier', 'functions', requires_context=True),
        }

    def get_language_name(self) -> str:
        return "typescript"

    def get_supported_extensions(self) -> List[str]:
        return ['.ts', '.tsx']

    def parse_file(self, file_path: str, content: str) -> Tuple[Dict[str, SymbolInfo], FileInfo]:
        """Parse TypeScript file using tree-sitter with single-pass optimization."""
        symbols: Dict[str, SymbolInfo] = {}
        functions: List[SymbolInfo] = []
        classes: List[SymbolInfo] = []
        imports: List[str] = []
        exports: List[str] = []

        # Symbol lookup index for O(1) access
        symbol_lookup: Dict[str, str] = {}  # name -> symbol_id mapping

        parser = tree_sitter.Parser(self.ts_language)
        tree = parser.parse(content.encode('utf8'))

        # Single-pass traversal that handles everything
        context = TraversalContext(
            content=content,
            file_path=file_path,
            symbols=symbols,
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            symbol_lookup=symbol_lookup
        )

        self._traverse_node_single_pass(tree.root_node, context)

        file_info = FileInfo(
            language=self.get_language_name(),
            line_count=len(content.splitlines()),
            symbols={"functions": functions, "classes": classes},
            imports=imports,
            exports=exports
        )

        return symbols, file_info

    def _traverse_node_single_pass(self, node, context: 'TraversalContext',
                                  current_function: Optional[str] = None,
                                  current_class: Optional[str] = None):
        """Single-pass traversal that extracts symbols and analyzes calls."""

        if node.type in self._node_handlers:
            self._handle_symbol_declaration(node, context, current_function, current_class)
        elif node.type == 'call_expression' and current_function:
            self._handle_call_expression(node, context, current_function)
        elif node.type == 'import_statement':
            self._handle_import_statement(node, context)
        elif node.type in ['export_statement', 'export_default_declaration']:
            self._handle_export_statement(node, context)
        else:
            for child in node.children:
                self._traverse_node_single_pass(child, context, current_function=current_function,
                                               current_class=current_class)

    def _handle_symbol_declaration(self, node, context: 'TraversalContext',
                                  current_function: Optional[str], current_class: Optional[str]) -> None:
        """Unified handler for all symbol declarations."""
        handler = self._node_handlers[node.type]
        name = self._extract_name(node, context.content, handler.identifier_type)

        if not name:
            return

        if handler.requires_context and not current_class:
            return

        if handler.requires_context:
            full_name = f"{current_class}.{name}"
            symbol_id = self._create_symbol_id(context.file_path, full_name)
        else:
            full_name = name
            symbol_id = self._create_symbol_id(context.file_path, name)

        symbol_info = SymbolInfo(
            type=handler.symbol_type,
            file=context.file_path,
            line=node.start_point[0] + 1,
            signature=self._get_ts_function_signature(node, context.content) if handler.symbol_type in ['function', 'method'] else None
        )

        context.symbols[symbol_id] = symbol_info
        context.symbol_lookup[full_name] = symbol_id

        if handler.requires_context:
            context.symbol_lookup[name] = symbol_id

        if handler.target_list == 'functions':
            context.functions.append(full_name)
        elif handler.target_list == 'classes':
            context.classes.append(name)

        new_function = f"{context.file_path}::{full_name}" if handler.symbol_type in ['function', 'method'] else current_function
        new_class = name if handler.symbol_type in ['class', 'interface'] else current_class

        for child in node.children:
            self._traverse_node_single_pass(child, context, current_function=new_function, current_class=new_class)

    def _handle_call_expression(self, node, context: 'TraversalContext',
                               current_function: str) -> None:
        """Handle call expression nodes to analyze function calls."""
        called_function = self._extract_called_function(node, context)
        
        if called_function:
            self._add_function_call_relationship(called_function, context, current_function)

    def _extract_called_function(self, node, context: 'TraversalContext') -> Optional[str]:
        """Extract the function being called from a call expression node."""
        if not node.children:
            return None
            
        func_node = node.children[0]
        if func_node.type == 'identifier':
            # Direct function call
            return context.content[func_node.start_byte:func_node.end_byte]
        elif func_node.type == 'member_expression':
            # Method call (obj.method or this.method)
            for child in func_node.children:
                if child.type == 'property_identifier':
                    return context.content[child.start_byte:child.end_byte]
        
        return None

    def _add_function_call_relationship(self, called_function: str, context: 'TraversalContext',
                                       current_function: str) -> None:
        """Add relationship between caller and called function."""
        if called_function in context.symbol_lookup:
            symbol_id = context.symbol_lookup[called_function]
            symbol_info = context.symbols[symbol_id]
            if current_function not in symbol_info.called_by:
                symbol_info.called_by.append(current_function)
        else:
            # Try to find method with class prefix
            for name, sid in context.symbol_lookup.items():
                if name.endswith(f".{called_function}"):
                    symbol_info = context.symbols[sid]
                    if current_function not in symbol_info.called_by:
                        symbol_info.called_by.append(current_function)
                    break

    def _handle_import_statement(self, node, context: 'TraversalContext') -> None:
        """Handle import statement nodes."""
        import_text = context.content[node.start_byte:node.end_byte]
        context.imports.append(import_text)

    def _handle_export_statement(self, node, context: 'TraversalContext') -> None:
        """Handle export statement nodes."""
        export_text = context.content[node.start_byte:node.end_byte]
        context.exports.append(export_text)

    def _extract_name(self, node, content: str, identifier_type: str) -> Optional[str]:
        """Extract name from tree-sitter node based on identifier type."""
        for child in node.children:
            if child.type == identifier_type:
                return content[child.start_byte:child.end_byte]
        return None

    def _get_ts_function_signature(self, node, content: str) -> str:
        """Extract TypeScript function signature."""
        return content[node.start_byte:node.end_byte].split('\n')[0].strip()


class TraversalContext:
    """Context object to pass state during single-pass traversal."""

    def __init__(self, content: str, file_path: str, symbols: Dict,
                 functions: List, classes: List, imports: List, exports: List, symbol_lookup: Dict):
        self.content = content
        self.file_path = file_path
        self.symbols = symbols
        self.functions = functions
        self.classes = classes
        self.imports = imports
        self.exports = exports
        self.symbol_lookup = symbol_lookup
