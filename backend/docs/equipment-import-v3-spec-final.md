# 设备批量导入 v3 - 智能映射规格书

**状态**: Draft  
**创建日期**: 2026-08-18  
**来源**: /grill-with-docs 会话输出  
**关联 ADR**: [ADR 001](./adr/001-equipment-import-v3.md)

---

## 1. 需求背景

### 1.1 业务场景
用户需要批量导入 `202606sbgz.xls` 文件中的 2970 条设备数据到系统设备台账。

### 1.2 当前痛点（v2 版本）
1. **部门映射不完整**：Excel 有 39 个部门，系统只有 27 个，未匹配部门导致数据跳过
2. **缺少智能推断**：所有设备默认为 C 类、中等重要性，不符合实际业务
3. **"数量"字段丢失**：Excel 中的数量列未在前端展示
4. **资产类别说明未充分利用**：财务分类信息未被结构化存储

### 1.3 数据源分析
- **文件格式**: `.xls` (Excel 97-2003)
- **表头位置**: 第 4 行（索引从 0 开始）
- **总行数**: 2970 条数据
- **关键列**: 资产编号、标签号、设备名称、资产类别说明、数量、制造商、型号、当前成本、帐面净值、启用日期、实物所在部门、实物所在地点、报废状态、报废时间

---

## 2. 功能规格

### 2.1 混合导入模式

#### 流程
```
1. 用户上传 Excel 文件
   ↓
2. 前端解析并展示预览（不入库）
   ↓
3. 用户确认导入范围
   ↓
4. 后端执行批量导入（部分成功模式）
   ↓
5. 返回导入结果（成功/跳过/错误详情）
```

#### 验收标准
- [ ] 前端能正确解析 Excel 并展示预览表格
- [ ] 预览表格显示智能推断的字段值（equipment_class, importance, status）
- [ ] 预览表格标记部门未匹配的警告（但不阻止导入）
- [ ] 导入完成后显示详细的统计信息（成功数、跳过数、错误列表）

### 2.2 智能推断规则

#### 2.2.1 equipment_class（设备分类）
**输入**: `category_description`（资产类别说明）  
**规则**:
```python
if "房屋建筑物" in category_description or "房屋" in category_description:
    return "A"
elif "运输设备" in category_description or "车辆" in category_description:
    return "B"
elif "电子设备" in category_description or "机器设备" in category_description:
    return "C"
else:
    return "C"  # 默认
```

**测试用例**:
| 输入 | 预期输出 |
|------|---------|
| "固定资产.电子设备" | "C" |
| "固定资产.机器设备" | "C" |
| "固定资产.运输设备" | "B" |
| "固定资产.房屋建筑物" | "A" |
| None | "C" |

#### 2.2.2 importance（设备重要性）
**输入**: `current_cost`（当前成本，单位：元）  
**规则**:
```python
if current_cost is None:
    return "中"
elif current_cost > 100000:
    return "高"
elif current_cost >= 50000:
    return "中"
else:
    return "低"
```

**测试用例**:
| 输入 | 预期输出 |
|------|---------|
| 150000 | "高" |
| 75000 | "中" |
| 30000 | "低" |
| None | "中" |

#### 2.2.3 status（设备状态）
**输入**: `scrap_status`（报废状态）  
**规则**:
```python
if scrap_status == "未报废":
    return "在用"
elif scrap_status in ["已报废", "报废"]:
    return "报废"
else:
    return "在用"  # 默认
```

**测试用例**:
| 输入 | 预期输出 |
|------|---------|
| "未报废" | "在用" |
| "已报废" | "报废" |
| None | "在用" |

### 2.3 部门映射增强

#### 2.3.1 映射策略
```python
def map_department_name_v3(excel_dept: str, db: AsyncSession):
    # 步骤1: 尝试 DEPT_MAPPING_V3 精确匹配
    standard_name = DEPT_MAPPING_V3.get(excel_dept)
    
    # 步骤2: 如果映射表中没有，直接使用原名查询
    if not standard_name:
        standard_name = excel_dept
    
    # 步骤3: 查询数据库
    dept_id = await get_department_id_by_name(db, standard_name)
    
    # 步骤4: 未找到，返回 None（降级处理，不跳过数据）
    if dept_id:
        return standard_name, dept_id
    else:
        return None, None
```

#### 2.3.2 新增映射关系
```python
DEPT_MAPPING_V3 = {
    # ... 原有映射 ...
    
    # v3 新增：溶剂回收车间各岗位
    "溶剂回收车间-401岗": "溶剂回收车间",
    "溶剂回收车间-402岗": "溶剂回收车间",
    "溶剂回收车间-403岗": "溶剂回收车间",
    "溶剂回收车间-404岗": "溶剂回收车间",
    "溶剂回收车间-405岗": "溶剂回收车间",
    
    # v3 新增：其他缺失部门
    "非头孢制造部": "非头孢制造部",
    "头孢销售部": "头孢销售部",
    "注册部": "注册部",
    "财务部": "财务部",
    "采购部": "采购部",
}
```

#### 2.3.3 验收标准
- [ ] 溶剂回收车间各岗位能正确映射到"溶剂回收车间"
- [ ] 系统中不存在的部门（如"XX临时部门"）不会导致数据跳过
- [ ] 预览接口返回 warning 列表，告知用户哪些部门未匹配

### 2.4 数量字段处理

#### 2.4.1 存储策略
- **位置**: `equipment.technical_params` (JSONB 字段)
- **键名**: `"数量"`
- **示例**: `{"数量": 1}`

#### 2.4.2 前端展示
在 `EquipmentTable.tsx` 中新增列：
```typescript
{ 
  title: '数量', 
  dataIndex: 'technical_params', 
  key: 'quantity', 
  width: 80, 
  render: (params: Record<string, unknown> | null) => {
    if (!params || typeof params !== 'object') return '-'
    const quantity = (params as Record<string, unknown>)['数量']
    return quantity ?? '-'
  } 
}
```

#### 2.4.3 验收标准
- [ ] 导入后数据库中 `technical_params` 包含 `"数量"` 字段
- [ ] 前端表格能正确显示数量值
- [ ] 数量为 NULL 时显示 "-"

### 2.5 资产类别说明处理

#### 2.5.1 存储策略
- **字段**: `equipment.category_description`
- **内容**: 直接存入 Excel 原始值（如"固定资产.电子设备"）
- **用途**: 保留财务分类信息，供后续报表使用

#### 2.5.2 验收标准
- [ ] 导入后 `category_description` 字段包含原始值
- [ ] 前端详情页能显示该字段

---

## 3. API 规格

### 3.1 预览接口
**端点**: `POST /api/v1/equipments/import/preview`  
**请求体**:
```json
[
  {
    "资产编号": "59070",
    "设备名称": "生化培养箱",
    "实物所在部门": "检验室",
    "当前成本": 22123.89,
    ...
  }
]
```

**响应体**:
```json
{
  "code": 200,
  "data": {
    "total": 2970,
    "valid_count": 2970,
    "warning_count": 15,
    "items": [
      {
        "row_index": 0,
        "asset_no": "59070",
        "name": "生化培养箱",
        "department_name": "质量控制部",
        "department_id": "uuid...",
        "equipment_class": "C",
        "importance": "低",
        "status": "在用",
        "category_description": "固定资产.电子设备",
        "current_cost": 22123.89,
        "technical_params": {"数量": 1},
        "validation_errors": [],
        "warnings": []
      }
    ]
  }
}
```

### 3.2 批量导入接口
**端点**: `POST /api/v1/equipments/import/batch`  
**请求体**: 同预览接口  
**响应体**:
```json
{
  "code": 200,
  "data": {
    "created_count": 2950,
    "skipped_count": 20,
    "errors": [
      {"row": 100, "error": "资产编号不能为空"}
    ]
  }
}
```

---

## 4. 测试计划

### 4.1 单元测试
- [ ] `test_infer_equipment_class()`: 验证 5 种资产类别的推断
- [ ] `test_infer_importance()`: 验证 3 档成本分级
- [ ] `test_infer_status()`: 验证报废状态映射
- [ ] `test_map_department_name_v3()`: 验证部门映射和降级逻辑

### 4.2 集成测试
- [ ] 使用真实 Excel 文件测试预览接口
- [ ] 验证 2970 条数据的导入成功率 > 95%
- [ ] 检查 technical_params 中是否正确存储"数量"

### 4.3 端到端测试
- [ ] 前端上传 Excel → 预览 → 确认导入 → 验证数据库
- [ ] 前端表格显示"数量"列

---

## 5. 风险与缓解

### 5.1 风险：智能推断可能与实际不符
**缓解**: 
- 在预览阶段展示推断结果，允许用户手动修正
- 提供"导出修正后的 Excel"功能（未来迭代）

### 5.2 风险：部门映射仍不完整
**缓解**:
- 记录未匹配部门到日志，定期更新映射表
- 提供"批量添加部门"的管理功能（未来迭代）

---

## 6. 验收清单

- [ ] 所有单元测试通过
- [ ] 集成测试通过率 > 95%
- [ ] 前端预览界面正常显示
- [ ] 前端表格显示"数量"列
- [ ] 代码通过 `ruff check` 和 `tsc --noEmit`
- [ ] ADR 001 已归档
- [ ] CONTEXT.md 已更新

---

*规格书作者: AI Assistant*  
*审核状态: Pending Review*
