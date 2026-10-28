# Spec: 设备统计窗口增加“报废”状态卡片

## Problem Statement
当前设备列表页 (`/equipment/assets`) 顶部的统计窗口仅显示“总数”、“在用”、“维修中”和“停用”。由于缺少“报废”状态的统计，管理员无法直观掌握已报废资产的数量。

## Solution
在设备列表页顶部的统计卡片行中，增加一个独立的“报废”统计卡片。

## User Stories
1. As a **设备管理员**, I want to **see the count of "Scrapped" (报废) devices** in the statistics dashboard.
2. As a **User**, I want the "Scrapped" card to be **visually consistent** with other status cards.

## Implementation Decisions
*   **Frontend**: Modify `frontend/src/app/(dashboard)/equipment/assets/page.tsx`.
*   **Data**: Use `by_status['报废']` from the existing statistics object.
*   **UI**: Add a new card in the same row as "Total", "In Use", etc.
