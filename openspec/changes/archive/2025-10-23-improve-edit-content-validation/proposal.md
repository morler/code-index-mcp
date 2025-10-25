## Why
当前编辑操作在内容验证时过于严格，简单的字符串匹配导致常见的编辑场景失败，如空白字符差异、部分内容替换等。

## What Changes
- **修复空白字符处理**：标准化空白字符和换行符的比较逻辑
- **改进部分匹配**：优化现有的部分内容替换算法，避免误删除
- **增强错误信息**：提供具体的匹配失败原因，而非通用错误消息

## Impact
- Affected specs: edit-operations  
- Affected code: src/core/edit_operations.py