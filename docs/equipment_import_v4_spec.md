# 设备批量导入 v4 功能规格说明书

## 1. 核心设计原则
- **唯一标识**：`(asset_no, department_id, location_text)` 三元组。资产编号仅作为批次号，同一批次在不同位置的设备视为独立实例。
- **范围隔离**：导入操作严格限制在 Excel 数据集对应的记录内，严禁跨部门/位置匹配。
- **按需覆盖**：财务字段自动同步，基础信息字段受 `force_override` 开关保护。

## 2. API 接口
- **端点**: `POST /api/v1/equipment/equipments/import/batch`
- **参数**: 
  - `data`: JSON 数组
  - `force_override`: Boolean (默认 True)。控制是否强制覆盖数据库中已有的非空基础信息。

## 3. 三级匹配策略
| 优先级 | 策略名 | 匹配条件 | 说明 |
|--------|--------|---------|------|
| **P1** | composite | `asset_no + dept_id + loc` | 精确匹配唯一标识，最优先 |
| **P2** | tag | `equipment_tag` | 全局唯一位号匹配，处理无资产编号但有位号的场景 |
| **P3** | fuzzy | `name + dept_id + loc` | 仅在无编号且无位号时触发 |

*注：已删除 P1b (location_match) 和旧 P2 (asset_no_only) 以避免错误关联。*

## 4. 增量更新规则
- **A类字段 (总是更新)**: `current_cost`, `book_value`
- **B类字段 (条件更新)**: 
  - 列表: `label_no`, `equipment_tag`, `equipment_class`, `name`, `responsible_person_name`, `status`, `category_description`, `quantity`, `model`, `specification`, `manufacturer`, `supplier`, `scrap_status`, `scrap_time`, `production_date`, `commissioning_date`, `description`, `department_id`, `location_text`
  - 逻辑: 仅当 `force_override=True` 或数据库原值为 `NULL` 时执行更新。

## 5. 数据完整性保障
- **内部去重**: 导入前检测 Excel 内部的 `(asset_no, dept, loc)` 重复行并跳过。
- **部门映射**: 通过 `config/dept_mapping.py` 进行标准化，缺失部门则 Fail-fast 跳过并输出清单。
- **审计日志**: 所有创建、更新、跳过操作均记录至 `import_audit_logs` 表。
