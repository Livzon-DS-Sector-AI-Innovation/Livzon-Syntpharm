# Spec: 设备台账动态排序与精密仪器交互优化

## Problem Statement
用户在设备台账页面编辑或浏览数据时，由于当前固定的“创建时间倒序”排列，导致具有相同业务属性的设备分散在不同页面。此外，新录入或更新设备后，列表顺序的跳变干扰了用户的连续操作体验。用户缺乏对列表展示顺序的控制权。

## Solution
为设备台账列表引入动态排序功能，默认采用“资产编号升序 + 空值置后”的逻辑。前端采用“精密仪器”风格的交互设计，通过方向性视觉反馈和状态标签增强用户对数据秩序的掌控感。

## API Contract (Frozen)
*   **Parameters**: `sort_by` (string), `order` (string: 'asc' | 'desc')
*   **Whitelist**: `asset_no`, `name`, `created_at`, `department_id`
*   **Default**: `sort_by='asset_no'`, `order='asc'` (Backend handles default if params are missing)
*   **NULL Handling**: `NULLS LAST` in SQL for all sortable columns.

## User Stories
1. As a 设备管理员, I want to sort the equipment list by Asset Number, so that I can quickly locate specific devices.
2. As a 财务专员, I want NULL asset numbers to appear at the end of the list, so that they do not interfere with valid assets.
3. As a 用户, I want to click on column headers to toggle sorting, so that I can view data in my preferred order.
4. As a 用户, I want to see a visual indicator of the current sort direction (Precision Instrument style), so that I understand the list state.

## Implementation Decisions
- **Backend**: Modify `GET /api/v1/equipment/equipments` to accept `sort_by` and `order`. Implement strict whitelist mapping to prevent SQL injection.
- **Frontend**: 
    - Use Ant Design controlled `sorter` mode.
    - Sync state with URL Query Params (reset page to 1 on sort change).
    - Visuals: 56px row height, Monospace fonts for IDs, directional underline animation.
    - **Note**: No FLIP animations for rows due to offset pagination; use simple fade-in instead.

## Testing Decisions
- Verify Repository layer generates correct SQL with dynamic `ORDER BY ... NULLS LAST`.
- Verify Frontend correctly resets page number when sorting changes.
- Check `aria-sort` attributes for accessibility.

## Out of Scope
- **Keyset Pagination**: Offset-based jitter (duplicate/missing rows across pages during data mutation) is accepted as a known limitation.
- **Multi-column Sorting**.
- **Complex Row Re-ordering Animations**.
