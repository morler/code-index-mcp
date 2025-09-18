"""
Rust parsing strategy using regex patterns.
"""

import re
from typing import Dict, List, Tuple, Optional
from .base_strategy import ParsingStrategy
from ..models import SymbolInfo, FileInfo


class RustParsingStrategy(ParsingStrategy):
    """Rust-specific parsing strategy using regex patterns."""

    def get_language_name(self) -> str:
        return "rust"

    def get_supported_extensions(self) -> List[str]:
        return ['.rs']

    def parse_file(self, file_path: str, content: str) -> Tuple[Dict[str, SymbolInfo], FileInfo]:
        """Parse Rust file using regex patterns."""
        symbols = {}
        functions = []
        classes = []  # Rust structs, enums, traits
        imports = []
        package = None

        lines = content.splitlines()

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*'):
                continue

            # Crate/package name (from Cargo.toml would be more accurate, but we can get module names)
            if line.startswith('mod '):
                mod_match = re.search(r'mod\s+(\w+)', line)
                if mod_match:
                    package = mod_match.group(1)

            # Use statements (imports)
            elif line.startswith('use '):
                use_match = re.search(r'use\s+([^;]+)', line)
                if use_match:
                    imports.append(use_match.group(1).strip())

            # Function declarations
            elif re.match(r'fn\s+\w+', line):
                func_match = re.match(r'fn\s+(\w+)\s*\(', line)
                if func_match:
                    func_name = func_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, func_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="function",
                        file=file_path,
                        line=i + 1,
                        signature=line
                    )
                    functions.append(func_name)

            # Struct declarations
            elif re.match(r'struct\s+\w+', line):
                struct_match = re.match(r'struct\s+(\w+)', line)
                if struct_match:
                    struct_name = struct_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, struct_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="struct",
                        file=file_path,
                        line=i + 1
                    )
                    classes.append(struct_name)

            # Enum declarations
            elif re.match(r'enum\s+\w+', line):
                enum_match = re.match(r'enum\s+(\w+)', line)
                if enum_match:
                    enum_name = enum_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, enum_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="enum",
                        file=file_path,
                        line=i + 1
                    )
                    classes.append(enum_name)

            # Trait declarations
            elif re.match(r'trait\s+\w+', line):
                trait_match = re.match(r'trait\s+(\w+)', line)
                if trait_match:
                    trait_name = trait_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, trait_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="trait",
                        file=file_path,
                        line=i + 1
                    )
                    classes.append(trait_name)

            # Impl blocks (methods within impl blocks)
            elif re.match(r'impl\s+\w+', line):
                impl_match = re.match(r'impl\s+(\w+)', line)
                if impl_match:
                    # Track the impl context for subsequent methods
                    impl_type = impl_match.group(1)
                    # Continue parsing to find methods within this impl block
                    self._parse_impl_block(lines, i + 1, file_path, symbols, functions, impl_type)

            # Const declarations
            elif re.match(r'const\s+\w+', line):
                const_match = re.match(r'const\s+(\w+)', line)
                if const_match:
                    const_name = const_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, const_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="const",
                        file=file_path,
                        line=i + 1
                    )

            # Static declarations
            elif re.match(r'static\s+\w+', line):
                static_match = re.match(r'static\s+(\w+)', line)
                if static_match:
                    static_name = static_match.group(1)
                    symbol_id = self._create_symbol_id(file_path, static_name)
                    symbols[symbol_id] = SymbolInfo(
                        type="static",
                        file=file_path,
                        line=i + 1
                    )

        # Phase 2: Add call relationship analysis
        self._analyze_rust_calls(content, symbols, file_path)

        file_info = FileInfo(
            language=self.get_language_name(),
            line_count=len(lines),
            symbols={"functions": functions, "classes": classes},
            imports=imports,
            package=package
        )

        return symbols, file_info

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
