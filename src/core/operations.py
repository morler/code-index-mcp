"""
Operations - 语义操作模块

高级代码操作功能，如重构、分析等
按照plans.md要求独立化操作逻辑
"""

from typing import Any, Dict, List

from .index import CodeIndex, SearchQuery


class SemanticOperations:
    """语义操作引擎 - 高级功能"""

    def __init__(self, index: CodeIndex):
        self.index = index

    def find_references(self, symbol_name: str) -> Dict[str, Any]:
        """查找符号的所有引用"""
        query = SearchQuery(pattern=symbol_name, type="references")
        result = self.index.search(query)
        return {
            "symbol": symbol_name,
            "references": result.matches,
            "count": result.total_count,
            "search_time": result.search_time,
        }

    def find_definition(self, symbol_name: str) -> Dict[str, Any]:
        """查找符号定义"""
        query = SearchQuery(pattern=symbol_name, type="definition")
        result = self.index.search(query)
        return {
            "symbol": symbol_name,
            "definition": result.matches,
            "found": len(result.matches) > 0,
            "search_time": result.search_time,
        }

    def find_callers(self, function_name: str) -> Dict[str, Any]:
        """查找函数调用者"""
        query = SearchQuery(pattern=function_name, type="callers")
        result = self.index.search(query)
        return {
            "function": function_name,
            "callers": result.matches,
            "count": result.total_count,
            "search_time": result.search_time,
        }

    def analyze_symbol_usage(self, symbol_name: str) -> Dict[str, Any]:
        """分析符号使用情况"""
        definition = self.find_definition(symbol_name)
        references = self.find_references(symbol_name)
        callers = self.find_callers(symbol_name)

        return {
            "symbol": symbol_name,
            "definition": definition["definition"],
            "references": references["references"],
            "callers": callers["callers"],
            "usage_count": references["count"] + callers["count"],
            "is_defined": definition["found"],
            "is_used": references["count"] > 0 or callers["count"] > 0,
        }

    def detect_unused_symbols(self) -> List[Dict[str, Any]]:
        """检测未使用的符号"""
        unused = []
        for symbol_name, symbol_info in self.index.symbols.items():
            # 简单检测：没有引用和调用者的符号
            if not symbol_info.references and not symbol_info.called_by:
                unused.append(
                    {
                        "symbol": symbol_name,
                        "type": symbol_info.type,
                        "file": symbol_info.file,
                        "line": symbol_info.line,
                    }
                )
        return unused

    def analyze_file_dependencies(self, file_path: str) -> Dict[str, Any]:
        """分析文件依赖关系"""
        file_info = self.index.get_file(file_path)
        if not file_info:
            return {"error": f"File not found: {file_path}"}

        # 分析导入和导出
        dependencies = {
            "file": file_path,
            "imports": file_info.imports,
            "exports": file_info.exports,
            "symbols": file_info.symbols,
            "language": file_info.language,
            "lines": file_info.line_count,
        }

        # 查找使用此文件导出的其他文件
        used_by = []
        for other_path, other_info in self.index.files.items():
            if other_path != file_path:
                # 简单检测：其他文件导入了此文件的导出
                for export in file_info.exports:
                    if export in other_info.imports:
                        used_by.append(other_path)
                        break

        dependencies["used_by"] = used_by
        return dependencies
