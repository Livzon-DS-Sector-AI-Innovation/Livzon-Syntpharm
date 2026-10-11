# 设备批量导入 v4 实施清单

**创建日期**: 2026-09-07  
**关联ADR**: [ADR 002](../../backend/docs/adr/002-equipment-import-v4-incremental-update.md)  
**状态**: Design Complete → Ready for Implementation

---

## ✅ Phase 1: 数据库迁移

### 1.1 添加 is_fixed_asset 字段
- [ ] 在 `equipment.equipments` 表添加 `is_fixed_asset BOOLEAN NOT NULL DEFAULT true`
- [ ] 为现有 `asset_no IS NULL` 的记录设置 `is_fixed_asset = false`
- [ ] 验证：`SELECT COUNT(*) FROM equipment.equipments WHERE is_fixed_asset = false`

### 1.2 添加 equipment_tag 唯一索引
- [ ] 创建部分唯一索引：`uq_equipments_equipment_tag`
- [ ] 条件：`WHERE equipment_tag IS NOT NULL AND is_deleted = false`
- [ ] 验证：尝试插入重复位号，确认约束生效

### 1.3 创建审计日志表
- [ ] 创建 `equipment.import_audit_logs` 表
- [ ] 字段：batch_id, operation_type, match_strategy, asset_no, equipment_tag, department_id, location_text, changes (JSON), warnings (JSON), error_message, row_index, created_by, created_at
- [ ] 为 `batch_id` 和 `created_at` 添加索引
- [ ] 验证：插入测试记录

### 1.4 创建归档清理任务
- [ ] 创建定时任务：每月执行一次
- [ ] 逻辑：将6个月前的审计日志移动到归档表或冷存储
- [ ] 验证：手动触发测试

---

## ✅ Phase 2: 后端实现

### 2.1 模型更新
- [ ] 在 `models/equipment.py` 添加 `is_fixed_asset: Mapped[bool]`
- [ ] 创建 `models/import_audit.py`（ImportAuditLog模型）
- [ ] 验证：模型可正常导入

### 2.2 核心匹配逻辑
- [ ] 实现 `find_existing_equipment()` 函数
  - 优先级1: `(asset_no + department_id + location_text)` 复合匹配
  - 优先级2: `equipment_tag` 精确匹配
  - 优先级3: `(name + department_id + location_text)` 组合匹配
- [ ] 单元测试：各种匹配场景

### 2.3 重复检测逻辑
- [ ] 在预览阶段检测Excel内部重复
- [ ] 记录已处理的 `(asset_no, dept_id, location)` 组合
- [ ] 标记后续重复行为"将跳过"
- [ ] 单元测试：重复检测准确性

### 2.4 增量更新逻辑
- [ ] A类字段（成本/净值）：总是更新
- [ ] B类字段：仅当DB为NULL时更新
- [ ] 模糊匹配记录：仅更新A类字段
- [ ] NULL值处理：空字符串 → NULL
- [ ] 单元测试：各种更新场景

### 2.5 位号冲突检测
- [ ] 在创建新记录前检查位号是否已被其他资产使用
- [ ] 冲突时记录错误，跳过该行
- [ ] 部分成功模式：不影响其他行
- [ ] 单元测试：冲突检测

### 2.6 批量事务优化
- [ ] 实现每100条commit一次的逻辑
- [ ] 错误回滚仅影响当前批次
- [ ] 性能测试：对比逐条commit vs 批量commit

### 2.7 审计日志记录
- [ ] 实现 `log_audit()` 函数
- [ ] 记录匹配策略、变更详情、警告信息
- [ ] 批次ID生成：`import_{timestamp}_{user_id}`
- [ ] 集成测试：审计日志完整性

### 2.8 API端点更新
- [ ] 更新 `/preview` 端点：返回匹配策略、重复标记、警告
- [ ] 重写 `/batch` 端点：四级匹配+增量更新+审计日志
- [ ] 返回详细统计：created/updated/skipped/error + batch_id

---

## ✅ Phase 3: 前端适配

### 3.1 预览界面优化
- [ ] 显示 `is_fixed_asset` 标记（固定资产/非固定资产图标）
- [ ] 显示匹配策略标签（composite/tag/fuzzy）
- [ ] 重复行标记："将跳过（与第X行重复）"
- [ ] 警告图标和提示文本（模糊匹配、部门未找到等）

### 3.2 用户编辑功能
- [ ] 允许用户修改部门、位置、负责人、设备位号
- [ ] 成本/净值字段可编辑
- [ ] "恢复默认值"按钮
- [ ] 修改后的数据正确传递到后端

### 3.3 导入结果展示
- [ ] 显示批次ID
- [ ] 统计卡片：创建X条，更新Y条，跳过Z条，错误N条
- [ ] 错误列表展开/折叠
- [ ] 成功消息：包含批次ID便于追溯

---

## ✅ Phase 4: 测试与验证

### 4.1 单元测试
- [ ] `find_existing_equipment()` 四级匹配逻辑
- [ ] 重复检测逻辑
- [ ] 增量更新策略（A类/B类字段）
- [ ] NULL值处理
- [ ] 位号冲突检测
- [ ] 覆盖率目标：>80%

### 4.2 集成测试
- [ ] 完整导入流程（上传→预览→修改→导入）
- [ ] 审计日志完整性验证
- [ ] 位号冲突场景
- [ ] 重复记录场景
- [ ] 模糊匹配场景

### 4.3 性能测试
- [ ] 1000条数据：< 10秒
- [ ] 3000条数据：< 30秒
- [ ] 5000条数据：< 60秒
- [ ] 内存占用监控

### 4.4 手动测试场景
- [ ] **场景1**：财务重估 - 仅更新成本净值
- [ ] **场景2**：首次导入 - 所有字段填充
- [ ] **场景3**：位号匹配 - 无资产编号，有位号
- [ ] **场景4**：模糊匹配 - 无资产编号、无位号，有名称+部门+位置
- [ ] **场景5**：重复记录 - Excel内部重复
- [ ] **场景6**：位号冲突 - Excel位号与DB冲突
- [ ] **场景7**：NULL值 - 成本为空字符串
- [ ] **场景8**：非固定资产 - asset_no为空

---

## ✅ Phase 5: 文档与部署

### 5.1 技术文档
- [x] ADR 002 已创建
- [x] CONTEXT.md 已更新
- [ ] API文档更新（Swagger/OpenAPI）
- [ ] 数据库迁移脚本说明
- [ ] 归档清理任务配置说明

### 5.2 用户手册
- [ ] "如何使用增量导入"指南
- [ ] 截图展示预览和修改流程
- [ ] 常见问题FAQ（重复记录、位号冲突等）

### 5.3 部署检查
- [ ] 数据库迁移脚本准备
- [ ] 定时任务配置（归档清理）
- [ ] 环境变量检查
- [ ] 回滚计划

---

## 🎯 验收标准

- [ ] 所有单元测试通过（覆盖率>80%）
- [ ] 集成测试通过
- [ ] 手动测试8个场景全部验证
- [ ] 性能指标达标（3000条<30秒）
- [ ] 审计日志完整准确
- [ ] 前端UI符合设计
- [ ] 文档齐全
- [ ] 业务方验收通过

---

**预计完成时间**: 2026-09-14（1周）  
**负责人**: Codex-Z  
**审核人**: 待定  
** blockers**: 无
