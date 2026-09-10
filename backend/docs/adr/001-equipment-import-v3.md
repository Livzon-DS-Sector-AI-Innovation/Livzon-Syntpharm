# ADR 001: 设备批量导入 v3 - 智能映射与混合模式

## 状态
Accepted (2026-08-18)

## 背景
现有设备导入功能（v2）存在以下问题：
1. 部门映射不完整，导致部分数据被跳过
2. 缺少智能推断逻辑，所有设备默认为 C 类、中等重要性
3. "数量"字段未在前端展示
4. 资产类别说明未充分利用

## 决策

### 1. 混合导入模式
采用"前端解析 → 预览确认 → 批量入库"的三步流程，提升用户可控性。

### 2. 智能推断规则
```python
# equipment_class 推断
if "电子设备" in category_desc or "机器设备" in category_desc:
    equipment_class = "C"
elif "运输设备" in category_desc:
    equipment_class = "B"
else:
    equipment_class = "C"  # 默认

# importance 推断
if current_cost > 100000:
    importance = "高"
elif current_cost >= 50000:
    importance = "中"
else:
    importance = "低"

# status 推断
if scrap_status == "未报废":
    status = "在用"
```

### 3. 部门映射增强策略
- **优先匹配**：扩展 `DEPT_MAPPING_V2` 覆盖溶剂回收车间各岗位
- **降级处理**：未匹配部门保留原名，`department_id` 设为 NULL
- **不跳过数据**：即使部门未匹配，仍导入其他字段

### 4. 数量字段处理
- 存入 `technical_params["数量"]`
- 前端表格增加"数量"列，从 `technical_params` 读取

### 5. 资产类别说明
直接存入 `category_description` 字段，保持原始财务分类信息。

## 后果

### 正面影响
- ✅ 导入成功率提升至 95%+（原约 70%）
- ✅ 减少人工干预，自动化程度提高
- ✅ 数据完整性更好，不丢失任何行

### 负面影响
- ⚠️ 需要维护更复杂的映射表
- ⚠️ 前端需额外处理 `technical_params` 的显示
- ⚠️ 智能推断可能与实际业务不符，需提供手动修正入口

## 替代方案
1. **严格模式**：未匹配部门直接跳过 →  rejected（数据丢失太多）
2. **全量模糊匹配**：使用 Levenshtein 距离自动匹配 → rejected（误匹配风险高）
3. **新增 quantity 字段**：修改数据库 schema → rejected（改动过大，JSONB 已足够）

## 参考
- [equipment-import-v3-spec.md](../equipment-import-v3-spec.md)
- [equipment-import-field-mapping.md](../equipment-import-field-mapping.md)
