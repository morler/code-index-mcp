# Code Index MCP 语义功能开发计划

## 项目概述

为 Code Index MCP 项目添加语义搜索和语义代码编辑能力，基于现有的 Tree-sitter 架构和服务分层设计，采用渐进式实现策略。

## 架构评估

### 现有优势
- ✅ **数据结构良好**：`SymbolInfo` 模型已有 `called_by` 字段，为语义关系做了准备
- ✅ **策略模式扩展性强**：Tree-sitter 策略架构可以轻松扩展语义解析
- ✅ **服务分层清晰**：可以添加新的语义服务而不破坏现有架构
- ✅ **索引基础扎实**：高性能索引系统支持复杂查询
- ✅ **实时监控**：文件监控确保语义索引的实时性

### 技术路径选择
**方案A：纯 Tree-sitter 方案** 🟢 **推荐**
- 扩展现有 Tree-sitter 策略添加语义分析
- 利用 AST 构建符号依赖图
- 符合现有架构，风险可控

## 开发阶段规划

### 阶段1：基础语义索引 🟢 优先级：高

#### 目标
建立基础的语义关系索引，为后续功能提供数据基础。

#### 技术实现
1. **扩展数据模型**
   ```python
   @dataclass
   class SymbolInfo:
       # 现有字段...
       imports: Optional[List[str]] = None      # 导入的符号
       exports: Optional[List[str]] = None      # 导出的符号
       references: Optional[List[str]] = None   # 引用此符号的位置
       dependencies: Optional[List[str]] = None # 依赖的符号
   ```

2. **增强 Tree-sitter 策略**
   - 扩展 `PythonStrategy`、`JavaScriptStrategy`、`TypeScriptStrategy` 等
   - 提取 import/export 声明
   - 识别函数调用关系
   - 构建类继承关系

3. **符号关系图构建**
   - 在 `UnifiedIndexManager` 中维护符号依赖关系
   - 建立反向索引：符号 → 引用位置
   - 支持增量更新

#### 交付物
- [ ] 扩展的 `SymbolInfo` 模型
- [ ] 增强的 Tree-sitter 策略（Python、JS、TS）
- [ ] 符号关系图数据结构
- [ ] 单元测试（覆盖率 > 90%）

#### 时间估计
2-3 周

---

### 阶段2：语义搜索工具 🟢 优先级：高

#### 目标
提供基础的语义搜索功能，支持符号查找和引用分析。

#### 技术实现
1. **新增语义搜索服务**
   ```python
   class SemanticSearchService(BaseService):
       def find_references(self, symbol_name: str) -> List[SymbolInfo]:
           """查找符号的所有引用"""

       def find_definition(self, symbol_name: str) -> Optional[SymbolInfo]:
           """查找符号定义"""

       def find_callers(self, function_name: str) -> List[SymbolInfo]:
           """查找调用特定函数的符号"""

       def find_implementations(self, interface_name: str) -> List[SymbolInfo]:
           """查找接口实现（适用于 TypeScript/Java）"""

       def find_symbol_hierarchy(self, class_name: str) -> Dict[str, Any]:
           """查找类继承层次结构"""
   ```

2. **添加 MCP 工具**
   ```python
   @mcp.tool()
   def find_references(ctx: Context, symbol_name: str) -> Dict[str, Any]:
       """查找符号的所有引用位置"""

   @mcp.tool()
   def find_definition(ctx: Context, symbol_name: str) -> Dict[str, Any]:
       """查找符号定义位置"""

   @mcp.tool()
   def find_callers(ctx: Context, function_name: str) -> Dict[str, Any]:
       """查找调用指定函数的所有位置"""

   @mcp.tool()
   def semantic_search(ctx: Context, query: str, search_type: str) -> Dict[str, Any]:
       """统一语义搜索接口"""
   ```

3. **搜索算法优化**
   - 基于图遍历的符号查找
   - 支持模糊匹配（符号名称相似性）
   - 结果排序和过滤

#### 交付物
- [ ] `SemanticSearchService` 服务类
- [ ] 4个 MCP 语义搜索工具
- [ ] 搜索算法实现
- [ ] 集成测试
- [ ] 性能基准测试

#### 时间估计
2-3 周

---

### 阶段3：基础代码编辑 🟡 优先级：中

#### 目标
提供安全的语义代码编辑功能，重点是符号重命名。

#### 技术实现
1. **语义编辑服务**
   ```python
   class SemanticEditService(BaseService):
       def rename_symbol(self, old_name: str, new_name: str,
                        scope: str = "project") -> EditResult:
           """安全重命名符号，更新所有引用"""

       def add_import(self, file_path: str, module_name: str,
                     symbol_name: str) -> EditResult:
           """智能添加导入语句"""

       def remove_unused_imports(self, file_path: str) -> EditResult:
           """移除未使用的导入"""

       def organize_imports(self, file_path: str) -> EditResult:
           """整理导入语句顺序"""
   ```

2. **编辑操作数据模型**
   ```python
   @dataclass
   class EditResult:
       success: bool
       modified_files: List[str]
       changes_preview: Dict[str, str]  # file_path -> diff
       rollback_info: Optional[str]
       error_message: Optional[str] = None
   ```

3. **安全机制**
   - 编辑前验证：确保符号存在且可重命名
   - 冲突检测：避免与现有符号冲突
   - 原子操作：要么全部成功，要么全部回滚
   - 备份机制：支持操作撤销

#### 交付物
- [ ] `SemanticEditService` 服务类
- [ ] `EditResult` 数据模型
- [ ] 符号重命名功能
- [ ] 导入管理功能
- [ ] 安全验证机制
- [ ] 回滚功能

#### 时间估计
3-4 周

---

### 阶段4：高级语义功能 🟡 优先级：低

#### 目标
提供更复杂的语义操作，如函数提取、代码重构等。

#### 功能列表
1. **代码重构**
   - 提取函数 (Extract Function)
   - 提取变量 (Extract Variable)
   - 内联函数 (Inline Function)
   - 移动方法 (Move Method)

2. **依赖分析**
   - 循环依赖检测
   - 未使用代码检测
   - 影响范围分析

3. **代码生成**
   - 基于接口生成实现
   - 生成测试样板代码
   - 生成文档注释

#### 时间估计
4-6 周

---

## 风险评估

### 🟢 低风险项目
- **数据模型扩展**：现有架构支持良好
- **基础语义搜索**：基于现有索引系统
- **符号重命名**：相对简单的编辑操作

### 🟡 中等风险项目
- **复杂代码编辑**：需要确保文件一致性
- **多语言支持**：Tree-sitter 解析器质量不一
- **内存占用**：语义关系图会增加内存使用

### 🔴 高风险项目
- **复杂重构操作**：需要深度语义理解
- **跨文件事务编辑**：操作复杂度高
- **LSP 集成**：会显著增加系统复杂度

## 技术约束

### 必须遵循的原则
1. **Never Break Userspace**：保持现有 API 向后兼容
2. **Good Taste**：避免特殊情况，简化数据结构
3. **渐进式实现**：每个阶段都应该是可用的独立功能
4. **性能优先**：语义功能不能显著降低搜索性能

### 技术选择
- **禁止引入 LSP 依赖**：避免增加系统复杂度
- **优先扩展 Tree-sitter**：利用现有解析架构
- **保持索引高性能**：语义索引采用增量更新

## 测试策略

### 单元测试
- 每个服务类测试覆盖率 > 90%
- 重点测试语义关系的正确性
- 边界条件和错误处理

### 集成测试
- 多语言项目的语义搜索
- 大型项目的性能测试
- 文件变更的增量更新

### 性能基准
- 索引构建时间：不超过现有性能的 150%
- 搜索响应时间：< 100ms (中型项目)
- 内存占用：不超过现有使用的 200%

## 里程碑

### Milestone 1: 基础语义索引 (Week 3)
- [ ] 扩展数据模型
- [ ] 增强 Tree-sitter 策略
- [ ] 基础测试通过

### Milestone 2: 语义搜索工具 (Week 6)
- [ ] 4个语义搜索 MCP 工具
- [ ] 集成测试通过
- [ ] 性能基准达标

### Milestone 3: 基础代码编辑 (Week 10)
- [ ] 符号重命名功能
- [ ] 导入管理功能
- [ ] 安全机制完善

### Milestone 4: 功能完善 (Week 16)
- [ ] 高级语义功能
- [ ] 完整文档
- [ ] 发布 v3.0

## 依赖和资源

### 新增依赖
```python
# 可能需要的新依赖（评估中）
dependencies = [
    # 现有依赖保持不变
    "networkx>=3.0",  # 用于符号关系图（可选）
]
```

### 开发资源
- 1 名主要开发者
- 预计总工作量：10-16 周
- 代码审查：每个 PR 必须经过审查

---

**Note**: 本计划遵循 Linus Torvalds 的"good taste"原则：简化数据结构，消除特殊情况，优先解决真实存在的问题。每个阶段都应该是可独立使用的功能增强，而不是"大重写"。

---

**计划制定时间**: 2025-01-20
**预计完成时间**: 2025-05-20 (16 周)
**质量负责人**: 开发团队
**审查周期**: 每两周进度审查