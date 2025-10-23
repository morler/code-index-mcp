## Context
当前编辑操作在 `edit_operations.py:72-99` 的内容验证逻辑存在三个具体问题：
1. 空白字符处理：`strip()` 过于激进，丢失重要的格式信息
2. 部分匹配缺陷：删除操作可能误删包含目标字符串的其他行
3. 错误信息模糊：只返回"cannot find old_content"，缺乏具体指导

## Goals / Non-Goals
- Goals: 修复上述三个具体问题，提高编辑成功率
- Non-Goals: 不引入新算法、不改变API、不影响其他模块

## Decisions
- Decision: 最小化修改现有逻辑，专注修复已知问题
  - 理由：降低风险，保持稳定性
  - 替代方案：重写验证逻辑（风险过高）

## Implementation Approach
1. 保留现有的三层验证结构（精确→部分→失败）
2. 修复每层的具体缺陷
3. 改进错误消息的具体性

## Testing Strategy
- 专注回归测试，确保不破坏现有功能
- 添加针对已知问题的边界测试用例