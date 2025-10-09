---
description: "Task list for Apply Edit Backup Directory Fix implementation"
---

# Tasks: Apply Edit Backup Directory Fix

**Input**: Design documents from `/specs/001-apply-edit-edit/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow the plan.md structure

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backup_manager.py file structure in src/core/backup_manager.py
- [ ] T002 [P] Add required imports to backup_manager.py (pathlib, shutil, tempfile, time, threading, hashlib, logging)
- [ ] T003 [P] Create test directory structure: tests/unit/test_backup_manager.py, tests/integration/test_concurrent_backups.py
- [ ] T004 [P] Configure logging for backup operations (errors and warnings only per research findings)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement BackupFile dataclass in src/core/backup_manager.py (from data-model.md)
- [ ] T006 [P] Implement BackupDirectory dataclass in src/core/backup_manager.py (from data-model.md)
- [ ] T007 [P] Implement EditOperation dataclass in src/core/backup_manager.py (from data-model.md)
- [ ] T008 [P] Implement EditStatus and BackupLocation enums in src/core/backup_manager.py
- [ ] T009 Implement atomic_backup function with microsecond timestamps (from research.md)
- [ ] T010 [P] Implement cross-platform path normalization functions (from research.md)
- [ ] T011 [P] Implement concurrent-safe naming strategy (from research.md)
- [ ] T012 Implement error handling hierarchy (permission → temp fallback, disk full → abort) (from research.md)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Reliable Backup Creation (Priority: P1) 🎯 MVP

**Goal**: When a user edits any file through the apply_edit function, the system must successfully create a backup file in the .edit_backup directory without failing due to directory permission or existence issues.

**Independent Test**: Can be fully tested by attempting to edit files in various directory permission scenarios and verifying backup creation succeeds.

### Implementation for User Story 1

- [ ] T013 [US1] Implement create_backup_directory method in src/core/backup_manager.py (auto-create .edit_backup)
- [ ] T014 [US1] Implement handle_permission_errors method in src/core/backup_manager.py (graceful permission handling)
- [ ] T015 [US1] Implement validate_backup_creation method in src/core/backup_manager.py (verify backup success)
- [ ] T016 [US1] Enhance _create_backup method in src/core/index.py to use new backup_manager (replace existing logic)
- [ ] T017 [US1] Update tool_apply_edit function in src/code_index_mcp/mcp_tools.py to handle backup errors gracefully
- [ ] T018 [US1] Add fallback to system temp directory when primary location unavailable (FR-005)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Graceful Backup Failure Handling (Priority: P2)

**Goal**: When backup creation fails due to unavoidable issues (e.g., filesystem read-only), the system should provide clear error messages and optional recovery strategies rather than failing silently.

**Independent Test**: Can be fully tested by simulating backup failure scenarios and verifying appropriate error handling.

### Implementation for User Story 2

- [ ] T019 [US2] Implement clear_error_messages method in src/core/backup_manager.py (user-friendly error messages)
- [ ] T020 [US2] Implement recovery_strategies method in src/core/backup_manager.py (optional recovery options)
- [ ] T021 [US2] Enhance error handling in src/core/index.py _edit_single_file method to use new error messaging
- [ ] T022 [US2] Add error context to tool_apply_edit in src/code_index_mcp/mcp_tools.py (include suggestions)
- [ ] T023 [US2] Implement logging for errors and warnings only (per FR-004 and research findings)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Concurrent Edit Safety (Priority: P3)

**Goal**: When multiple edit operations occur simultaneously, the backup system must handle concurrent access to .edit_backup directory without conflicts or data corruption.

**Independent Test**: Can be fully tested by running concurrent edit operations and verifying backup integrity.

### Implementation for User Story 3

- [ ] T024 [US3] Implement generate_unique_filename method in src/core/backup_manager.py (microsecond timestamps + process ID)
- [ ] T025 [US3] Implement concurrent_safe_backup method in src/core/backup_manager.py (lock-free operations)
- [ ] T026 [US3] Add thread safety to backup operations in src/core/index.py (ensure atomic operations)
- [ ] T027 [US3] Implement backup integrity validation for concurrent scenarios in src/core/backup_manager.py
- [ ] T028 [US3] Add concurrent backup testing utilities in tests/integration/test_concurrent_backups.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T029 [P] Implement cleanup_old_backups method in src/core/backup_manager.py (retain 100 most recent per FR-006)
- [ ] T030 [P] Implement quarantine_corrupted_backups method in src/core/backup_manager.py (per FR-008)
- [ ] T031 [P] Add backup integrity checking in src/core/backup_manager.py (validate checksums)
- [ ] T032 [P] Update quickstart.md with actual implementation examples
- [ ] T033 Code cleanup and refactoring (ensure <200 lines per file, <30 lines per function)
- [ ] T034 [P] Constitutional compliance check: verify files <200 lines, <3 indentation levels
- [ ] T035 [P] Constitutional compliance check: verify functions <30 lines
- [ ] T036 [P] Constitutional compliance check: verify unified interface usage
- [ ] T037 [P] Constitutional compliance check: verify direct data manipulation (no service abstractions)
- [ ] T038 Performance validation: sub-100ms operations, <100MB memory usage
- [ ] T039 [P] Update documentation in src/core/edit.py (mark as deprecated with migration note)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Core implementation before integration
- Models before services
- Services before endpoints
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all setup tasks together:
Task: "Add required imports to backup_manager.py"
Task: "Create test directory structure"
Task: "Configure logging for backup operations"

# Launch all foundational tasks together:
Task: "Implement BackupFile dataclass"
Task: "Implement BackupDirectory dataclass"
Task: "Implement EditOperation dataclass"
Task: "Implement EditStatus and BackupLocation enums"

# Launch User Story 1 implementation:
Task: "Implement create_backup_directory method"
Task: "Implement handle_permission_errors method"
Task: "Implement validate_backup_creation method"
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
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Focus on Linus-style direct data manipulation (no service abstractions)
- Maintain constitutional constraints: <200 lines files, <30 lines functions, <3 indentation levels
- All operations must route through unified interface
- Performance targets: <50ms backup creation for <1MB files, <100MB memory usage