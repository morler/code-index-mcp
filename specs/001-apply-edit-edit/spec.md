# Feature Specification: Apply Edit Backup Directory Fix

**Feature Branch**: `001-apply-edit-edit`  
**Created**: 2025-10-09  
**Status**: Draft  
**Input**: User description: "解决apply_edit编辑代码时，.edit_backup目录写入问题"

## Clarifications

### Session 2025-10-09

- Q: 当主备份位置不可用时，系统应该提供哪些具体的回退选项？ → A: 使用临时目录（如系统临时目录）作为备用备份位置
- Q: 当磁盘空间不足导致备份创建失败时，系统应该采取什么具体处理机制？ → A: 中止编辑操作并返回明确的磁盘空间不足错误信息
- Q: 当检测到备份文件损坏或无法读取时，系统应该如何处理？ → A: 将损坏的备份移动到隔离目录并创建新备份
- Q: 当多个编辑操作同时尝试创建同一文件的备份时，系统应该如何解决并发冲突？ → A: 使用微秒级时间戳确保每个备份文件名唯一，无锁操作
- Q: 备份操作应该记录什么级别的详细日志信息用于故障排除？ → A: 仅记录错误和警告，正常操作不记录日志
- Q: 备份文件的元数据应该包含哪些具体属性？ → A: 最小元数据：仅时间戳、原始路径、操作ID
- Q: 系统依赖哪些外部服务或API来实现备份功能？ → A: 仅依赖本地文件系统，无外部服务依赖
- Q: 除了已列出的边缘情况，还需要考虑哪些其他失败场景？ → A: 仅考虑已列出的场景即可，避免过度复杂化
- Q: 当备份创建失败时，用户应该如何确认是否继续编辑操作？ → A: 自动中止操作，显示错误信息，用户需重新发起编辑
- Q: 保留100个最近备份文件的清理算法应该如何工作？ → A: 按创建时间戳排序，删除最旧的文件，保留最新的100个

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reliable Backup Creation (Priority: P1)

When a user edits any file through the apply_edit function, the system must successfully create a backup file in the .edit_backup directory without failing due to directory permission or existence issues.

**Why this priority**: Backup creation is critical for data safety and edit operation reliability. Failure to create backups should not prevent users from editing files.

**Independent Test**: Can be fully tested by attempting to edit files in various directory permission scenarios and verifying backup creation succeeds.

**Acceptance Scenarios**:

1. **Given** a file exists in a writable directory, **When** apply_edit is called, **Then** a backup file is created in .edit_backup directory and the edit succeeds
2. **Given** .edit_backup directory does not exist, **When** apply_edit is called, **Then** the directory is created automatically and backup succeeds
3. **Given** .edit_backup directory has restrictive permissions, **When** apply_edit is called, **Then** the system attempts to fix permissions or creates backup in alternative location

---

### User Story 2 - Graceful Backup Failure Handling (Priority: P2)

When backup creation fails due to unavoidable issues (e.g., filesystem read-only), the system should provide clear error messages and optional recovery strategies rather than failing silently.

**Why this priority**: Users need to understand why edits fail and what they can do to resolve the issue.

**Independent Test**: Can be fully tested by simulating backup failure scenarios and verifying appropriate error handling.

**Acceptance Scenarios**:

1. **Given** backup creation fails due to permissions, **When** apply_edit is called, **Then** a clear error message explains the issue and suggests solutions
2. **Given** backup creation fails, **When** apply_edit is called, **Then** the operation aborts automatically with clear error message requiring user to restart the edit process

---

### User Story 3 - Concurrent Edit Safety (Priority: P3)

When multiple edit operations occur simultaneously, the backup system must handle concurrent access to .edit_backup directory without conflicts or data corruption.

**Why this priority**: Prevents race conditions in multi-threaded or multi-process environments.

**Independent Test**: Can be fully tested by running concurrent edit operations and verifying backup integrity.

**Acceptance Scenarios**:

1. **Given** multiple simultaneous edit operations, **When** backups are created, **Then** each backup has a unique filename and no conflicts occur
2. **Given** concurrent access to .edit_backup directory, **When** operations complete, **Then** all backups are valid and correspond to correct original files

---

### Edge Cases

- **Disk Full**: System aborts edit operation and returns clear disk space error message
- **Long File Paths**: System truncates backup filenames while maintaining uniqueness
- **Directory Deletion**: System recreates .edit_backup directory automatically and continues operation

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create .edit_backup directory automatically if it doesn't exist
- **FR-002**: System MUST handle permission errors gracefully when creating backup directory
- **FR-003**: System MUST generate unique backup filenames using microsecond timestamps to avoid conflicts in concurrent scenarios without locking
- **FR-004**: System MUST provide clear error messages when backup creation fails, logging only errors and warnings
- **FR-005**: System MUST offer fallback options when primary backup location is unavailable, using system temporary directory as backup location
- **FR-006**: System MUST clean up old backup files to prevent disk space issues, retaining only the 100 most recent backups by creation timestamp
- **FR-007**: System MUST validate backup creation success before proceeding with edit operation
- **FR-008**: System MUST quarantine corrupted backup files and attempt backup recreation

### Code Index MCP Constitutional Constraints

- **FR-009**: System MUST use direct data manipulation - no service abstractions or wrapper classes
- **FR-010**: All operations MUST route through unified interface - no specialized tool functions
- **FR-011**: Symbol operations MUST use SCIP protocol with tree-sitter parsing for core languages
- **FR-012**: System MUST process only changed files for incremental updates
- **FR-013**: Files MUST stay under 200 lines with maximum 3 indentation levels
- **FR-014**: Functions MUST be under 30 lines without explicit justification
- **FR-015**: System MUST maintain sub-100ms response times for file operations
- **FR-016**: Memory usage MUST stay under 100MB for typical projects

### Key Entities *(include if feature involves data)*

- **Backup File**: Represents a snapshot of original file content before editing, with minimal metadata including timestamp, original path, and operation ID
- **Backup Directory**: Centralized .edit_backup directory containing all backup files with consistent naming scheme
- **Edit Operation**: Represents a file modification request with content validation and rollback capabilities

### Integration & External Dependencies

- **Local Filesystem Only**: System depends solely on local filesystem operations without external service dependencies

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 99.9% of edit operations successfully create backups without user intervention
- **SC-002**: Backup creation completes within 50ms for files under 1MB
- **SC-003**: System handles 100 concurrent backup operations without conflicts
- **SC-004**: User-reported edit failures due to backup issues decrease by 95%
- **SC-005**: Backup directory size stays under 1GB with automatic cleanup