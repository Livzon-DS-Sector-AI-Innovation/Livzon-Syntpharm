# Spec: 设备批量导入 v3 - 智能映射与混合模式

## Problem Statement

作为设备管理员，我需要将 `202606sbgz.xls` 中的 2970 条设备数据批量导入系统台账。现有的 v2 导入功能存在以下问题：
1. **部门映射缺失**：Excel 中有 39 个部门名称，而系统中仅有 27 个，导致大量数据因部门无法匹配而被直接跳过。
2. **字段推断僵化**：所有设备的分类（Class）和重要性（Importance）均被强制设为默认值，无法反映资产的实际价值和管理需求。
3. **信息丢失**：Excel 中的"数量"列和详细的"资产类别说明"在导入后未能有效展示或存储。

## Solution

实现设备导入 v3 版本，采用"前端解析预览 + 后端智能入库"的混合模式。通过增强部门映射表、引入基于业务规则的字段自动推断逻辑，并将非标字段结构化存入 JSONB，确保数据导入的成功率提升至 95% 以上，同时保留完整的财务与管理信息。

## User Stories

1. 作为设备管理员，我希望上传 Excel 后能先看到数据预览，以便在正式入库前确认字段映射是否正确。
2. 作为设备管理员，我希望系统能根据"资产类别说明"自动推断设备分类（A/B/C），减少手动选择的工作量。
3. 作为设备管理员，我希望系统能根据"当前成本"自动划分设备重要性（高/中/低），确保高价值设备得到重点关注。
4. 作为设备管理员，我希望当 Excel 中的部门名称在系统中找不到时，数据依然能被导入（仅部门字段留空），而不是整行跳过。
5. 作为设备管理员，我希望能在设备台账表格中直接看到每台设备的"数量"，方便核对资产实物。
6. 作为设备管理员，我希望原始的"资产类别说明"能被完整保存，以便后续进行财务维度的统计分析。
7. 作为系统维护者，我希望导入过程能提供详细的警告列表（如部门未匹配），以便我持续优化映射规则。

## Implementation Decisions

### 1. 智能推断引擎 (Smart Inference Engine)
在后端 `batch_import.py` 中实现三个核心推断函数，作为预处理步骤：
- **`infer_equipment_class`**: 
  - "固定资产.房屋建筑物" → "A"
  - "固定资产.运输设备" → "B"
  - "固定资产.电子设备/机器设备" → "C"
- **`infer_importance`**: 
  - 成本 > 10万 → "高"
  - 5万 ≤ 成本 ≤ 10万 → "中"
  - 成本 < 5万 → "低"
- **`infer_status`**: 
  - "未报废" → "在用"

### 2. 部门映射降级策略 (Department Mapping Fallback)
修改 `map_department_name` 逻辑：
- **第一优先级**：查 `DEPT_MAPPING_V3` 扩展映射表（新增溶剂回收车间各岗位等）。
- **第二优先级**：直接使用 Excel 原名查询 `hr.departments`。
- **降级处理**：若仍找不到，返回 `department_id = NULL`，但**不跳过**该行数据，并在预览接口返回 `warnings`。

### 3. 非标字段结构化存储
- **数量 (Quantity)**: 存入 `equipment.technical_params` JSONB 字段，键名为 `"数量"`。
- **资产类别说明**: 直接存入 `equipment.category_description` 文本字段。

### 4. API 契约变更
- **`POST /api/v1/equipments/import/preview`**: 响应体增加 `equipment_class`, `importance`, `status`, `warnings` 字段。
- **`POST /api/v1/equipments/import/batch`**: 支持 `department_id` 为 NULL 的记录入库。

### 5. 前端展示增强
- 在 `EquipmentTable.tsx` 中增加"数量"列，从 `record.technical_params['数量']` 读取并渲染。

## Testing Decisions

### 1. 单元测试 (Unit Tests)
- **测试对象**: `infer_equipment_class`, `infer_importance`, `infer_status`, `map_department_name_v3`。
- **原则**: 覆盖所有分支逻辑，特别是边界值（如成本正好为 10 万）。

### 2. 集成测试 (Integration Tests)
- **测试对象**: `preview_import` 和 `batch_import` 接口。
- **方法**: 使用 `202606sbgz.xls` 的前 100 行作为 Fixture，验证推断结果是否符合预期，以及部门未匹配时的警告机制。

### 3. 端到端测试 (E2E)
- **测试对象**: 前端导入弹窗流程。
- **方法**: 模拟用户上传文件，检查预览表格中是否显示了推断后的分类和重要性，以及导入成功后数据库中是否存在对应的 `technical_params`。

## Out of Scope

1. **数据库 Schema 变更**: 不新增 `quantity` 物理列，坚持使用 JSONB。
2. **模糊匹配算法**: 不使用 Levenshtein 距离进行部门名模糊匹配，避免误匹配风险。
3. **手动修正界面**: 本次迭代不提供在预览阶段手动修改单行数据的 UI，仅支持全量确认或取消。

## Further Notes

- **性能考量**: 部门查询已从每行一次优化为批量预加载或缓存查找，以应对 3000+ 条数据的导入压力。
- **可观测性**: 所有的推断失败或映射降级都将记录在导入结果的 `warnings` 列表中，便于后续审计。
