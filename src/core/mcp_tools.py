"""
MCP Tools - Linus式统一工具实现

替代tools/目录下的所有Java风格抽象
直接操作数据，无包装器，无特殊情况
"""

import errno
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from .builder import handle_mcp_errors
from .index import SearchQuery, get_index
from .index import set_project_path as core_set_project_path
# 向后兼容 - 导出execute_tool
from .tool_registry import execute_tool

__all__ = ["execute_tool"]


def _create_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """创建具体化的错误响应 - Linus风格：直接说明问题"""
    if isinstance(error, FileNotFoundError):
        return {"success": False, "error": f"File not found: {error.filename}"}
    elif isinstance(error, PermissionError):
        return {"success": False, "error": f"Permission denied: {error.filename}"}
    elif isinstance(error, OSError) and error.errno == errno.ENOENT:
        return {
            "success": False,
            "error": f"Directory does not exist: {error.filename}",
        }
    elif isinstance(error, OSError) and error.errno == errno.EACCES:
        return {"success": False, "error": f"Access denied: {error.filename}"}
    elif isinstance(error, UnicodeDecodeError):
        return {
            "success": False,
            "error": f"File encoding error: cannot decode {error.object!r}",
        }
    elif isinstance(error, ValueError):
        return {"success": False, "error": f"Invalid value: {str(error)}"}
    else:
        error_msg = f"{context}: {str(error)}" if context else str(error)
        return {"success": False, "error": error_msg}


def _resolve_file_path(base_path: Optional[str], file_path: str) -> Path:
    """统一路径解析 - Linus风格：消除重复的Path处理逻辑"""
    if not base_path:
        return Path(file_path)

    base = Path(base_path)
    file_p = Path(file_path)

    # 绝对路径直接返回，相对路径相对于base_path
    return file_p if file_p.is_absolute() else base / file_path


# ----- 核心工具 - 直接数据操作 -----


@handle_mcp_errors
def tool_set_project_path(path: str) -> Dict[str, Any]:
    """设置项目路径 - 直接操作"""
    index = core_set_project_path(path)
    return {
        "success": True,
        "path": path,
        "files_indexed": len(index.files),
        "symbols_indexed": len(index.symbols),
    }


@handle_mcp_errors
def tool_search_code(
    pattern: str,
    search_type: str = "text",
    file_pattern: Optional[str] = None,
    case_sensitive: bool = True,
) -> Dict[str, Any]:
    """统一搜索 - 消除特殊情况"""
    index = get_index()
    query = SearchQuery(
        pattern=pattern,
        type=search_type,
        file_pattern=file_pattern,
        case_sensitive=case_sensitive,
    )
    result = index.search(query)
    return {
        "success": True,
        "matches": result.matches,
        "total_count": result.total_count,
        "search_time": result.search_time,
        "query_type": search_type,
    }


@handle_mcp_errors
def tool_find_files(pattern: str) -> Dict[str, Any]:
    """文件查找 - 直接操作"""
    index = get_index()
    files = index.find_files_by_pattern(pattern)
    return {"success": True, "files": files, "count": len(files)}


@handle_mcp_errors
def tool_get_file_summary(file_path: str) -> Dict[str, Any]:
    """文件信息 - 直接访问"""
    index = get_index()
    file_info = index.get_file(file_path)
    if not file_info:
        return {"success": False, "error": f"File not found: {file_path}"}

    return {
        "success": True,
        "file_path": file_path,
        "language": file_info.language,
        "line_count": file_info.line_count,
        "symbol_count": sum(len(symbols) for symbols in file_info.symbols.values()),
        "imports": file_info.imports,
        "exports": file_info.exports,
    }


@handle_mcp_errors
def tool_get_index_stats() -> Dict[str, Any]:
    """索引统计 - 直接数据"""
    index = get_index()
    stats = index.get_stats()
    return {"success": True, **stats}


# ----- 语义搜索 - 数据驱动 -----


def tool_semantic_search(query: str, search_type: str) -> Dict[str, Any]:
    """统一语义搜索 - 替代所有专门函数"""
    return cast(Dict[str, Any], tool_search_code(query, search_type))


def tool_find_references(symbol_name: str) -> Dict[str, Any]:
    """查找引用 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "references")


def tool_find_definition(symbol_name: str) -> Dict[str, Any]:
    """查找定义 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "definition")


def tool_find_callers(function_name: str) -> Dict[str, Any]:
    """查找调用者 - 委托给统一接口"""
    return tool_semantic_search(function_name, "callers")


def tool_find_implementations(interface_name: str) -> Dict[str, Any]:
    """查找实现 - 委托给统一接口"""
    return tool_semantic_search(interface_name, "implementations")


def tool_find_hierarchy(symbol_name: str) -> Dict[str, Any]:
    """查找层次结构 - 委托给统一接口"""
    return tool_semantic_search(symbol_name, "hierarchy")


@handle_mcp_errors
def tool_organize_imports(file_path: str) -> Dict[str, Any]:
    """整理导入 - 简单实现"""
    index = get_index()
    file_info = index.get_file(file_path)
    if not file_info:
        return {"success": False, "error": f"File not found: {file_path}"}

    # 简单的导入整理逻辑
    organized_imports = sorted(set(file_info.imports))
    return {
        "success": True,
        "original_count": len(file_info.imports),
        "organized_count": len(organized_imports),
        "organized_imports": organized_imports,
    }


# ----- 系统操作 - 最简实现 -----


@handle_mcp_errors
def tool_refresh_index() -> Dict[str, Any]:
    """刷新索引 - 优先使用增量更新"""
    index = get_index()
    if not index.base_path:
        return {"success": False, "error": "No project path set"}

    # Linus原则: 优先使用增量更新，减少无意义的重建
    start_time = time.time()
    stats = index.update_incrementally()
    elapsed = time.time() - start_time

    return {
        "success": True,
        "files_indexed": len(index.files),
        "symbols_indexed": len(index.symbols),
        "update_stats": stats,
        "update_time": elapsed,
        "method": "incremental",
    }


@handle_mcp_errors
def tool_check_file_exists(file_path: str) -> Dict[str, Any]:
    """文件存在检查 - 直接系统调用"""
    index = get_index()
    full_path = Path(index.base_path) / file_path
    exists = full_path.exists()
    return {
        "success": True,
        "exists": exists,
        "full_path": str(full_path),
        "in_index": file_path in index.files,
    }


# ----- 文件内容读取工具 - Linus式直接访问 -----


@handle_mcp_errors
def tool_get_file_content(
    file_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    show_line_numbers: bool = False,
) -> Dict[str, Any]:
    """获取文件内容 - 直接操作，零抽象，支持全文件和片段"""
    index = get_index()

    # 直接文件操作
    full_path = _resolve_file_path(index.base_path, file_path)
    if not full_path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        # 复用SearchEngine的文件读取逻辑
        lines = full_path.read_text(encoding="utf-8", errors="ignore").split("\n")

        # 处理片段请求 - 消除特殊情况
        if start_line is not None:
            start_idx = max(0, start_line - 1)
            end_idx = len(lines) if end_line is None else min(len(lines), end_line)
            content_lines = lines[start_idx:end_idx]
            actual_start = start_line
        else:
            content_lines = lines
            actual_start = 1

        # 获取文件元信息（如果已索引）
        file_info = index.get_file(file_path)
        language = file_info.language if file_info else "unknown"

        # 构建返回数据 - 条件性包含line_numbers
        result = {
            "success": True,
            "file_path": file_path,
            "content": content_lines,
            "total_lines": len(lines),
            "language": language,
            "encoding": "utf-8",
            "start_line": actual_start,
            "end_line": end_line or len(lines),
        }

        # 只在需要时添加line_numbers - 消除冗余数据
        if show_line_numbers:
            if start_line is not None:
                result["line_numbers"] = list(
                    range(start_line, start_line + len(content_lines))
                )
            else:
                result["line_numbers"] = list(range(1, len(lines) + 1))

        return result
    except Exception as e:
        return _create_error_response(e, "Failed to read file")


# ----- 符号语法体提取工具 - Linus式启发式算法 -----


def _detect_syntax_body_end(lines: List[str], start_line: int, language: str) -> int:
    """
    检测语法体结束行 - Linus式启发式算法

    统一算法处理不同语言，消除特殊情况
    """
    if start_line >= len(lines):
        return start_line

    start_idx = start_line - 1  # 转换为0索引

    # 语言特定的检测策略
    if language in ["python"]:
        return _detect_python_body_end(lines, start_idx)
    elif language in ["javascript", "typescript", "java", "c", "cpp", "rust", "go"]:
        return _detect_brace_body_end(lines, start_idx)
    else:
        # 默认启发式：基于缩进的通用算法
        return _detect_indent_body_end(lines, start_idx)


def _detect_python_body_end(lines: List[str], start_idx: int) -> int:
    """Python缩进检测 - 最简实现"""
    if start_idx >= len(lines):
        return start_idx + 1

    start_line = lines[start_idx].rstrip()
    if not start_line:
        return start_idx + 1

    # 计算起始缩进
    start_indent = len(start_line) - len(start_line.lstrip())

    # 查找第一个小于等于起始缩进的非空行
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].rstrip()
        if not line:  # 跳过空行
            continue

        current_indent = len(line) - len(line.lstrip())
        if current_indent <= start_indent:
            return i  # 返回1索引行号

    return len(lines)  # 文件末尾


def _detect_brace_body_end(lines: List[str], start_idx: int) -> int:
    """大括号匹配检测 - 适用于C系语言"""
    if start_idx >= len(lines):
        return start_idx + 1

    brace_count = 0
    found_opening = False

    # 从起始行开始扫描
    for i in range(start_idx, len(lines)):
        line = lines[i]

        for char in line:
            if char == "{":
                brace_count += 1
                found_opening = True
            elif char == "}":
                brace_count -= 1
                if found_opening and brace_count == 0:
                    return i + 2  # 返回1索引，包含结束大括号的下一行

    return len(lines)  # 文件末尾


def _detect_indent_body_end(lines: List[str], start_idx: int) -> int:
    """通用缩进检测 - 语言无关算法"""
    if start_idx >= len(lines):
        return start_idx + 1

    start_line = lines[start_idx].rstrip()
    if not start_line:
        return start_idx + 1

    # 计算起始缩进
    start_indent = len(start_line) - len(start_line.lstrip())

    # 查找缩进回退的位置
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].rstrip()
        if not line:  # 跳过空行
            continue

        current_indent = len(line) - len(line.lstrip())
        if current_indent <= start_indent:
            return i  # 返回1索引行号

    return len(lines)  # 文件末尾


@handle_mcp_errors
def tool_get_symbol_body(
    symbol_name: str,
    file_path: Optional[str] = None,
    language: str = "auto",
    show_line_numbers: bool = False,
) -> Dict[str, Any]:
    """
    获取符号完整语法体 - Linus式组合现有功能

    统一接口处理所有符号类型和语言
    """
    index = get_index()

    # 1. 查找符号信息
    symbol_info = index.symbols.get(symbol_name)
    if not symbol_info:
        return {"success": False, "error": f"Symbol not found: {symbol_name}"}

    # 使用符号信息中的文件路径，除非显式指定
    target_file = file_path or symbol_info.file
    start_line = symbol_info.line

    # 2. 自动检测语言
    if language == "auto":
        file_info = index.get_file(target_file)
        language = file_info.language if file_info else "unknown"

    # 3. 读取文件内容
    try:
        full_path = _resolve_file_path(index.base_path, target_file)
        if not full_path.exists():
            return {"success": False, "error": f"File not found: {target_file}"}

        lines = full_path.read_text(encoding="utf-8", errors="ignore").split("\n")

        # 4. 检测语法体边界
        end_line = _detect_syntax_body_end(lines, start_line, language)

        # 5. 提取语法体内容
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        body_lines = lines[start_idx:end_idx]

        # 构建返回数据 - 条件性包含line_numbers
        result = {
            "success": True,
            "symbol_name": symbol_name,
            "symbol_type": symbol_info.type,
            "file_path": target_file,
            "language": language,
            "start_line": start_line,
            "end_line": end_line,
            "body_lines": body_lines,
            "signature": symbol_info.signature,
            "total_lines": len(body_lines),
        }

        # 只在需要时添加line_numbers - 消除冗余数据
        if show_line_numbers:
            result["line_numbers"] = list(
                range(start_line, start_line + len(body_lines))
            )

        return result

    except Exception as e:
        return _create_error_response(e, "Failed to extract symbol body")


# ----- 语义编辑工具 - 新增功能 -----


@handle_mcp_errors
def tool_rename_symbol(old_name: str, new_name: str) -> Dict[str, Any]:
    """符号重命名 - 原子性事务操作"""
    try:
        index = get_index()
        success, error, files_changed = index.rename_symbol_atomic(old_name, new_name)

        return {"success": success, "files_changed": files_changed, "error": error}
    except Exception as e:
        return _create_error_response(e, "Symbol rename failed")


@handle_mcp_errors
def tool_add_import(file_path: str, import_statement: str) -> Dict[str, Any]:
    """添加导入 - 原子性操作"""
    try:
        index = get_index()
        success, error = index.add_import_atomic(file_path, import_statement)

        return {
            "success": success,
            "files_changed": 1 if success and error is None else 0,
            "error": error,
        }
    except Exception as e:
        return _create_error_response(e, "Add import failed")


@handle_mcp_errors
def tool_update_incrementally() -> Dict[str, Any]:
    """增量更新索引 - Linus原则: 只处理变更文件"""
    index = get_index()
    if not index.base_path:
        return {"success": False, "error": "No project path set"}

    start_time = time.time()
    stats = index.update_incrementally()
    elapsed = time.time() - start_time

    return {
        "success": True,
        "update_stats": stats,
        "update_time": elapsed,
        "files_indexed": len(index.files),
        "symbols_indexed": len(index.symbols),
    }


@handle_mcp_errors
def tool_force_update_file(file_path: str) -> Dict[str, Any]:
    """强制更新指定文件 - 忽略变更检测"""
    index = get_index()
    if not index.base_path:
        return {"success": False, "error": "No project path set"}

    success = index.force_update_file(file_path)
    return {
        "success": success,
        "file_path": file_path,
        "files_indexed": len(index.files),
        "symbols_indexed": len(index.symbols),
    }


@handle_mcp_errors
def tool_get_changed_files() -> Dict[str, Any]:
    """获取变更文件列表 - 诊断工具"""
    index = get_index()
    if not index.base_path:
        return {"success": False, "error": "No project path set"}

    changed_files = index.get_changed_files()
    from .incremental import get_incremental_indexer

    stats = get_incremental_indexer().get_stats()

    return {"success": True, "changed_files": changed_files, "stats": stats}


@handle_mcp_errors
def tool_full_rebuild_index() -> Dict[str, Any]:
    """完全重建索引 - 强制全量更新"""
    index = get_index()
    if not index.base_path:
        return {"success": False, "error": "No project path set"}

    # 清空现有索引并重建
    start_time = time.time()
    new_index = core_set_project_path(index.base_path)
    elapsed = time.time() - start_time

    return {
        "success": True,
        "files_indexed": len(new_index.files),
        "symbols_indexed": len(new_index.symbols),
        "rebuild_time": elapsed,
        "method": "full_rebuild",
    }


@handle_mcp_errors
def tool_apply_edit(
    file_path: str, old_content: str, new_content: str
) -> Dict[str, Any]:
    """应用编辑 - 原子性操作"""
    try:
        index = get_index()
        success, error = index.edit_file_atomic(file_path, old_content, new_content)

        return {
            "success": success,
            "error": error,
            "files_changed": 1 if success else 0,
        }
    except Exception as e:
        return _create_error_response(e, "Apply edit failed")


# ----- SCIP协议工具 - Linus风格统一接口 -----


@handle_mcp_errors
def tool_generate_scip_symbol_id(
    symbol_name: str, file_path: str, language: str, symbol_type: str = "unknown"
) -> Dict[str, Any]:
    """生成SCIP标准符号ID"""
    index = get_index()
    if not index.scip_manager:
        return {"success": False, "error": "SCIP manager not initialized"}

    symbol_id = index.scip_manager.generate_symbol_id(
        symbol_name, file_path, language, symbol_type
    )

    return {
        "success": True,
        "symbol_id": symbol_id,
        "symbol_name": symbol_name,
        "file_path": file_path,
        "language": language,
        "symbol_type": symbol_type,
    }


@handle_mcp_errors
def tool_find_scip_symbol(symbol_name: str) -> Dict[str, Any]:
    """查找SCIP符号 - 支持重载和多定义"""
    index = get_index()
    if not hasattr(index, "find_scip_symbol"):
        return {"success": False, "error": "SCIP integration not available"}

    symbols = index.find_scip_symbol(symbol_name)

    return {
        "success": True,
        "symbol_name": symbol_name,
        "matches": [
            {
                "symbol_id": sym.symbol_id,
                "name": sym.name,
                "language": sym.language,
                "file_path": sym.file_path,
                "line": sym.line,
                "column": sym.column,
                "symbol_type": sym.symbol_type,
                "signature": sym.signature,
                "documentation": sym.documentation,
            }
            for sym in symbols
        ],
        "match_count": len(symbols),
    }


@handle_mcp_errors
def tool_get_cross_references(symbol_name: str) -> Dict[str, Any]:
    """获取符号的跨文件引用"""
    index = get_index()
    if not hasattr(index, "get_cross_references"):
        return {"success": False, "error": "SCIP integration not available"}

    cross_refs = index.get_cross_references(symbol_name)

    # 转换为JSON友好格式
    references_by_file = {}
    total_references = 0

    for file_path, occurrences in cross_refs.items():
        file_refs = []
        for occ in occurrences:
            file_refs.append(
                {
                    "symbol_id": occ.symbol_id,
                    "line": occ.line,
                    "column": occ.column,
                    "occurrence_type": occ.occurrence_type,
                    "context": occ.context,
                }
            )
        references_by_file[file_path] = file_refs
        total_references += len(file_refs)

    return {
        "success": True,
        "symbol_name": symbol_name,
        "references_by_file": references_by_file,
        "total_references": total_references,
        "files_with_references": len(references_by_file),
    }


@handle_mcp_errors
def tool_get_symbol_graph(symbol_id: str) -> Dict[str, Any]:
    """获取符号关系图 - 完整的依赖和引用信息"""
    index = get_index()
    if not index.scip_manager:
        return {"success": False, "error": "SCIP manager not initialized"}

    graph = index.scip_manager.get_symbol_graph(symbol_id)
    if not graph:
        return {"success": False, "error": f"Symbol not found: {symbol_id}"}

    # 转换为JSON友好格式
    result = {
        "success": True,
        "symbol_id": symbol_id,
        "symbol": {
            "name": graph["symbol"].name,
            "language": graph["symbol"].language,
            "file_path": graph["symbol"].file_path,
            "line": graph["symbol"].line,
            "symbol_type": graph["symbol"].symbol_type,
            "signature": graph["symbol"].signature,
        },
        "definitions": [
            {
                "file_path": def_occ.file_path,
                "line": def_occ.line,
                "column": def_occ.column,
                "occurrence_type": def_occ.occurrence_type,
            }
            for def_occ in graph["definitions"]
        ],
        "references": [
            {
                "file_path": ref_occ.file_path,
                "line": ref_occ.line,
                "column": ref_occ.column,
                "occurrence_type": ref_occ.occurrence_type,
                "context": ref_occ.context,
            }
            for ref_occ in graph["references"]
        ],
        "cross_file_usage": graph["cross_file_usage"],
        "definition_count": len(graph["definitions"]),
        "reference_count": len(graph["references"]),
    }

    return result


@handle_mcp_errors
def tool_export_scip_index() -> Dict[str, Any]:
    """导出SCIP标准格式索引"""
    index = get_index()
    if not hasattr(index, "export_scip"):
        return {"success": False, "error": "SCIP integration not available"}

    scip_index = index.export_scip()

    return {
        "success": True,
        "scip_index": scip_index,
        "metadata": scip_index.get("metadata", {}),
        "document_count": len(scip_index.get("documents", [])),
        "external_symbols_count": len(scip_index.get("external_symbols", [])),
    }


@handle_mcp_errors
def tool_process_file_with_scip(
    file_path: str, language: Optional[str] = None
) -> Dict[str, Any]:
    """使用SCIP处理单个文件的符号"""
    index = get_index()
    if not index.scip_manager:
        return {"success": False, "error": "SCIP manager not initialized"}

    # 自动检测语言
    if not language:
        from .builder import detect_language

        language = detect_language(file_path)

    # 从现有索引获取符号信息
    file_info = index.get_file(file_path)
    if not file_info:
        return {"success": False, "error": f"File not indexed: {file_path}"}

    # 转换为SCIP格式
    symbols_data = []
    for symbol_name, symbol_info in index.symbols.items():
        if symbol_info.file == file_path:
            symbols_data.append(
                {
                    "name": symbol_name,
                    "type": symbol_info.type,
                    "line": symbol_info.line,
                    "column": 0,  # 默认列
                    "signature": symbol_info.signature,
                }
            )

    # 使用SCIP管理器处理
    document = index.scip_manager.process_file_symbols(
        file_path, language, symbols_data
    )

    return {
        "success": True,
        "file_path": file_path,
        "language": language,
        "symbols_processed": len(document.symbols),
        "occurrences_created": len(document.occurrences),
        "external_symbols": len(document.external_symbols),
        "document": {
            "relative_path": document.file_path,
            "language": document.language,
            "symbols": [
                {
                    "symbol_id": sym.symbol_id,
                    "name": sym.name,
                    "symbol_type": sym.symbol_type,
                    "line": sym.line,
                    "signature": sym.signature,
                }
                for sym in document.symbols
            ],
        },
    }


# 工具注册表已移至tool_registry.py以保持文件<200行原则
