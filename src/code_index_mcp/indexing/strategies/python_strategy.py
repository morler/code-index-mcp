"""
Python parsing strategy for semantic indexing.
"""

import ast
from typing import Any, Dict, List


class PythonParsingStrategy:
    """Strategy for parsing Python files."""

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Python file and extract symbols."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            symbols: Dict[str, List[str]] = {
                "classes": [],
                "functions": [],
                "variables": [],
                "imports": [],
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols["classes"].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    symbols["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        symbols["imports"].append(f"{module}.{alias.name}")

            return symbols

        except Exception:
            return {"classes": [], "functions": [], "variables": [], "imports": []}
