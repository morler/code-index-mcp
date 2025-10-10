---
description: "Task list for removing apply_edit backup functionality"
---

# Tasks: 取消apply_edit备份功能

**Input**: Design documents from `/specs/002-apply-edit/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), data-model.md, contracts/edit-api.yaml

**Tests**: Tests are included as this is a critical core functionality change affecting data safety.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow the existing Code Index MCP structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create feature branch `002-apply-edit` from main
- [ ] T002 [P] Verify existing test infrastructure in tests/
- [ ] T003 [P] Setup performance baseline measurement for current apply_edit operations
- [ ] T004 [P] Document current backup behavior in tests/test_backup_baseline.py
- [ ] T005 [P] Setup memory usage monitoring for comparison metrics

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Analyze current apply_edit implementation in src/code_index_mcp/core/edit.py
- [ ] T007 Analyze current backup implementation in src/code_index_mcp/core/backup.py
- [ ] T008 [P] Create MemoryBackupManager data structure in src/code_index_mcp/core/memory_backup.py
- [ ] T009 [P] Create FileState data structure in src/code_index_mcp/core/file_state.py
- [ ] T010 [P] Create EditOperation data structure in src/code_index_mcp/core/edit_operation.py
- [ ] T011 Implement file locking mechanism in src/code_index_mcp/core/file_lock.py
- [ ] T012 [P] Configure memory monitoring and LRU eviction system with 50MB limit in src/code_index_mcp/core/memory_monitor.py
- [ ] T012-A [P] Add file size validation logic (10MB limit) in src/code_index_mcp/core/operations.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 禁用文件编辑备份 (Priority: P1) 🎯 MVP

**Goal**: 用户在使用apply_edit工具编辑文件时，系统不再自动创建备份文件，直接进行编辑操作

**Independent Test**: 可以通过编辑文件并验证没有备份文件生成来独立测试此功能

### Tests for User Story 1 ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Contract test for /edit endpoint in tests/contract/test_edit_api.py
- [ ] T014 [P] [US1] Integration test for edit without backup creation in tests/integration/test_edit_no_backup.py
- [ ] T015 [P] [US1] Performance test comparing edit times before/after in tests/performance/test_edit_performance.py

### Implementation for User Story 1

- [ ] T016 [P] [US1] Modify EditOperation model in src/code_index_mcp/core/edit_operation.py
- [ ] T017 [P] [US1] Modify MemoryBackupManager in src/code_index_mcp/core/memory_backup.py
- [ ] T018 [US1] Remove backup file creation logic from src/code_index_mcp/core/edit.py
- [ ] T018-A [US1] Remove existing disk backup files and cleanup backup directories in src/code_index_mcp/core/backup.py
- [ ] T018-B [US1] Update backup.py to remove all disk-related backup functions and constants
- [ ] T019 [US1] Update apply_edit tool in src/code_index_mcp/server_unified.py to use memory backup
- [ ] T020 [US1] Update mcp_tools.py tool_apply_edit function for memory backup
- [ ] T021 [US1] Add validation for 10MB file size limits in src/code_index_mcp/core/operations.py
- [ ] T022 [US1] Add memory usage monitoring in src/code_index_mcp/core/memory_monitor.py
- [ ] T023 [US1] Implement edit operation logging without backup content in src/code_index_mcp/core/edit_logger.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 保持错误回滚机制 (Priority: P2)

**Goal**: 虽然取消了备份功能，但系统在编辑失败时仍能正确回滚到原始状态

**Independent Test**: 可以通过模拟编辑失败场景来验证回滚机制是否正常工作

### Tests for User Story 2 ⚠️

- [ ] T024 [P] [US2] Contract test for edit failure rollback in tests/contract/test_edit_rollback.py
- [ ] T025 [P] [US2] Integration test for memory-based rollback in tests/integration/test_memory_rollback.py
- [ ] T026 [P] [US2] Concurrent edit failure test in tests/integration/test_concurrent_rollback.py

### Implementation for User Story 2

- [ ] T027 [P] [US2] Implement rollback mechanism in MemoryBackupManager in src/code_index_mcp/core/memory_backup.py
- [ ] T028 [US2] Update FileState for rollback validation in src/code_index_mcp/core/file_state.py
- [ ] T029 [US2] Modify edit operations to support rollback in src/code_index_mcp/core/edit.py
- [ ] T030 [US2] Add crash recovery mechanism in src/code_index_mcp/core/backup.py
- [ ] T031 [US2] Update error handling in src/code_index_mcp/core/operations.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T032 [P] Update API documentation in docs/api/
- [ ] T033 [P] Update user documentation in README.md
- [ ] T034 Code cleanup and refactoring in src/code_index_mcp/core/
- [ ] T035 Performance optimization across all edit operations
- [ ] T036 [P] Additional unit tests in tests/unit/test_memory_backup.py
- [ ] T037 [P] Additional unit tests in tests/unit/test_file_lock.py
- [ ] T038 Security hardening for memory operations
- [ ] T039 Run quickstart.md validation
- [ ] T040 Constitutional compliance check: verify files <200 lines, <3 indentation levels
- [ ] T041 Constitutional compliance check: verify functions <30 lines
- [ ] T042 Constitutional compliance check: verify unified interface usage
- [ ] T043 Constitutional compliance check: verify SCIP protocol usage for symbols
- [ ] T044 Performance validation: sub-100ms operations, <100MB memory usage
- [ ] T045 Memory usage validation: verify <50MB limit for backup cache
- [ ] T046 Final integration tests across all user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-4)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 memory backup infrastructure

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, User Story 1 can start
- User Story 2 can start after User Story 1 memory infrastructure is ready
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for /edit endpoint in tests/contract/test_edit_api.py"
Task: "Integration test for edit without backup creation in tests/integration/test_edit_no_backup.py"
Task: "Performance test comparing edit times before/after in tests/performance/test_edit_performance.py"

# Launch all models for User Story 1 together:
Task: "Modify EditOperation model in src/code_index_mcp/core/edit_operation.py"
Task: "Modify MemoryBackupManager in src/code_index_mcp/core/memory_backup.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Performance Targets

- **Response Time**: 20% reduction compared to current disk backup
- **Memory Usage**: <50MB for backup cache
- **Disk Space**: 50% reduction (no backup files)
- **File Size Limit**: 10MB maximum for memory backup
- **Concurrent Operations**: Support multiple simultaneous edits

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Monitor memory usage throughout development
- Performance testing is critical for this feature
- File locking mechanism must be thoroughly tested
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: memory leaks, file corruption, performance regressions