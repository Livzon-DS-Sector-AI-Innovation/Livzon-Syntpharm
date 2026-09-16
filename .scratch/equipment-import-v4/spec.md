# Spec: 设备导入 v4 优化 (Branch: lzhc-zhuang-equipment)

## Problem Statement
在 `lzhc-zhuang-equipment` 分支的基准版本 (`f7baf5a7`) 中，导入功能仍使用 v3 逻辑 (`batch_import.py`)。存在字段显示不全、匹配策略不够严谨、以及缺乏全量字段预览的问题。

## Solution
在现有分支基础上，引入 `batch_import_v4.py` 及配套组件，实现：
1. **后端**：22 字段全量映射、三级精准匹配、增量更新控制。
2. **前端**：基于 Ant Design v6 的 `ImportCockpit` 动态表格，支持 22 列横向滚动预览。

## Implementation Decisions (Based on Branch State)
*   **Backend**: 
    *   新增 `backend/app/modules/equipment/api/batch_import_v4.py`。
    *   新增 `backend/app/modules/equipment/service/import_engine.py` (包含 P1/P2/P3 匹配逻辑)。
    *   新增 `backend/app/modules/equipment/config/dept_mapping.py` (39 部门映射)。
*   **Frontend**: 
    *   重构 `frontend/src/components/equipment/ImportCockpit.tsx`。
    *   使用 `FIELD_DEFINITIONS` 硬编码 22 列（或改为从后端 `PREVIEW_HEADERS` 动态获取）。
*   **Database**: 
    *   需执行迁移脚本将唯一约束升级为 `(asset_no, department_id, location_text, is_deleted)`（含软删除标记，允许同一编号在软删除后重建）。

## User Stories
1. As a **设备管理员**, I want to **preview all 22 fields** in the `ImportCockpit`, so that I can verify data before import.
2. As a **Developer**, I want the **import logic to be isolated in v4 modules**, so that it doesn't break the existing v3 logic in this branch.

## Testing Decisions
*   Verify that `ImportCockpit` displays all 22 columns defined in `FIELD_DEFINITIONS`.
*   Verify that `batch_import_v4` correctly handles the 3-level matching strategy.

## Out of Scope
*   Modifying the existing `batch_import.py` (v3) logic.

## Additional Requirement: Statistics Window Update
*   **Problem**: The current statistics window only shows "Total", "In Use", "Under Repair", and "Disabled". It misses the "Scrapped" (报废) status.
*   **Solution**: Add a "Scrapped" counter to the statistics dashboard.
*   **Implementation**: 
    *   Backend: Ensure the `/statistics` API returns the count for `status = '报废'`.
    *   Frontend: Update the statistics component (likely in `EquipmentImportModal.tsx` or a dedicated stats component) to display the "Scrapped" count.
