# 06 — 三段式布局实现一屏显示

**What to build:** 将设备台账页面重构为三段式布局（标题+统计+筛选、表格、分页），实现完全一屏显示，无页面级滚动。

**Blocked by:** 04 (统计卡片移到顶部), 05 (工业色彩主题)

**Blocking:** None

**Status:** completed

## Acceptance Criteria

- [x] 页面根容器设置为 `height: 100vh; overflow: hidden`，无页面级滚动
- [x] 第一段（控制层）：标题 + 统计卡片 + 筛选栏，紧凑化设计
- [x] 第二段（数据层）：左右分栏，表格区域启用内部滚动
- [x] 第三段（导航层）：分页控件固定在底部，始终可见
- [x] EquipmentTable 配置 `scroll={{ x: 'max-content', y: '100%' }}`，表头 sticky 固定
- [x] 默认每页显示 15 条数据（`DEFAULT_EQUIPMENT_PAGE_SIZE = 15`）
- [x] 无页面级滚动条，只有表格内部滚动条

## Implementation Details

### 布局结构

```
页面根容器 (height: 100vh, overflow: hidden)
├── 第一段 (flexShrink: 0) - 固定高度
│   ├── 标题行 (marginBottom: 8, paddingBottom: 6)
│   ├── 统计卡片 (横向铺满，20px 数字，8px 12px 内边距)
│   └── 工具栏 (padding: 8px 0 6px)
├── 第二段 (flex: 1, overflow: hidden)
│   ├── 左侧边栏
│   └── 右侧表格容器 (padding: 12px 16px)
│       ├── 折叠按钮
│       ├── 表格区域 (flex: 1, overflow: auto) ← 内部滚动
│       │   └── EquipmentTable (scroll.y: 100%)
│       │       ├── 表头 (sticky, top: 0) ← 固定
│       │       └── 表体 (15行，可滚动)
│       └── 第三段：分页控件 (flexShrink: 0)
```

### 关键修改

1. **EquipmentPage.tsx**
   - 页面根容器：`height: '100vh'`, 移除 padding/gap
   - 标题行：压缩间距
   - 统计卡片：字号从 22px→20px，内边距从 10px 16px→8px 12px
   - 工具栏：padding 从 12px 0 8px→8px 0 6px
   - 右侧表格容器：padding 从 20px 24px→12px 16px
   - 表格区域：添加 `overflow: 'auto'`

2. **StatsCards.tsx**
   - 数字字号：22px→20px
   - 标签字号：12px→11px
   - 内边距：10px 16px→8px 12px
   - 标签间距：4px→2px

3. **EquipmentTable.tsx**
   - 添加 `scroll={{ x: 'max-content', y: '100%' }}`
   - 保持 `sticky={{ offsetHeader: 0 }}`

4. **equipment-query.ts**
   - `DEFAULT_EQUIPMENT_PAGE_SIZE`: 20→15

5. **industrial-theme.css**
   - 移除 `.equipment-ledger-table-scroll` 自定义滚动条样式

## Testing

- [x] 手动测试：验证页面无滚动条，三段内容都在视口内
- [x] 手动测试：验证表格内部可以滚动，表头固定
- [x] 手动测试：验证分页控件始终可见在底部
- [x] 手动测试：调整浏览器窗口大小，验证响应式表现

## Design Rationale

**控制层紧凑化**：统计和筛选是辅助信息，应该占用最少空间，把主要空间留给数据层。

**数据层最大化**：表格是核心内容，通过内部滚动可以显示任意数量的行，同时保持表头固定。

**导航层固定可见**：分页控件必须在视口内，无需滚动即可看到，提升操作效率。

## Related Commits

- `e05665d9` feat(equipment): 实现一屏显示优化方案
- `4afcf511` fix(equipment): 移除表格内部滚动，实现完全一屏显示
- `21ba2df6` style(equipment): 紧凑化设计，确保一屏显示三段内容
- `05bccfd4` fix(equipment): 调整页面高度确保三段内容一屏显示
- `8ea0b59f` feat(equipment): 整合三段式布局与视觉优化
