---
title: "设备导入 v4 - 强制覆盖业务字段选项"
status: ready-for-agent
created: 2026-09-08
---

## Problem Statement
在当前的 v4 导入逻辑中，为了保护用户手动修正的业务数据（如归属部门、设备位置），系统采用了“仅当数据库为 NULL 时更新”的保护性策略。然而，在某些特定场景下（如全厂组织架构大调整、批量位置迁移），用户希望利用 Excel 表格作为“最新真理来源”，**强制覆盖**数据库中现有的所有业务字段，即使这些字段已经有值。目前系统缺乏这种灵活性，导致用户无法通过导入完成批量业务数据的修正。

## Solution
在设备批量导入界面增加一个可选的复选框：“**强制覆盖业务字段 (Force Override Business Fields)**”。
*   **默认状态**：未勾选（保持当前的保护性更新逻辑，确保稳定性）。
*   **勾选状态**：后端在执行导入时，将忽略“仅当 DB 为 NULL 时更新”的限制，对 B类字段（部门、位置、位号等）执行与 A类字段相同的“强制覆盖”逻辑。

## User Stories
1. As a 设备管理员, I want to check a "Force Override" box during import, so that I can bulk update equipment locations after a factory reorganization without manually editing each record.
2. As a 财务专员, I want the default behavior to remain protective, so that accidental re-imports of old Excel files do not overwrite my carefully corrected department assignments.
3. As a 系统审计员, I want to see a clear indication in the audit log when a business field was force-overridden, so that I can track significant data changes.

## Implementation Decisions
*   **API 接口变更**: `POST /api/v1/equipment/import/batch` 增加可选布尔字段 `force_override_business_fields` (default: `false`)。
*   **后端逻辑调整**: 在 `apply_incremental_update` 函数中增加 `force_override` 参数。如果为 `True`，B类字段无论当前值是否为 NULL，均与 Excel 数据进行比对并更新。
*   **前端交互设计**: 在导入预览界面添加带有警示 tooltip 的复选框，并在勾选时弹出二次确认对话框。
*   **审计日志增强**: 在 `import_audit_logs` 表中，当发生强制覆盖时，在 `changes` 字段中明确标记 `"override_type": "force"`。

## Testing Decisions
*   **单元测试**: 验证 `apply_incremental_update` 在两种模式下的行为差异。
*   **集成测试**: 
    *   场景 1 (保护模式): 确认已手动修改的部门未被旧 Excel 覆盖。
    *   场景 2 (强制模式): 确认所有匹配到的设备业务字段均被 Excel 数据替换。

## Out of Scope
*   不支持针对单个字段的独立覆盖策略。
*   不包含导入前的数据差异预览。
