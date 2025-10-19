## Why
项目存在严重的架构过度复杂化问题：重复的核心模块、1011行的单文件、40+个重复测试文件，违背了Linus式"Good Taste"原则。

## What Changes
- **删除重复模块**: 移除 `src/code_index_mcp/core/` 重复实现
- **拆分大文件**: 将1011行的 `builder.py` 重构为3个<200行的文件  
- **合并测试**: 删除重复测试，保留5个核心测试
- **统一接口**: 用单一数据流替代30+个专门工具函数

## Impact
- Affected specs: core-indexing, code-analysis, testing
- Affected code: src/core/, src/code_index_mcp/core/, tests/
- **BREAKING**: 重构核心数据结构和API接口