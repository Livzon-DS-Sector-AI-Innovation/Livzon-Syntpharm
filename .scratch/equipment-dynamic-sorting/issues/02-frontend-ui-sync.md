# 02 — [Frontend] 可排序表头 + URL 单一数据源 + 排版基线

**What to build:** 用 antd Table 受控 `sorter` 给 8 个高频列接上排序，把查询状态（排序 / 分页 / 筛选）收敛到 URL 唯一来源，并靠等宽与对齐而非加大行高建立台账的秩序感。

**Blocked by:** 01（需要返工后的白名单与重新生成的 API 类型，可点列必须与之相等）

**Status:** ready-for-human（代码完成，待人工验收）

- [x] **D10 前置修复**：`EquipmentPage.tsx:160-163` 的 fetch effect 缺失 `fetchData` 依赖且硬编码 `fetchData(1, 20)`，会把用户选定的 `page_size` 重置。不先修好，加排序会原样复现
- [x] **D10 状态收敛**：删除 `EquipmentTable.tsx:51-52` 的 `localPage/localPageSize` 与 `stores/equipment.ts:44-45` 中对设备列表已失效的 `page/pageSize`，改为 URL 单一数据源；排序变化时重置到第 1 页
- [x] **D10 SSR**：`assets/page.tsx:44` 目前硬编码 `{page:1, page_size:20}` 且忽略查询串。改为读取 `searchParams` 并传入同一查询构造函数，使带排序的 URL 冷启动首屏即落在正确视角，而非默认序后再被客户端覆盖产生闪变
- [x] **D7** 8 列挂 `sorter: true`，经 `onChange(pagination, filters, sorter)` 映射为 `sort_by`/`sort_order`；参照仓库既有同构实现 `src/app/(dashboard)/production/product-output/[workshop]/[productId]/page.tsx:557-650`
- [x] **D2 类型对齐**：`sort_by` 须为 OpenAPI enum（ticket 01 用 `Literal` 保证）。前端维护一份运行时清单（列 key → 表头列），用生成类型 `EquipmentSortBy` 做 `satisfies`/`Record` 编译期校验——**不是运行时从类型派生**（TS 联合类型编译期擦除、不可枚举）。后端增删字段即编译报错，达成不漂移。未列入的列不渲染排序 affordance
- [x] **D8 排版**：`asset_no`、标签号、设备位号、日期、金额列使用等宽字体 + `font-variant-numeric: tabular-nums`；`current_cost`、`book_value`、数量列改右对齐（现左对齐，`EquipmentTable.tsx:178-179`）
- [x] **D8** 当前排序列以 theme token 表达（表头底色/下划线）；**保持 `size="small"`，不改行高**
- [x] `EquipmentTable.tsx:79` 的 `h - 37 - 56` 魔法数改为从实测表头高度派生
- [x] **D11** 排序状态并入 `FilterSummary` 并带「恢复默认」动作；注意该组件在无任何筛选时 `return null`，排序非默认时也需渲染
- [x] **D9** 动效限于表头指示器方向切换（≤150ms）与 tbody 交叉淡入，遵守 `prefers-reduced-motion`

明确不做（v1 曾要求、v2 已否决）：自定义 Sort Icon 组件、方向性渐变下划线自研指示器、56px 行高、右上角独立「排序状态胶囊」、200ms 行重排 FLIP 动画。

## Comments

**验证**：`tsc --noEmit` 与 `eslint`（0 error）通过；浏览器实测 8 列表头三态（URL / 请求参数 / `aria-sort`）一致，
排序切换保留 `page_size`、只重置 `page`；SSR 读 `searchParams`，冷启动无默认序闪变；动效 150ms 且受
`prefers-reduced-motion` 约束。`EquipmentTable.tsx:268` 的淡入相位切换会触发
`react-hooks/set-state-in-effect` **warning**（非 error）——这是重放 CSS animation 的有意写法。
