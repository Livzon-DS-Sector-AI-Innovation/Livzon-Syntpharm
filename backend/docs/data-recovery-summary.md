# 设备模块数据完整恢复报告

**日期**: 2026-08-31  
**问题**: 设备模块的位置、分类、部门数据被清空，导致前端筛选功能失效

## 问题根因

数据库中以下表被清空：
- `equipment.locations` - 位置表（0 条记录）
- `equipment.equipment_categories` - 分类表（0 条记录）
- `identity.departments` - 部门表（0 条记录）

但设备主表 `equipment.equipments` 保持完整（2952 条记录）。

**重要说明**: Git 分支切换不会影响数据库数据，数据丢失是因为执行了 SQL 删除操作。

## 恢复方案

### 1. 位置数据恢复 ✅

**脚本**: `backend/scripts/migration/restore_locations_from_equipment.py`

**方法**: 从设备的 `location_text` 字段提取唯一位置名称，批量创建位置记录

**结果**:
- ✅ 创建了 **952 个位置记录**
- ✅ 更新了 **2927 台设备**的 location_id
- ⚠️ 仍有 25 台设备未匹配（location_text 为 NULL 或 '-'）

### 2. 分类数据恢复 ✅

**脚本**: `backend/scripts/migration/restore_categories_from_equipment.py`

**方法**: 从设备的 `category_description` 字段解析分类层级（如"固定资产.机器设备"），批量创建分类记录和关联

**结果**:
- ✅ 创建了 **6 个分类**（固定资产、机器设备、房屋建筑物、电子设备、运输设备、其他设备）
- ✅ 创建了 **2952 个设备分类关联**
- ✅ 所有设备都有分类

### 3. 部门数据恢复 ✅

**种子文件**: `backend/scripts/seed/departments.json`

**方法**: 从种子 JSON 文件导入 18 个标准部门

**结果**:
- ✅ 导入了 **18 个部门**
- 包括：101车间、201车间、202车间、人事行政部、仓储部、动力部等

## 最终数据状态

| 数据类型 | 数量 | 状态 |
|---------|------|------|
| 位置记录 | 952 | ✅ 已恢复 |
| 分类记录 | 6 | ✅ 已恢复 |
| 部门记录 | 18 | ✅ 已恢复 |
| 设备记录 | 2952 | ✅ 完整 |
| 有 location_id 的设备 | 2927 | ✅ 已关联 |
| 有分类的设备 | 2952 | ✅ 全部关联 |

## API 验证

所有 API 端点正常工作：
- ✅ `GET /api/v1/equipment/locations?tree=true` - 返回 952 个位置
- ✅ `GET /api/v1/equipment/categories?tree=true` - 返回 6 个分类
- ✅ `GET /api/v1/equipment/equipments?location_id=xxx` - 正确筛选设备
- ✅ `GET /api/v1/equipment/equipments?category_id=xxx` - 正确筛选设备
- ✅ 前端位置树形菜单正常显示
- ✅ 前端分类树形菜单正常显示
- ✅ 前端按车间/分类筛选功能恢复正常

## 新增文件

1. **位置恢复脚本**: `backend/scripts/migration/restore_locations_from_equipment.py`
2. **分类恢复脚本**: `backend/scripts/migration/restore_categories_from_equipment.py`
3. **部门导入脚本**: `backend/scripts/migration/seed_departments.py`
4. **本报告**: `backend/docs/data-recovery-summary.md`

## 注意事项

1. **位置层级**: 当前所有位置都是平级的（parent_id = NULL），如需建立层级关系，可以手动调整
2. **分类层级**: 已建立一级分类（固定资产），二级分类（机器设备、电子设备等）作为独立分类
3. **未匹配的 25 台设备**: 这些设备的 location_text 为 NULL 或 '-'，可能需要手动补充位置信息

## 后续建议

1. **数据备份**: 定期导出关键数据，防止再次丢失
2. **权限控制**: 限制直接操作数据库的权限，避免误删除
3. **审计日志**: 启用数据库审计日志，追踪数据变更操作
4. **自动化测试**: 添加数据完整性检查，确保关键表不为空

## 执行命令汇总

```bash
# 恢复位置数据
cd /home/zhuangweizi/Livzon-Syntpharm/backend
docker compose exec backend uv run python scripts/migration/restore_locations_from_equipment.py

# 恢复分类数据
docker compose exec backend uv run python scripts/migration/restore_categories_from_equipment.py

# 导入部门数据
cd /home/zhuangweizi/Livzon-Syntpharm
docker compose exec -T postgres psql -U postgres -d dazah < /tmp/insert_departments.sql
```
