# Feature Specification: 取消apply_edit备份功能

**Feature Branch**: `002-apply-edit`  
**Created**: 2025-01-09  
**Status**: Draft  
**Input**: User description: "取消项目apply_edit工具编辑文件时的备份功能"

## Clarifications

### Session 2025-01-09

- Q: 错误回滚机制实现方式 → A: 内存中保留原始文件内容直到编辑成功完成
- Q: 性能基准定义 → A: 基于当前带备份功能的apply_edit平均响应时间
- Q: 并发编辑处理策略 → A: 实现文件锁定机制，排队处理编辑请求
- Q: 备份功能配置灵活性 → A: 完全移除备份功能，无配置选项
- Q: 文件大小限制策略 → A: 超过内存限制时拒绝编辑操作

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 禁用文件编辑备份 (Priority: P1)

用户在使用apply_edit工具编辑文件时，系统不再自动创建备份文件，直接进行编辑操作。

**Why this priority**: 这是核心功能需求，用户明确要求取消备份机制以简化操作流程。

**Independent Test**: 可以通过编辑文件并验证没有备份文件生成来独立测试此功能。

**Acceptance Scenarios**:

1. **Given** 用户使用apply_edit工具编辑文件, **When** 编辑操作完成, **Then** 系统不创建任何备份文件
2. **Given** 用户多次编辑同一文件, **When** 每次编辑完成, **Then** 系统都不创建备份文件
3. **Given** 编辑操作失败, **When** 错误发生, **Then** 原文件保持不变且无备份文件生成

---

### User Story 2 - 保持错误回滚机制 (Priority: P2)

虽然取消了备份功能，但系统在编辑失败时仍能正确回滚到原始状态。

**Why this priority**: 确保数据安全性，防止编辑失败导致文件损坏。

**Independent Test**: 可以通过模拟编辑失败场景来验证回滚机制是否正常工作。

**Acceptance Scenarios**:

1. **Given** apply_edit操作过程中发生错误, **When** 操作失败, **Then** 原文件内容完全恢复
2. **Given** 系统崩溃或异常中断, **When** 重启后检查文件, **Then** 文件处于编辑前状态

---

### Edge Cases

- **用户手动中断**: 编辑操作被用户中断时，内存中的原始内容自动恢复，文件保持编辑前状态
- **磁盘空间不足**: 由于无备份文件创建，磁盘空间不足不影响编辑操作，仅影响最终文件写入
- **网络文件系统**: 通过文件锁定机制确保网络文件系统上的编辑操作原子性，失败时完整回滚
- **并发编辑冲突**: 多进程/多用户同时编辑同一文件时，系统通过文件锁定机制排队处理，确保数据一致性
- **大文件处理**: 超过10MB文件大小或50MB内存限制的编辑操作将被拒绝，返回明确错误信息

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须在apply_edit操作时不创建磁盘备份文件，保留内存备份机制用于错误回滚（完全移除磁盘备份，无配置选项）
- **FR-002**: 系统必须在编辑失败时能够回滚到原始文件状态（通过MemoryBackupManager在内存中保留原始内容实现，由memory_monitor.py负责监控50MB内存限制，operations.py负责检查10MB文件大小限制，超限时拒绝操作）  
- **FR-003**: 用户必须能够正常使用apply_edit进行文件编辑
- **FR-004**: 系统必须记录编辑操作但不存储备份内容
- **FR-005**: 系统必须在编辑完成后清理所有临时数据

### Code Index MCP Constitutional Constraints

详细宪法约束请参考 plan.md 中的 Constitution Check 部分，本规格遵循所有宪法要求。

### Key Entities

- **EditOperation**: 表示文件编辑操作，包含文件路径、编辑内容和操作状态
- **MemoryBackupManager**: 内存备份管理器，负责LRU缓存策略和内存中的原始内容保留，完全替代磁盘备份功能
- **FileState**: 文件状态跟踪器，用于回滚操作时验证文件完整性

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: apply_edit操作响应时间达到sub-100ms目标（基于当前150ms基准，实现33%+性能提升，基于当前带备份功能的平均响应时间基准测试）
- **SC-002**: 磁盘空间使用量减少50%，每个编辑操作节省原文件大小的存储空间（无备份文件生成）
- **SC-003**: 100%的编辑失败场景能正确回滚到原始状态
- **SC-004**: 用户编辑操作完成率保持在99%以上（失败场景包括：内存不足超过50MB限制、文件大小超过10MB、文件锁定冲突、磁盘空间不足、权限错误）