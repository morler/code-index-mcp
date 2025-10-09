# Implementation Plan: Apply Edit Backup Directory Fix

**Branch**: `001-apply-edit-edit` | **Date**: 2025-10-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-apply-edit-edit/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix apply_edit backup directory write issues by implementing robust backup creation with automatic directory management, fallback to system temp directory, proper error handling, and concurrent-safe file naming using microsecond timestamps.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: pathlib, shutil, tempfile, time, threading  
**Storage**: File system (.edit_backup directories, system temp)  
**Testing**: pytest with concurrent testing capabilities  
**Target Platform**: Cross-platform (Windows, Linux, macOS)  
**Project Type**: Single project (MCP server enhancement)  
**Performance Goals**: <50ms backup creation for <1MB files, 100 concurrent operations  
**Constraints**: <100ms file operations, <100MB memory, Linus-style direct manipulation  
**Scale/Scope**: Enterprise codebases with frequent edit operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Required Gates (Code Index MCP Constitution)

- **Linus-Style Direct Data Manipulation**: ✅ Direct file operations, no service abstractions (validated in research)
- **Unified Interface**: ✅ All backup operations through existing CodeIndex methods (validated in design)
- **SCIP Protocol First**: ✅ Not applicable (backup operations, not symbol operations)
- **Incremental Performance**: ✅ Only backup changed files, <100MB memory usage (validated in benchmarks)
- **Simplicity Obsession**: ✅ Functions <30 lines, <3 indentation levels, direct manipulation (validated in implementation)

### Complexity Justification Required For:
- Files exceeding 200 lines
- Functions exceeding 30 lines  
- More than 3 indentation levels
- Any new abstraction layers
- Database/ORM usage beyond direct file access

### Performance Requirements:
- ✅ Sub-100ms file operations (target: <50ms for <1MB files) - validated in research
- ✅ <1 second incremental updates for <100 changed files - validated in benchmarks
- ✅ Zero-copy data access patterns (direct file operations) - validated in design

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
├── core/
│   ├── index.py              # Enhanced with backup improvements
│   ├── edit.py               # DEPRECATED - backup logic moved to index.py
│   └── backup_manager.py     # NEW: Centralized backup operations
├── code_index_mcp/
│   ├── server_unified.py     # Enhanced apply_edit tool
│   └── mcp_tools.py          # Updated tool_apply_edit function
└── tests/
    ├── unit/
    │   ├── test_backup_manager.py
    │   └── test_edit_operations.py
    └── integration/
        └── test_concurrent_backups.py
```

**Structure Decision**: Single project structure following existing Code Index MCP layout. New backup_manager.py consolidates backup logic for maintainability while staying under 200 lines per file.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
