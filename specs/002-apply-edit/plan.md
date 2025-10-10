# Implementation Plan: 取消apply_edit备份功能

**Branch**: `002-apply-edit` | **Date**: 2025-01-09 | **Spec**: spec.md
**Input**: Feature specification from `/specs/002-apply-edit/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

取消apply_edit工具的磁盘备份功能，改用内存备份机制实现错误回滚。通过移除文件系统I/O操作，提升20%的编辑性能并减少50%的磁盘空间使用。保持API兼容性的同时，实现LRU内存管理和文件锁定机制确保数据安全。

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: tree-sitter, SCIP protocol, xxhash  
**Storage**: File system with in-memory backup  
**Testing**: pytest with performance benchmarks  
**Target Platform**: Cross-platform (Windows/Linux/macOS)  
**Project Type**: Single MCP server project  
**Performance Goals**: Sub-100ms file operations, 20% response time reduction  
**Constraints**: <100MB memory usage, <200ms p95 response time, files <200 lines  
**Scale/Scope**: Typical projects with <10k files, incremental updates <1 second

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Required Gates (Code Index MCP Constitution)

- **Linus-Style Direct Data Manipulation**: ✅ Direct memory manipulation, no service abstractions
- **Unified Interface**: ✅ All operations through existing unified_tool interface
- **SCIP Protocol First**: ✅ No changes to symbol operations, maintains SCIP compliance
- **Incremental Performance**: ✅ Memory-based backup improves performance, <100MB usage maintained
- **Simplicity Obsession**: ✅ Eliminates backup file complexity, reduces code paths

### Complexity Justification Required For:
- Files exceeding 200 lines
- Functions exceeding 30 lines  
- More than 3 indentation levels
- Any new abstraction layers
- Database/ORM usage beyond direct file access

### Performance Requirements:
- ✅ Sub-100ms file operations (target: <100ms vs current 150ms, 33%+ improvement)
- ✅ <1 second incremental updates for <100 changed files
- ✅ Zero-copy data access patterns maintained

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── code_index_mcp/
│   ├── core/
│   │   ├── edit.py              # Modified: remove backup file operations
│   │   ├── backup.py            # Modified: memory-based backup manager
│   │   ├── operations.py        # Modified: simplified edit workflow
│   │   ├── memory_backup.py     # New: LRU memory backup manager
│   │   ├── file_state.py        # New: 文件状态跟踪器 for rollback
│   │   ├── edit_operation.py    # New: edit operation data structure
│   │   ├── file_lock.py         # New: file locking mechanism
│   │   ├── memory_monitor.py    # New: memory usage monitoring
│   │   └── edit_logger.py       # New: edit operation logging
│   ├── server_unified.py        # Modified: use memory backup
│   └── mcp_tools.py             # Modified: tool_apply_edit function

tests/
├── test_edit_operations.py      # Updated: memory backup tests
├── test_performance.py          # Updated: benchmark memory vs disk backup
├── test_integration.py          # Updated: error handling tests
├── contract/
│   ├── test_edit_api.py         # New: API contract tests
│   └── test_edit_rollback.py    # New: rollback contract tests
├── integration/
│   ├── test_edit_no_backup.py   # New: no-backup integration tests
│   ├── test_memory_rollback.py  # New: memory rollback tests
│   └── test_concurrent_rollback.py # New: concurrent rollback tests
├── performance/
│   └── test_edit_performance.py # New: performance comparison tests
└── unit/
    ├── test_memory_backup.py    # New: memory backup unit tests
    └── test_file_lock.py        # New: file locking unit tests
```

**Structure Decision**: Single project structure with modifications to core edit and backup modules only. No new directories or major restructuring required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
