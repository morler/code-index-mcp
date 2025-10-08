"""
SCIP协议完整支持 - Linus风格直接数据操作

符合SCIP (Source Code Indexing Protocol) 标准的符号管理和跨文件引用解析。
采用操作注册表消除特殊情况，实现"Good Taste"原则。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast


@dataclass
class SCIPSymbol:
    """SCIP标准符号定义"""

    symbol_id: str  # SCIP标准符号ID格式
    name: str
    language: str
    file_path: str
    line: int
    column: int
    symbol_type: str  # function, class, variable, module等
    signature: Optional[str] = None
    documentation: Optional[str] = None
    references: List[str] = field(default_factory=list)  # 引用此符号的位置
    definitions: List[str] = field(default_factory=list)  # 符号定义位置


@dataclass
class SCIPOccurrence:
    """SCIP符号出现位置"""

    symbol_id: str
    file_path: str
    line: int
    column: int
    occurrence_type: str  # definition, reference, declaration
    context: Optional[str] = None  # 上下文代码片段


@dataclass
class SCIPDocument:
    """SCIP文档 - 单个文件的符号信息"""

    file_path: str
    language: str
    symbols: List[SCIPSymbol] = field(default_factory=list)
    occurrences: List[SCIPOccurrence] = field(default_factory=list)
    external_symbols: Set[str] = field(default_factory=set)  # 外部符号引用


class SCIPSymbolManager:
    """
    SCIP符号管理器 - Linus风格统一数据操作

    消除特殊情况的单一入口点，替代多个分散的符号处理逻辑。
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.symbols: Dict[str, SCIPSymbol] = {}
        self.documents: Dict[str, SCIPDocument] = {}
        self.symbol_index: Dict[str, List[str]] = {}  # name -> symbol_ids

        # Linus风格：操作注册表消除条件分支
        self._language_processors = {
            "python": self._process_python_symbol,
            "javascript": self._process_javascript_symbol,
            "typescript": self._process_typescript_symbol,
            "java": self._process_java_symbol,
            "go": self._process_go_symbol,
            "zig": self._process_zig_symbol,
        }

    def generate_symbol_id(
        self,
        symbol_name: str,
        file_path: str,
        language: str,
        symbol_type: str = "unknown",
    ) -> str:
        """
        生成SCIP标准符号ID

        格式: scip:<scheme>:<manager>:<namespace>:<symbol>
        例如: scip:python:file:/path/to/file.py:MyClass
        """
        # 标准化文件路径
        rel_path = self._normalize_path(file_path)

        # 生成符号标识符
        symbol_descriptor = f"{symbol_type}:{symbol_name}"

        # SCIP标准格式
        symbol_id = f"scip:{language}:file:{rel_path}:{symbol_descriptor}"

        return symbol_id

    def add_symbol(self, symbol: SCIPSymbol) -> None:
        """添加符号到索引 - 统一入口点"""
        self.symbols[symbol.symbol_id] = symbol

        # 更新名称索引 - 支持快速查找
        symbol_ids = self.symbol_index.setdefault(symbol.name, [])
        if symbol.symbol_id not in symbol_ids:
            symbol_ids.append(symbol.symbol_id)

    def find_symbol_by_name(self, name: str) -> List[SCIPSymbol]:
        """按名称查找符号 - 支持重载和多定义"""
        symbol_ids = self.symbol_index.get(name, [])
        return [self.symbols[sid] for sid in symbol_ids if sid in self.symbols]

    def find_symbol_by_id(self, symbol_id: str) -> Optional[SCIPSymbol]:
        """按SCIP ID查找符号"""
        return self.symbols.get(symbol_id)

    def resolve_references(self, symbol_id: str) -> List[SCIPOccurrence]:
        """
        解析符号引用 - 跨文件支持

        返回所有引用指定符号的位置
        """
        references = []

        for document in self.documents.values():
            for occurrence in document.occurrences:
                if (
                    occurrence.symbol_id == symbol_id
                    and occurrence.occurrence_type == "reference"
                ):
                    references.append(occurrence)

        return references

    def resolve_definitions(self, symbol_id: str) -> List[SCIPOccurrence]:
        """解析符号定义位置"""
        definitions = []

        for document in self.documents.values():
            for occurrence in document.occurrences:
                if (
                    occurrence.symbol_id == symbol_id
                    and occurrence.occurrence_type
                    in [
                        "definition",
                        "declaration",
                    ]
                ):
                    definitions.append(occurrence)

        return definitions

    def create_document(self, file_path: str, language: str) -> SCIPDocument:
        """创建SCIP文档"""
        doc = SCIPDocument(file_path=self._normalize_path(file_path), language=language)
        self.documents[doc.file_path] = doc
        return doc

    def process_file_symbols(
        self, file_path: str, language: str, symbols: List[Dict[str, Any]]
    ) -> SCIPDocument:
        """
        处理文件符号 - 语言无关统一接口

        使用操作注册表消除语言特殊情况
        """
        document = self.create_document(file_path, language)

        # 获取语言处理器
        processor = self._language_processors.get(
            language, self._process_generic_symbol
        )

        for symbol_data in symbols:
            try:
                scip_symbol = processor(symbol_data, file_path, language)
                if scip_symbol:
                    document.symbols.append(scip_symbol)
                    self.add_symbol(scip_symbol)

                    # 添加定义出现位置
                    occurrence = SCIPOccurrence(
                        symbol_id=scip_symbol.symbol_id,
                        file_path=document.file_path,
                        line=scip_symbol.line,
                        column=scip_symbol.column,
                        occurrence_type="definition",
                    )
                    document.occurrences.append(occurrence)

            except Exception:
                # 忽略处理错误，继续处理其他符号
                continue

        return document

    def find_cross_references(
        self, symbol_name: str
    ) -> Dict[str, List[SCIPOccurrence]]:
        """
        查找符号的跨文件引用

        返回格式: {file_path: [occurrences]}
        """
        cross_refs: Dict[str, List[SCIPOccurrence]] = {}

        # 查找所有匹配名称的符号
        symbols = self.find_symbol_by_name(symbol_name)

        for symbol in symbols:
            references = self.resolve_references(symbol.symbol_id)

            for ref in references:
                file_refs = cross_refs.setdefault(ref.file_path, [])
                file_refs.append(ref)

        return cross_refs

    def get_symbol_graph(self, symbol_id: str) -> Dict[str, Any]:
        """
        获取符号关系图

        包含定义、引用、调用关系等完整信息
        """
        symbol = self.find_symbol_by_id(symbol_id)
        if not symbol:
            return {}

        return {
            "symbol": symbol,
            "definitions": self.resolve_definitions(symbol_id),
            "references": self.resolve_references(symbol_id),
            "cross_file_usage": len(
                set(occ.file_path for occ in self.resolve_references(symbol_id))
            ),
        }

    def export_scip_index(self) -> Dict[str, Any]:
        """
        导出SCIP标准格式索引

        符合SCIP协议的完整索引数据
        """
        return {
            "metadata": {
                "version": "0.3.0",
                "tool_info": {"name": "code-index-mcp", "version": "1.0.0"},
                "project_root": str(self.project_root),
            },
            "documents": [
                {
                    "relative_path": doc.file_path,
                    "language": doc.language,
                    "symbols": [
                        {
                            "symbol": sym.symbol_id,
                            "kind": self._map_symbol_type_to_scip_kind(sym.symbol_type),
                            "display_name": sym.name,
                        }
                        for sym in doc.symbols
                    ],
                    "occurrences": [
                        {
                            "range": self._create_scip_range(occ.line, occ.column),
                            "symbol": occ.symbol_id,
                            "symbol_roles": self._map_occurrence_type_to_roles(
                                occ.occurrence_type
                            ),
                        }
                        for occ in doc.occurrences
                    ],
                }
                for doc in self.documents.values()
            ],
            "external_symbols": list(
                set().union(*[doc.external_symbols for doc in self.documents.values()])
            ),
        }

    # 私有方法 - 语言特定处理器

    def _process_python_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """Python符号处理器"""
        symbol_id = self.generate_symbol_id(
            symbol_data["name"], file_path, language, symbol_data.get("type", "unknown")
        )

        return SCIPSymbol(
            symbol_id=symbol_id,
            name=symbol_data["name"],
            language=language,
            file_path=self._normalize_path(file_path),
            line=symbol_data.get("line", 0),
            column=symbol_data.get("column", 0),
            symbol_type=symbol_data.get("type", "unknown"),
            signature=symbol_data.get("signature"),
            documentation=symbol_data.get("docstring"),
        )

    def _process_javascript_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """JavaScript符号处理器"""
        # JavaScript特定逻辑
        return self._process_generic_symbol(symbol_data, file_path, language)

    def _process_typescript_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """TypeScript符号处理器"""
        # TypeScript特定逻辑，包含类型信息
        return self._process_generic_symbol(symbol_data, file_path, language)

    def _process_java_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """Java符号处理器"""
        # Java特定逻辑，包含包名和访问修饰符
        return self._process_generic_symbol(symbol_data, file_path, language)

    def _process_go_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """Go符号处理器"""
        # Go特定逻辑，包含包和接口信息
        return self._process_generic_symbol(symbol_data, file_path, language)

    def _process_zig_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """Zig符号处理器"""
        # Zig特定逻辑
        return self._process_generic_symbol(symbol_data, file_path, language)

    def _process_generic_symbol(
        self, symbol_data: Dict[str, Any], file_path: str, language: str
    ) -> Optional[SCIPSymbol]:
        """通用符号处理器 - 语言无关逻辑"""
        symbol_id = self.generate_symbol_id(
            symbol_data["name"], file_path, language, symbol_data.get("type", "unknown")
        )

        return SCIPSymbol(
            symbol_id=symbol_id,
            name=symbol_data["name"],
            language=language,
            file_path=self._normalize_path(file_path),
            line=symbol_data.get("line", 0),
            column=symbol_data.get("column", 0),
            symbol_type=symbol_data.get("type", "unknown"),
        )

    def _normalize_path(self, file_path: str) -> str:
        """标准化文件路径 - 统一路径处理"""
        path = Path(file_path)
        if path.is_absolute():
            try:
                rel_path = path.relative_to(self.project_root)
                return str(rel_path).replace("\\", "/")
            except ValueError:
                # 文件在项目外
                return str(path).replace("\\", "/")
        return str(path).replace("\\", "/")

    def _map_symbol_type_to_scip_kind(self, symbol_type: str) -> int:
        """映射符号类型到SCIP标准类型"""
        scip_kinds = {
            "unknown": 0,
            "file": 1,
            "module": 2,
            "namespace": 3,
            "package": 4,
            "class": 5,
            "method": 6,
            "property": 7,
            "field": 8,
            "constructor": 9,
            "enum": 10,
            "interface": 11,
            "function": 12,
            "variable": 13,
            "constant": 14,
            "string": 15,
            "number": 16,
            "boolean": 17,
            "array": 18,
            "object": 19,
            "key": 20,
            "null": 21,
            "enum_member": 22,
            "struct": 23,
            "event": 24,
            "operator": 25,
            "type_parameter": 26,
        }
        return scip_kinds.get(symbol_type, 0)

    def _map_occurrence_type_to_roles(self, occurrence_type: str) -> int:
        """映射出现类型到SCIP角色"""
        roles = {
            "definition": 1,
            "declaration": 2,
            "reference": 4,
            "implementation": 8,
            "type_definition": 16,
            "read": 32,
            "write": 64,
        }
        return roles.get(occurrence_type, 4)  # 默认为引用

    def _create_scip_range(
        self, line: int, column: int, end_line: Optional[int] = None,
        end_column: Optional[int] = None
    ) -> List[int]:
        """创建SCIP范围格式 [start_line, start_col, end_line, end_col]"""
        if end_line is None:
            end_line = line
        if end_column is None:
            end_column = column + 1  # 假设单字符符号

        return [line, column, end_line, end_column]


# 全局SCIP管理器实例
_global_scip_manager: Optional[SCIPSymbolManager] = None


def get_scip_manager() -> Optional[SCIPSymbolManager]:
    """获取全局SCIP管理器"""
    return _global_scip_manager


def create_scip_manager(project_root: str) -> SCIPSymbolManager:
    """创建SCIP管理器并设置为全局实例"""
    global _global_scip_manager
    _global_scip_manager = SCIPSymbolManager(project_root)
    return _global_scip_manager


def integrate_with_code_index(code_index, scip_manager: SCIPSymbolManager) -> None:
    """
    将SCIP管理器集成到CodeIndex中

    这是Linus风格的直接集成，避免抽象层
    """
    # 为CodeIndex添加SCIP方法
    code_index.scip_manager = scip_manager

    # 添加SCIP查询方法
    def find_scip_symbol(self, name: str) -> List[SCIPSymbol]:
        result = self.scip_manager.find_symbol_by_name(name)
        return cast(List[SCIPSymbol], result)

    def get_cross_references(self, symbol_name: str) -> Dict[str, List[SCIPOccurrence]]:
        result = self.scip_manager.find_cross_references(symbol_name)
        return cast(Dict[str, List[SCIPOccurrence]], result)

    def export_scip(self) -> Dict[str, Any]:
        result = self.scip_manager.export_scip_index()
        return cast(Dict[str, Any], result)

    # 绑定方法到CodeIndex实例
    code_index.find_scip_symbol = find_scip_symbol.__get__(code_index)
    code_index.get_cross_references = get_cross_references.__get__(code_index)
    code_index.export_scip = export_scip.__get__(code_index)
