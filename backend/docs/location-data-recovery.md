# 位置数据恢复报告

**日期**: 2026-08-31  
**问题**: 设备模块的位置表（locations）被清空，导致前端筛选车间时无法显示任何设备

## 问题根因

数据库中 `equipment.locations` 表的所有记录被删除，但 `equipment.equipments` 表中的 2952 条设备记录仍然存在。由于设备的 `location_id` 字段全部为 NULL，前端按位置筛选时无法返回任何数据。

**注意**: Git rebase/merge 操作不会影响数据库数据，数据丢失是因为执行了 SQL 删除操作。

## 解决方案

### 执行的脚本

创建了 `backend/scripts/migration/restore_locations_from_equipment.py` 脚本，从设备记录的 `location_text` 字段恢复位置数据。

### 执行步骤

1. **提取唯一位置名称**: 从 2952 条设备记录中提取出 952 个唯一的 `location_text`
2. **创建位置记录**: 批量创建 952 个位置记录，生成代码格式为 `LOC-XXXX`
3. **更新设备关联**: 通过精确匹配 `location_text`，更新了 2927 台设备的 `location_id`
4. **验证结果**: 
   - 位置表: 952 条记录 ✅
   - 有 location_id 的设备: 2927 台 ✅
   - 无 location_id 的设备: 25 台（location_text 为 NULL 或 '-'）

### 执行命令

```bash
cd /home/zhuangweizi/Livzon-Syntpharm/backend
docker compose exec backend uv run python scripts/migration/restore_locations_from_equipment.py
```

## 恢复结果

### 数据状态

| 指标 | 数量 | 状态 |
|------|------|------|
| 位置记录总数 | 952 | ✅ 已恢复 |
| 有 location_id 的设备 | 2927 | ✅ 已关联 |
| 无 location_id 的设备 | 25 | ⚠️ 未匹配 |
| 设备总数 | 2952 | ✅ 完整 |

### API 验证

- ✅ `GET /api/v1/equipment/locations?tree=true` - 返回 952 个位置
- ✅ `GET /api/v1/equipment/equipments?location_id=xxx` - 正确筛选设备
- ✅ 前端位置树形菜单正常显示
- ✅ 前端按车间筛选功能恢复正常

## 未匹配的 25 台设备

这些设备的 `location_text` 可能是：
- NULL（从未填写过位置）
- `-`（表示无位置）
- 其他特殊值

如需处理这些设备，可以：
1. 手动通过前端界面补充位置信息
2. 修改脚本支持模糊匹配
3. 忽略这些设备（它们可能确实没有固定位置）

## 后续建议

1. **数据备份**: 定期导出位置和分类数据，防止再次丢失
2. **导入脚本**: 如果有 Excel 格式的完整位置数据，可以编写导入脚本替换自动生成的数据
3. **层级结构**: 当前所有位置都是平级的（parent_id = NULL），如需建立层级关系，可以手动调整或通过脚本根据命名规则自动生成
4. **分类数据**: 如果分类表（equipment_categories）也被清空，可以使用类似方法从设备的 `category_description` 字段恢复

## 相关文件

- 恢复脚本: `backend/scripts/migration/restore_locations_from_equipment.py`
- 本报告: `backend/docs/location-data-recovery.md`
