"""
Rust parsing strategy using regex patterns.
"""

import re
from typing import Dict, List, Tuple, Optional, NamedTuple, Callable
from .base_strategy import ParsingStrategy
from ..models import SymbolInfo, FileInfo


class PatternHandler(NamedTuple):
    pattern: str
    symbol_type: str
    target_list: str  # 'functions' or 'classes'


class RustParsingStrategy(ParsingStrategy):
    """Rust-specific parsing strategy using regex patterns."""

    def __init__(self):
        super().__init__()
        self._symbol_patterns = {
            'fn': PatternHandler(r'fn\s+(\w+)\s*\(', 'function', 'functions'),
            'struct': PatternHandler(r'struct\s+(\w+)', 'struct', 'classes'),
            'enum': PatternHandler(r'enum\s+(\w+)', 'enum', 'classes'),
            'trait': PatternHandler(r'trait\s+(\w+)', 'trait', 'classes'),
            'const': PatternHandler(r'const\s+(\w+)', 'const', ''),
            'static': PatternHandler(r'static\s+(\w+)', 'static', ''),
        }

    def get_language_name(self) -> str:
        return "rust"

    def get_supported_extensions(self) -> List[str]:
        return ['.rs']

    def parse_file(self, file_path: str, content: str) -> Tuple[Dict[str, SymbolInfo], FileInfo]:
        """Parse Rust file using regex patterns."""
        symbols = {}
        functions = []
        classes = []
        imports = []
        package = None
        lines = content.splitlines()

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue

            if line.startswith('mod '):
                package = self._extract_name(r'mod\s+(\w+)', line) or package
            elif line.startswith('use '):
                use_import = self._extract_name(r'use\s+([^;]+)', line)
                if use_import:
                    imports.append(use_import.strip())
            elif line.startswith('impl '):
                impl_type = self._extract_name(r'impl\s+(\w+)', line)
                if impl_type:
                    self._parse_impl_block(lines, i + 1, file_path, symbols, functions, impl_type)
            else:
                self._parse_symbol_line(line, i, file_path, symbols, functions, classes)

        self._analyze_rust_calls(content, symbols, file_path)

        return symbols, FileInfo(
            language=self.get_language_name(),
            line_count=len(lines),
            symbols={"functions": functions, "classes": classes},
            imports=imports,
            package=package
        )

    def _extract_name(self, pattern: str, line: str) -> Optional[str]:
        """Extract name using regex pattern."""
        match = re.search(pattern, line)
        return match.group(1) if match else None

    def _parse_symbol_line(self, line: str, line_index: int, file_path: str,
                          symbols: Dict[str, SymbolInfo], functions: List[str], classes: List[str]) -> None:
        """Parse line for symbol declarations using pattern matching."""
        for keyword, handler in self._symbol_patterns.items():
            if re.match(handler.pattern.replace(r'\s+(\w+)', r'\s+\w+'), line):
                name = self._extract_name(handler.pattern, line)
                if name:
                    symbol_id = self._create_symbol_id(file_path, name)
                    symbols[symbol_id] = SymbolInfo(
                        type=handler.symbol_type,
                        file=file_path,
                        line=line_index + 1,
                        signature=line if handler.symbol_type == 'function' else None
                    )
                    if handler.target_list == 'functions':
                        functions.append(name)
                    elif handler.target_list == 'classes':
                        classes.append(name)
                break

    def _parse_impl_block(self, lines: List[str], start_line: int, file_path: str,
                         symbols: Dict[str, SymbolInfo], functions: List[str], impl_type: str):
        """Parse methods within an impl block."""
        for idx in range(start_line, len(lines)):
            line = lines[idx].strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue

            # End of impl block
            if line == '}':
                break

            # Method declarations within impl
            if re.match(r'fn\s+\w+', line):
                func_match = re.match(r'fn\s+(\w+)\s*\(', line)
                if func_match:
                    method_name = func_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, f"{impl_type}::{method_name}")
                    symbols[symbol_id] = SymbolInfo(
                        type="method",
                        file=file_path,
                        line=idx + 1,
                        signature=line
                    )
                    functions.append(f"{impl_type}::{method_name}")

    def _analyze_rust_calls(self, content: str, symbols: Dict[str, SymbolInfo], file_path: str):
        """Analyze Rust function calls for relationships."""
        lines = content.splitlines()
        current_function = None
        is_function_declaration_line = False

        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue

            # Track current function context
            if re.match(r'fn\s+\w+', line):
                func_name = self._extract_rust_function_name(line)
                if func_name:
                    current_function = self._create_symbol_id(file_path, func_name)
                    is_function_declaration_line = True
            else:
                is_function_declaration_line = False

            # Find function calls: functionName() or obj.methodName()
            # Skip the function declaration line itself to avoid false self-calls
            if current_function and not is_function_declaration_line and ('(' in line and ')' in line):
                called_functions = self._extract_rust_called_functions(line)
                for called_func in called_functions:
                    # Find the called function in symbols and add relationship
                    for symbol_id, symbol_info in symbols.items():
                        if called_func in symbol_id.split("::")[-1]:
                            if symbol_info.called_by is not None and current_function not in symbol_info.called_by:
                                symbol_info.called_by.append(current_function)

    def _extract_rust_function_name(self, line: str) -> Optional[str]:
        """Extract function name from Rust function declaration."""
        try:
            # fn functionName(...) or pub fn functionName(...)
            match = re.match(r'(?:pub\s+)?fn\s+(\w+)\s*\(', line)
            if match:
                return match.group(1)
        except (OSError, ValueError, RuntimeError) as e:
            pass
        return None

    def _extract_rust_called_functions(self, line: str) -> List[str]:
        """Extract function names that are being called in this line."""
        called_functions = []

        # Find patterns like: functionName( or obj.methodName( or Type::function(
        patterns = [
            r'(\w+)\s*\(',  # functionName(
            r'\.(\w+)\s*\(',  # .methodName(
            r'(\w+)::(\w+)\s*\(',  # Type::function(
        ]

        for pattern in patterns:
            matches = re.findall(pattern, line)
            if isinstance(matches[0], tuple) if matches else False:
                # For Type::function( pattern, take the function name
                for match in matches:
                    if len(match) == 2:
                        called_functions.append(match[1])
                    else:
                        called_functions.append(match)
            else:
                called_functions.extend(matches)

        return called_functions
