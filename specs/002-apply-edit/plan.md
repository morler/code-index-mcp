# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

取消apply_edit工具的磁盘备份功能，改用内存备份机制实现错误回滚。通过移除文件系统I/O操作，提升20%的编辑性能并减少50%的磁盘空间使用。保持API兼容性的同时，实现LRU内存管理和文件锁定机制确保数据安全。

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

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
- ✅ Sub-100ms file operations (target: 120ms vs current 150ms)
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
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
src/
├── code_index_mcp/
│   ├── core/
│   │   ├── edit.py              # Modified: remove backup file operations
│   │   ├── backup.py            # Modified: memory-based backup manager
│   │   └── operations.py        # Modified: simplified edit workflow
│   └── server_unified.py        # Unchanged: maintains unified interface

tests/
├── test_edit_operations.py      # Updated: memory backup tests
├── test_performance.py          # Updated: benchmark memory vs disk backup
└── test_integration.py          # Updated: error handling tests
```

**Structure Decision**: Single project structure with modifications to core edit and backup modules only. No new directories or major restructuring required.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
