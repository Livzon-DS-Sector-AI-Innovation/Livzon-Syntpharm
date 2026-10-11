# Spec: 设备模块 Excel 智能同步功能

## Problem Statement

当前设备模块的成本和净值数据每月都会在 Excel 表格中更新。用户需要一种方式，能够将更新后的 Excel 表格导入系统，自动同步数据库中的设备信息（包括基础档案、财务数据、位置归属等），同时确保不丢失已有的维修工单、校准记录等业务关联数据。现有的“全量清空再导入”方式会导致历史业务数据丢失，无法满足生产环境需求。

## Solution

在后端实现一个基于“资产编号 + 部门 + 位置”唯一性约束的智能同步接口。该接口接收上传的 Excel 文件，通过比对数据库现有记录，执行增量更新（Upsert）：匹配成功的记录更新所有字段（含成本/净值），新增记录自动创建，Excel 中消失的记录在系统中软删除。前端提供文件上传入口，触发同步并展示结果统计。

## User Stories

1. As a 设备管理员, I want to upload an updated Excel file, so that the system automatically syncs equipment data without losing historical maintenance records.
2. As a 财务人员, I want the "Current Cost" and "Book Value" fields to be updated from the Excel file, so that the financial reports in the system are always accurate.
3. As a 仓库管理员, I want equipment that has been moved to a new location in the Excel file to be automatically updated in the system, so that the asset location is always consistent with reality.
4. As a 系统用户, I want to see a summary report after the import (e.g., how many updated, inserted, or deleted), so that I can verify the sync was successful.
5. As a 设备管理员, I want the system to handle duplicate asset numbers in different locations correctly, so that each physical device is tracked independently.
6. As a 审计人员, I want equipment removed from the monthly Excel list to be marked as "Deleted" rather than physically erased, so that we maintain a complete audit trail.

## Implementation Decisions

- **API Contract**: Add a `POST /api/v1/equipment/import-excel` endpoint that accepts a `multipart/form-data` file upload.
- **Service Logic**: Implement `sync_equipments_from_excel` in the Equipment Service layer. It will use `pandas` to parse the Excel file and `SQLAlchemy` for database operations.
- **Matching Logic**: The unique key for matching is `(asset_no, department_id, location_id)`. If an exact match isn't found, it will fallback to matching by `asset_no` alone to handle asset migrations (location changes).
- **Data Protection**: Use `UPDATE` statements instead of `DELETE` + `INSERT` to preserve foreign key relationships with work orders, calibration plans, and inspection records.
- **Soft Delete**: Records present in the database but missing from the Excel file will have their `is_deleted` flag set to `true`.
- **Field Mapping**: All fields from the Excel template (Name, Model, Manufacturer, Cost, Net Value, etc.) will be synchronized.
- **Department/Location Resolution**: The service will resolve raw Excel text (e.g., "环保中心") into internal UUIDs using existing mapping logic.

## Testing Decisions

- **Unit Tests**: Test the `sync_equipments_from_excel` function with mock Excel data covering scenarios: new equipment, updated cost, location migration, and soft deletion.
- **Integration Tests**: Verify that after a sync operation, related `WorkOrder` and `CalibrationRecord` entries remain linked to the correct equipment ID.
- **Validation**: Ensure the API rejects non-Excel files or malformed Excel structures with clear error messages.

## Out of Scope

- Automatic generation of depreciation schedules based on the new cost values.
- Syncing of personnel/responsible person details if they are not already in the identity module.
- Real-time synchronization; this is a batch process triggered by manual upload.

## Further Notes

- The Excel file format must strictly follow the existing template (`202606sbgz.xls`) with headers starting at row 5.
- This feature replaces the previous "full reset" migration scripts for ongoing monthly maintenance.
