"""
Semantic Operations - 语义搜索操作

从search_optimized.py拆分，保持文件<200行
"""

from typing import Any, Dict, List

from .index import CodeIndex, SearchQuery


class SemanticOperations:
    """语义操作 - 直接数据访问"""

    def __init__(self, index: CodeIndex):
        self.index = index

    def find_references_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """引用查找 - 直接数据访问"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []

        matches = []
        for ref in symbol_info.references:
            if ":" in ref:
                parts = ref.split(":")
                if len(parts) >= 2:
                    matches.append(
                        {
                            "file": parts[0],
                            "line": int(parts[1]),
                            "type": "reference",
                            "symbol": query.pattern,
                        }
                    )
        return matches

    def find_definition_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """定义查找 - 直接索引访问"""
        symbol_info = self.index.symbols.get(query.pattern)
        return (
            [
                {
                    "file": symbol_info.file,
                    "line": symbol_info.line,
                    "type": "definition",
                    "symbol": query.pattern,
                }
            ]
            if symbol_info
            else []
        )

    def find_callers_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """调用者查找 - 直接关系访问"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []

        matches = []
        for caller in symbol_info.called_by:
            caller_info = self.index.symbols.get(caller)
            if caller_info:
                matches.append(
                    {
                        "symbol": caller,
                        "file": caller_info.file,
                        "line": caller_info.line,
                        "type": "caller",
                    }
                )
        return matches

    def find_implementations_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找实现 - 直接索引访问"""
        matches = []
        # 查找实现特定接口或基类的符号
        for symbol_name, symbol_info in self.index.symbols.items():
            if (
                symbol_info.type == "class"
                and symbol_info.signature
                and query.pattern in symbol_info.signature
            ):
                matches.append(
                    {
                        "symbol": symbol_name,
                        "file": symbol_info.file,
                        "line": symbol_info.line,
                        "type": "implementation",
                    }
                )
        return matches

    def find_hierarchy_direct(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """查找层次结构 - 直接关系访问"""
        symbol_info = self.index.symbols.get(query.pattern)
        if not symbol_info:
            return []

        matches = []
        # 添加符号本身
        matches.append(
            {
                "symbol": query.pattern,
                "file": symbol_info.file,
                "line": symbol_info.line,
                "type": "self",
                "level": 0,
            }
        )

        # 添加调用者（上级）
        for caller in symbol_info.called_by:
            caller_info = self.index.symbols.get(caller)
            if caller_info:
                matches.append(
                    {
                        "symbol": caller,
                        "file": caller_info.file,
                        "line": caller_info.line,
                        "type": "parent",
                        "level": -1,
                    }
                )

        return matches
