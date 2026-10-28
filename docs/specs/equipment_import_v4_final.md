# 设备批量导入 v4 最终规格说明书 (Final Spec)

## 1. 核心架构
*   **组件体系**: `ImportCockpit` (预览), `ForceOverrideToggle` (开关), `BatchTracker` (结果)。
*   **UI 规范**: 严格使用 **Ant Design v6** (`Table`, `Tag`, `Tooltip`)。
*   **入口**: 集成于设备管理模块，通过 `EquipmentImportModal` 触发。

## 2. 数据契约 (API Contract)
*   **Preview**: `POST /api/v1/equipment/equipments/import/preview` (FormData)
    *   返回: `data.data.items` (包含 22 个映射字段)
*   **Batch**: `POST /api/v1/equipment/equipments/import/batch` (JSON)
    *   参数: `force_override_business_fields` (boolean)

## 3. 字段全集 (22 Fields)
`row_index`, `asset_no`, `label_no`, `name`, `category_description`, `equipment_class`, `manufacturer`, `model`, `current_cost`, `book_value`, `quantity`, `department_name`, `location_text`, `status`, `scrap_status`, `scrap_time`, `equipment_tag`, `responsible_person_name`, `specification`, `supplier`, `production_date`, `commissioning_date`, `description`.

## 4. 校验显示逻辑
*   **Pass**: 绿色 Tag "通过"
*   **Duplicate**: 黄色 Tag "重复"
*   **Error**: 红色 Tag "异常" (需 Tooltip 显示 error_message)
