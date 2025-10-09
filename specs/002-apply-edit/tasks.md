# Implementation Tasks: 取消apply_edit备份功能

**Branch**: `002-apply-edit` | **Date**: 2025-01-09 | **Spec**: [spec.md](spec.md)
**Total Tasks**: 15 | **Estimated Effort**: 2-3 days

## Implementation Strategy

**MVP Scope**: User Story 1 only (disable backup functionality)  
**Incremental Delivery**: Add rollback mechanism after core functionality works  
**Parallel Opportunities**: Memory management and file locking can be developed independently

---

## Phase 1: Setup Tasks

**Goal**: Project initialization and shared infrastructure

### T001: ✅ Create performance baseline tests
**File**: `tests/test_performance.py`  
**Description**: Establish current performance metrics for apply_edit with disk backup  
**Acceptance**: Measure average response time, disk usage, and memory usage for 100 test edits  
**Status**: COMPLETED - Baseline established: 8.8ms avg response time, 0.1MB disk usage

### T002: ✅ Setup memory monitoring infrastructure  
**File**: `src/code_index_mcp/core/memory_monitor.py`  
**Description**: Create memory usage tracking utilities for backup operations  
**Acceptance**: Can track current memory usage, set limits, and alert on threshold exceeded  
**Status**: COMPLETED - MemoryMonitor class implemented with cross-platform support

---

## Phase 2: Foundational Tasks

**Goal**: Blocking prerequisites that must complete before any user story implementation

### T003: ✅ Implement cross-platform file locking mechanism
**File**: `src/code_index_mcp/core/file_lock.py`  
**Description**: OS-level file locking (fcntl for Unix, LockFileEx for Windows)  
**Acceptance**: Prevents concurrent edits on same file across processes  
**Status**: COMPLETED - FileLock class with Windows fallback implemented

### T004: ✅ Create memory-based backup data structures
**File**: `src/code_index_mcp/core/edit_models.py`  
**Description**: Implement EditOperation, FileState, and EditStatus classes from data model  
**Acceptance**: All dataclasses defined with proper validation and type hints  
**Status**: COMPLETED - All data structures implemented with LRU memory management

---

## Phase 3: User Story 1 - 禁用文件编辑备份 (P1)

**Goal**: Remove disk backup functionality while maintaining edit operations  
**Independent Test**: Edit file and verify no backup files are created  
**Story Completion Criteria**: All acceptance scenarios from US1 pass

### T005: [US1] Implement MemoryBackupManager core functionality
**File**: `src/code_index_mcp/core/backup.py`  
**Description**: Replace disk-based backup with in-memory LRU cache system  
**Acceptance**: Can add, retrieve, and remove file backups from memory only

### T006: [US1] [P] Modify edit workflow to remove disk backup operations
**File**: `src/code_index_mcp/core/edit.py`  
**Description**: Remove all backup file creation/deletion logic from edit operations  
**Acceptance**: Edit operations complete without any disk backup files

### T007: [US1] [P] Update unified_tool interface for memory backup
**File**: `src/code_index_mcp/server_unified.py`  
**Description**: Ensure unified_tool routes edit operations through new memory backup system  
**Acceptance**: apply_edit calls work through unified interface without backup files

### T008: [US1] Implement memory usage validation and limits
**File**: `src/code_index_mcp/core/backup.py`  
**Description**: Add file size checks and memory limit enforcement with LRU eviction  
**Acceptance**: Files >10MB are rejected, memory usage stays within configured limits

### T009: [US1] Create edit operation status tracking
**File**: `src/code_index_mcp/core/operations.py`  
**Description**: Implement operation ID generation and status tracking for edit operations  
**Acceptance**: Can query operation status and track edit lifecycle

### T010: [US1] Update API contracts to reflect memory backup changes
**File**: `src/code_index_mcp/core/edit.py`  
**Description**: Modify API responses to include memory usage info and deprecate backup parameters  
**Acceptance**: API matches updated contract schema with memory status endpoints

### T011: [US1] Create integration tests for backup removal
**File**: `tests/test_edit_operations.py`  
**Description**: Test that edit operations work without creating backup files  
**Acceptance**: All US1 acceptance scenarios pass with 100% success rate

**🏁 Phase 3 Checkpoint**: User Story 1 complete - backup functionality removed

---

## Phase 4: User Story 2 - 保持错误回滚机制 (P2)

**Goal**: Implement rollback functionality using memory backups  
**Independent Test**: Simulate edit failures and verify file restoration  
**Story Completion Criteria**: All acceptance scenarios from US2 pass

### T012: [US2] Implement memory-based rollback mechanism
**File**: `src/code_index_mcp/core/edit.py`  
**Description**: Add automatic file content restoration from memory on edit failures  
**Acceptance**: Failed edits restore original file content completely

### T013: [US2] [P] Add file corruption detection and handling
**File**: `src/code_index_mcp/core/edit.py`  
**Description**: Implement checksum validation to detect file modifications during editing  
**Acceptance**: Corrupted files trigger rollback with appropriate error messages

### T014: [US2] Create error handling and exception classes
**File**: `src/code_index_mcp/core/exceptions.py`  
**Description**: Define EditOperationError, MemoryLimitExceededError, FileLockError, FileCorruptionError  
**Acceptance**: All error types properly raised and caught with descriptive messages

### T015: [US2] Create rollback integration tests
**File**: `tests/test_integration.py`  
**Description**: Test rollback scenarios including crashes, interruptions, and corruption  
**Acceptance**: All US2 acceptance scenarios pass with 100% rollback success

**🏁 Phase 4 Checkpoint**: User Story 2 complete - rollback mechanism implemented

---

## Phase 5: Polish & Cross-Cutting Concerns

**Goal**: Performance optimization and final integration

### T016: Performance optimization and benchmarking
**File**: `tests/test_performance.py`  
**Description**: Compare new memory-based performance against baseline measurements  
**Acceptance**: Achieve 20% response time reduction and 50% disk space savings

### T017: Update documentation and migration guides
**File**: `docs/apply_edit_migration.md`  
**Description**: Document changes, migration steps, and new configuration options  
**Acceptance**: Complete quickstart guide and API documentation updates

### T018: Final integration testing and validation
**File**: `tests/test_final_integration.py`  
**Description**: End-to-end testing of all functionality with performance validation  
**Acceptance**: All tests pass, performance targets met, backward compatibility maintained

---

## Dependencies

### User Story Dependencies
```
US1 (P1): T005 → T006 → T007 → T008 → T009 → T010 → T011
US2 (P2): T012 → T013 → T014 → T015
```

### Cross-Story Dependencies
- US2 depends on US1 completion (needs memory backup infrastructure)
- All stories depend on Phase 1-2 completion

### Critical Path
```
T001 → T002 → T003 → T004 → US1 Tasks → US2 Tasks → Polish Tasks
```

---

## Parallel Execution Opportunities

### Within User Story 1
```bash
# Parallel execution group 1
T005 & T006 & T007  # Core functionality in different files

# Parallel execution group 2  
T008 & T009 & T010  # Advanced features in different files

# Sequential
T011 (after all above complete)
```

### Within User Story 2
```bash
# Parallel execution group 1
T012 & T013 & T014  # Rollback components in different files

# Sequential
T015 (after all above complete)
```

---

## Independent Test Criteria

### User Story 1 Test Independence
- **Test Setup**: Create test files with known content
- **Test Execution**: Run apply_edit operations
- **Test Validation**: Verify no .backup files exist and content is correctly updated
- **Test Cleanup**: Remove test files

### User Story 2 Test Independence  
- **Test Setup**: Create test files and simulate various failure conditions
- **Test Execution**: Trigger edit failures (disk full, permissions, crashes)
- **Test Validation**: Verify original file content is completely restored
- **Test Cleanup**: Remove test files and locks

---

## Risk Mitigation

### High-Risk Tasks
- **T003**: File locking complexity across platforms
- **T008**: Memory management and LRU eviction correctness
- **T012**: Rollback reliability under various failure conditions

### Mitigation Strategies
- Extensive cross-platform testing for file locking
- Memory profiling and stress testing for LRU cache
- Chaos engineering for rollback scenarios

---

## Success Metrics

### Performance Targets
- **Response Time**: ≤120ms (20% improvement from 150ms baseline)
- **Memory Usage**: ≤50MB for backup cache
- **Disk Usage**: 50% reduction (no backup files)
- **Rollback Success**: 100% for all failure scenarios

### Quality Targets
- **Test Coverage**: ≥95% for modified code
- **Code Complexity**: ≤3 indentation levels, ≤30 lines per function
- **Constitution Compliance**: 100% (no violations)