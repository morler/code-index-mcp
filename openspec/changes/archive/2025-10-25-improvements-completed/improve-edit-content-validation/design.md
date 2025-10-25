## Context
当前edit_operations.py中的内容验证过于严格，空白字符差异（如制表符vs空格）导致合法编辑失败。

## Goals / Non-Goals
- Goals: 修复空白字符匹配问题，提高编辑成功率
- Non-Goals: 重构架构、添加复杂特性、改变接口

## Decisions
- Decision: 简化匹配逻辑为两步：精确匹配→标准化匹配
- Rationale: 解决80%的问题，保持代码简单

## Migration Plan
1. 改进normalize_whitespace函数
2. 简化find_content_match逻辑
3. 更新测试用例
4. 验证向后兼容性