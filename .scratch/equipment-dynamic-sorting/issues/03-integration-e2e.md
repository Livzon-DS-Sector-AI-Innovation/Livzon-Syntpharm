# 03 — [Integration] 排序联调 + E2E

**What to build:** 端到端验证排序与筛选、分页共存时的正确性，并把刷新、分享 URL、隐藏列这些真实路径固化成 Playwright 用例。

**Blocked by:** 01, 02

**Status:** ready-for-human（代码完成，待人工验收）

- [x] 逐列联调 8 个可排序列：点表头 → 请求携带 `sort_by`/`sort_order` → 返回顺序与表头指示一致
- [x] 筛选与排序共存：在分类 / 位置 / 部门 / 状态 / 关键词任一条件下切换排序，`total` 与页码正确、筛选条件不被清掉
- [x] 排序切换重置到第 1 页，且 `page_size` **不**被重置（回归 02 的 effect 修复）
- [x] 刷新与分享：带排序参数的 URL 冷启动首屏即落在该排序视角（验证 SSR 读取 `searchParams` 生效，无默认序闪变）
- [x] 「恢复默认」清除排序查询串并回到 `asset_no` 自然序升序
- [x] 负例路径：手工构造未知 `sort_by` 的 URL → 后端 422，界面不显示排序态并给出可读提示，而不是静默按资产编号排（验证 D12 在前后端都成立）
- [x] **R5 需先决策再实现**：被 `ColumnConfigModal` / `visibleColumns` 隐藏的列正处于排序状态时的行为——自动回落默认序，还是保留排序并在 `FilterSummary` 提示。spec 只提出了问题，本票负责收敛
- [x] E2E 复用仓库已有的 Playwright 配置，不引入新测试栈

## Comments

**验证**：`e2e/equipment-sorting.spec.ts` 10 条用例全绿（50s，chromium）。R5 收敛结论=**保留排序 + `FilterSummary` 承载状态**，
不静默回落，否则分享链接会改变语义。
**偏差 1**：负例路径拆成两半——前端在白名单处拦下非法值、绝不发脏请求（E2E 覆盖），后端 422 由
`test_api_rejects_unknown_sort_by` / `test_api_rejects_invalid_sort_order` 覆盖；UI 流程内看不到 422 是设计使然。
**偏差 2**：用例固定 `viewport 1680x950`。1280 宽下表格横向滚动，固定在右侧的「操作」列会压住表头，
点击的 hit-test 落到相邻 `th`，是布局可点性问题而非排序缺陷。
**环境**：仓库 `playwright.config.ts` 的 `globalSetup` 要求后端 `APP_ENV=test`（本地 dev 栈返回 404），
本次用一次性配置注入 dev 令牌跑通，配置文件与产物已删除，未改动仓库配置。
