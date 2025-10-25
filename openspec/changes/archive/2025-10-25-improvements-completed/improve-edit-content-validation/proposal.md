# Fix Edit Content Validation Issues

## Why
编辑操作经常因空白字符差异导致验证失败，当前匹配算法过于严格，缺乏容错性。

## What Changes
- **改进空白字符处理**: 统一换行符和制表符标准化
- **简化匹配逻辑**: 精确匹配失败时尝试标准化匹配
- **优化错误信息**: 提供基本的匹配失败详情

## Impact
- **Affected specs**: edit-operations  
- **Affected code**: `src/core/edit_operations.py`
- **Reliability**: 减少因空白字符导致的编辑失败