# Spec: 设备台账动态排序（v2）

> 本版替换 v2 之前的草稿。v1 的核心前提（`asset_no` 存在空值、需要 NULLS LAST）经真实数据勘查证伪，
> 且未处理编号格式混用导致的词法序错误。v2 以 `equipment.equipments` 实际 2972 行的分布为依据。
>
> v1 已采纳的两条决策保留：前端使用 antd 受控 `sorter`、行重排不做 FLIP 只做淡入。
>
> 01–04 落地后已回写实现事实：R5 收敛结论、antd 能力边界（键盘、固定列遮挡）、实测数据量与耗时。
> 阅读时以「决策 + 实测」为准，未标 `待确认` 的条目均已有测试钉住。
>
> **当前状态**：01–04 代码完成。验证 = 后端 `test_sorting.py` 34 passed + `test_import_v4_contract.py` 2 passed、
> 前端 `e2e/equipment-sorting.spec.ts` 10 passed。未关闭项仅 R4（状态业务序待业务确认）；
> R7 已关闭（自然滚动 + sticky 表头，详见 Risks）；
> R8（dev compose 挂载 tests）属受保护文件改动，待架构负责人批准。

## Problem Statement

设备台账原先固定按「创建时间倒序」展示，用户无法按业务属性组织数据，新录入或更新设备后行位置跳变，
打断连续核对工作。ticket 01 已实现服务端动态排序并把默认序切到 `asset_no` 升序后，暴露三个新问题：

1. **编号语义错误已对用户可见**：`asset_no` 一列混用两种格式。纯数字段（957 行，4–7 位变长）按词法序得到
   `0000002`(=2) 排在 `0001`(=1) 之前，用户看到的就是「编号没排对」。
2. **排序列覆盖不足且静默失效**：后端白名单只有 4 个字段，台账有 20 列。`SORT_MAP.get(sort_by, asset_no)`
   是静默兜底——前端把 20 列都挂上排序后，点「投用日期」会悄悄按资产编号排，界面仍显示按日期排。
3. **参数契约与仓库既有约定分叉**：01 用了 `order`，而 `hr`、`production` 模块均为 `sort_order`。

## 数据事实（2026-09-14 勘查，`equipment.equipments`，`is_deleted=false`，2972 行）

| 列 | 类型 | 可空 | 实际空值 | 排序结论 |
| --- | --- | --- | --- | --- |
| `asset_no` | varchar(50) | **NO** | 0 | 需自然序改造；NULLS LAST 是死代码 |
| `name` | varchar | NO | — | 直接排序 |
| `status` | varchar | NO | — | 中文枚举，需业务序而非字典序（D5） |
| `created_at` | timestamptz | NO | — | 已有 |
| `department_id` | uuid | YES | **0** | **不能按 UUID 排**，需按部门名称（D4） |
| `commissioning_date` | date | YES | 2 | 唯一真正需要 NULLS LAST 的列 |
| `current_cost` | float8 | YES | 0 | NULLS LAST 仅作防御 |
| `book_value` | float8 | YES | 0 | NULLS LAST 仅作防御 |

`asset_no` 格式分布：

| 形态 | 行数 | 长度 | 范围 | 词法序是否正确 |
| --- | --- | --- | --- | --- |
| `Z` + 7 位数字 | 2015 | 定长 8 | `Z0100001 .. Z0500326` | ✅ 正确（定长零填充） |
| 纯数字 | 957 | 变长 4–7 | `0000002 .. 59071` | ❌ 错误 |
| 其他形态 | 0 | — | — | — |

纯数字段 `asset_no::bigint` 无碰撞（不存在两个不同字符串映射到同一数值），数值化排序安全。

**规模结论**：2972 行，排序开销可忽略，本期不为性能引入索引或游标分页。

## API Contract (v2)

- **Parameters**：
  - `sort_by` (**Enum string**): 必须为白名单中的 8 项之一。OpenAPI schema 需明确列出枚举值，以便前端生成类型。
  - `sort_order` (string：`asc` | `desc`) — 由 v1 的 `order` 收敛而来（D1）
- **Whitelist**（8 项，与前端可点列严格一一对应）：
  `asset_no`、`name`、`commissioning_date`、`current_cost`、`book_value`、`department_name`、`status`、`created_at`
- **Default**：`sort_by='asset_no'`、`sort_order='asc'`，后端在参数缺失时兜底
- **NULL handling**：按列声明，不再是全局 `NULLS LAST`。仅 `commissioning_date`、`current_cost`、`book_value`、
  `department_name` 适用；`asset_no`/`name`/`status`/`created_at` 为 NOT NULL，不加空值语义
  （依据见「数据事实」表，落地见 Testing Decisions「空值断言改判」）。
  实现为对这些列单独套 `nulls_last`，而非在语句尾部统一追加
- **Invalid input**：未知 `sort_by` 或非法 `sort_order` → `422`，错误体列出支持字段（D12）。
  禁止 v1 的静默兜底
- **Stability**：所有排序末尾追加 `Equipment.id` 作为 tiebreak（D6）

## Goals

- 用户能对台账高频列稳定切换排序方向，顺序符合业务直觉（编号自然序）。
- 排序状态可分享、刷新后保持，且是列表查询状态的唯一真相。
- 不支持的排序字段明确失败，不静默改变用户看到的结果。
- 任何排序组合下分页稳定（同一查询重复执行行序一致）。

## Non-goals

- 多列组合排序、排序偏好持久化、跨模块统一排序中间件。
- 为排序引入游标分页或新索引。
- 提高表格行密度（v1 的 56px 方案已否决，见 D8）。

## User Stories

1. 作为**设备管理员**，我希望按资产编号的自然数值序排列（`0001` 在 `0000002` 前），以便按编号段连续核对设备。
2. 作为**财务专员**，我希望按投用日期和当前成本排序，以便筛出最早投用的设备、观察设备价值分布。
3. 作为**设备管理员**，我希望按归属部门排序时看到的顺序与部门名称列文字一致，而不是某种内部 ID 的顺序。
4. 作为**用户**，我希望点击表头切换排序、能明确看出当前哪一列哪个方向，并一步恢复默认。
5. 作为**用户**，我希望刷新或分享 URL 后仍保持我调整过的排序视角。
6. 作为**用户**，我接受极少数缺失投用日期的设备排在末尾，不希望它们混在正常序列里干扰核对。

> v1 的 story 2「财务专员希望空资产编号排在末尾」已删除：`asset_no` 在库中为 NOT NULL 且零空值，
> 该场景不可能发生。其真实意图（未登记设备可达）由 D11 的排序状态标签 + 现有筛选栏承接。

## Implementation Decisions

### D1 — 参数名收敛为 `sort_by` + `sort_order`

对齐 `app/modules/hr/api.py:1160`、`app/modules/production/product/output_api.py:51`。
成本已核实为最小：受影响仅 `api/equipment.py:254`、`service/equipment.py:239,244`、`repository/equipment.py:384`
三处形参（均位置传参）；`public_api.py:34,51` 用关键字参数且不传排序，不受影响；前端零消费者。
**必须在 02/03 接线之前完成**，否则成本立刻上升。

**已落地（01）**：一次改完 `api` → `service` → `repository` 三层形参与 OpenAPI，成本核实成立——
实际只动三处位置传参，`public_api.py` 的关键字调用不受影响，前端当时零消费者故零改动。
教训是这类「跨层改名 + 重生成契约」必须在接线前做，一旦前端开始消费 `order`，就要么留兼容分支要么改两处。

### D2 — 白名单与前端可排序列严格一致

| `sort_by` | 表头列 | 排序键 |
| --- | --- | --- |
| `asset_no` | 资产编号 | 自然序表达式（D3） |
| `name` | 设备名称 | 原列 |
| `commissioning_date` | 投用日期 | 原列 + NULLS LAST |
| `current_cost` | 当前成本 | 原列 + NULLS LAST |
| `book_value` | 账面净值 | 原列 + NULLS LAST |
| `department_name` | 归属部门 | 部门名称表达式（D4） |
| `status` | 设备状态 | 业务序（D5） |
| `created_at` | 创建时间 | 原列 |

两侧各自硬编码同一份清单不可接受。以后端 OpenAPI 为源：`sort_by` 用 `Literal` 声明，`pnpm generate:api`
后在 `openapi.json` 里反映为 8 值 enum，生成类型 `EquipmentSortBy` 即联合类型。注意 **TS 联合类型是编译期产物、
运行时不可 `Object.keys` 枚举**，所以前端不能真的从类型「派生」出列清单；正确形态是：前端维护一份运行时清单
（列 key → 表头列的映射），用 `EquipmentSortBy` 做 `satisfies`/`Record` 编译期完整性校验——后端增删字段即编译报错，
达成「不漂移」。未列入的列**不渲染排序 affordance**（不是点了没反应，而是根本不显示可点态）。

**已落地（02）**：运行时清单 = `lib/api/equipment-query.ts` 的 `SORT_BY_VALUES`（`Record<EquipmentSortBy, true>`，
对外导出为 `EQUIPMENT_SORT_FIELDS`）；列 key 映射 = `components/equipment/sorting.ts` 的 `SORT_BY_COLUMN_KEY` +
`sortableColumnKey`。**归属部门列表 key 是 `department`、契约字段是 `department_name`**，两者必须靠这层映射区分，
直接把列 key 当 `sort_by` 发出会得到 422。

编译期校验只挡「类型缺字段」，挡不住「`backend/openapi.json` 过期而 `generated/schema.ts` 没重生成」——
这种漂移两侧类型仍然自洽。因此额外加一条运行时断言（`e2e/equipment-sorting.spec.ts`）：读仓库内
`backend/openapi.json`，取 `sort_by` 的 enum 值集，与 `EQUIPMENT_SORT_FIELDS` 逐项相等。
后端改白名单但未重新导出契约时该用例即红，把「生成物收尾」从人工记忆变成 CI 事实。

### D3 — 资产编号用「前缀 + 数值段」复合自然序键，不引入 migration

```sql
-- 语义：字母前缀优先，其后数值段按补零定长比较；无尾数值的异常编号单独成桶置后
-- 列名一律带 equipments. 限定：D4 会 LEFT JOIN identity.departments，其 id 列与 equipments.id 同名
-- regexp_match 结果下标必须加括号，裸写 regexp_match(...)[1] 是 PostgreSQL 语法错误
ORDER BY
  (CASE WHEN equipments.asset_no ~ '[0-9]$' THEN 0 ELSE 1 END) ASC,
  coalesce((regexp_match(equipments.asset_no, '^[A-Za-z]*'))[1], '') ASC,
  lpad(coalesce((regexp_match(equipments.asset_no, '[0-9]+$'))[1], ''), 12, '0') ASC,
  equipments.asset_no COLLATE "C" ASC,
  equipments.id ASC
```
-- DESC 时前四段各自反转方向；末尾 `equipments.id ASC` 恒定（tiebreak 只需确定性，不随方向翻转）

- `lpad(…, 12)` 覆盖当前最大 7 位并留增长余量，避免比较时 `::bigint` 溢出。
- 末段 `COLLATE "C"` 作最终 tiebreak，保证同数值不同写法（`0001` 与 `1`）顺序确定。
- 异常编号（无尾数值）落独立桶并置后，不抛错——脏数据不得让整个列表页 500。
- **不采用** stored generated column + 索引：2972 行下表达式排序开销可忽略，migration 与回填的运维成本换不到收益。
  规模增长后再迁移（R2）。
- **实测（01）**：表驱动用例把三类样本钉成一条升序链——自定义变长编号先按数值段递增、字母前缀桶整体靠后
  （`009900001 < 09900002 < 9900003 < 9900004 < Z9900005`），无尾数值的异常编号落在独立桶并置后且不抛错。
  `lpad(…, 12)` 相对当前最大 7 位留有 5 位余量。

### D4 — 部门排序键改为名称，不是 UUID

01 的 `SORT_MAP` 把 `department_id` 映射到 UUID 列，而界面显示部门名称，两者顺序无关。
需按部门名称排序（join 或名称表达式，取实现上更省事的一侧），名称空值置后。属 01 返工，非新功能。

**已落地（01）**：取 join 侧——`sort_by == "department_name"` 时 `outerjoin(Department, ...)` 后按 `Department.name`
排序并 `nulls_last`（`repository/equipment.py:417-419,482-483`）。join **只在该 sort_by 下开启**，不常驻查询：
无部门条件时多一次 join 会拖慢所有排序。副作用是 D3 的表达式必须把列名写成 `equipments.` 限定，
否则与 `identity.departments.id` 同名歧义直接报错——契约测试里部门排序与名称列单调一致已覆盖。

### D5 — 设备状态按业务序而非字典序

`status` 是中文枚举（在用/备用/维修中/停用/报废），字典序无业务含义。按固定优先级映射排序，
使「维修中」等设备在升序下自然聚簇。默认优先级取「异常态在前」：维修中 > 停用 > 报废 > 备用 > 在用，**需业务确认**（R4）。

**已落地（01）**：`case()` 映射 `_STATUS_SORT_PRIORITY`，未列入清单的状态取 `else_=99` 置后——
脏状态值不得让整个列表页 500，也不得挤进正常业务序列中间。优先级数值本身仍待 R4 确认，
调整时只改 `_STATUS_SORT_PRIORITY` 一处，分页守恒用例（全量逐页无重无漏）会兜住误改。

### D6 — 每个 ORDER BY 追加唯一 tiebreak，保证分页稳定

offset 分页 + 非唯一排序键会导致同一行在相邻页之间漂移。服务端所有排序末尾必须追加 `Equipment.id`。
v1 只在 Out of Scope 里排除了游标分页，并把行序抖动记为「已知限制」接受——但 tiebreak 是低成本正确性修复，
不该和游标分页绑成一件事。

**实测（01）**：仅「重复执行同一参数得到同一序列」不足以证明 tiebreak 生效——它只测单次确定性。
补了两条更硬的：① 构造排序键完全打平的数据，逐页取到取完，断言并集无重复、无遗漏、且等于全集；
② 全量 2972 行按 `status`（大量同值）排序，逐页扫完 15 页做**行数守恒**断言。

### D7 — 复用 antd 内置排序，撤销自研表头组件

v1 的「自定义 Sort Icon（方向性渐变下划线）」删除。antd Table 的 `sorter: true` 已提供方向箭头、`aria-sort`、
键盘可达性与 `onChange(pagination, filters, sorter)` 接线，仓库且已有同构先例
`src/app/(dashboard)/production/product-output/[workshop]/[productId]/page.tsx:557-650`。
自研指示器会替换内置单元格、连带丢掉 `aria-sort`，而 ticket 04 又要求验证它。

**能力边界（实测）**：antd v6 表头单元格的 `onKeyDown` 只处理 `Enter`（`node_modules/antd/es/table/hooks/useSorter.js:166`），
**不响应 Space**。因此 ticket 04 原写的「Enter/Space 键盘切换」只能验收 Enter + `aria-sort` 变化，
Space 记为已知偏差（R6）而非静默删断言。同理，第三次点击 `sorter` 会给出 `order === undefined`，
`EquipmentTable.tsx` 把它映射为「回落默认序」，与 `FilterSummary` 的「恢复默认」共用同一语义——
避免出现两种「取消排序」得到不同 URL。

### D8 — 保持 `size="small"`，用排版建立秩序感而非加大行高

容器高度被 `EquipmentPage.tsx:232` 锁为 `calc(100vh - 280px)`，37px→56px 使单屏可见行从约 16 降到约 10，
20 条/页需要更多滚动，与「掌控数据秩序」目标相反。且 `EquipmentTable.tsx:79` 把 `h - 37 - 56` 写成魔法数，
改密度会静默算错 `scroll.y`。

替代（「精密仪器」风格的实际落点）：
- `asset_no`、标签号、设备位号、日期、金额列使用等宽字体 + `font-variant-numeric: tabular-nums`，数位对齐。
- `current_cost`、`book_value`、数量列右对齐（当前左对齐，`EquipmentTable.tsx:178-179`）。
- 当前排序列以 theme token 表达（表头底色/下划线），不新增组件、不改行高。

**已落地（02）**：等宽数字统一走 `.equipment-cell-mono`（`styles/industrial-theme.css`），列渲染由
`monoCell()` 一处套用，避免每列各抄一份 font-family 字面量。魔法数问题按 D8 指出的方向修掉了——
`scroll.y` 改为用 `ResizeObserver` 实测 `.ant-table-thead` 底边与 `.ant-table-pagination` 顶边，
不再写死 `h - 37 - 56`，因此后续调行高或批量操作栏出现/消失都不会静默算错滚动区高度。

### D9 — 动效限于表头指示器与数据切换

维持 v1 已接受的「不做行重排 FLIP」。补充：换序时不整表重挂载，
表头方向切换过渡 ≤150ms + tbody 交叉淡入，并遵守 `prefers-reduced-motion`。

**已落地（02）**：淡入用**双同名 keyframes + 相位属性**实现——容器上 `data-fade="a"|"b"`（`EquipmentTable.tsx:266-272`）
随 `sortBy/sortOrder/page` 切换，`animation-name` 变化即在该 DOM 上重启动画。
不选 `key` 重挂载：重挂载会丢掉 antd 的列宽测量与滚动位置，表现为换序后横向滚动条弹回最左。
整段动效包在 `@media (prefers-reduced-motion: no-preference)` 内，降级时完全不声明动画。
代价：相位由 effect 内 `setState` 驱动，会触发一次 `react-hooks/set-state-in-effect` 警告——
这是「用属性切换重放动画」的固有形状，接受警告而不是改回重挂载。

### D10 — URL 为查询状态唯一数据源，先收敛再加排序

现状三份真相：`EquipmentTable.tsx:51-52` 的 `localPage/localPageSize`、`stores/equipment.ts:44-45` 中对设备列表
已失效的 `page/pageSize`、以及 03 准备新增的 URL 参数。收敛为 URL 单一来源，排序与分页、筛选同构。
排序变化时重置到第 1 页（v1 决策保留）。

必须一并修复：`EquipmentPage.tsx:160-163` 的 fetch effect 缺失 `fetchData` 依赖且硬编码 `fetchData(1, 20)`，
用户选定的 `page_size` 会在任何筛选变化时被重置；把排序加进同一 effect 会原样复现该缺陷。

SSR 侧 `assets/page.tsx:44` 目前硬编码 `{page:1, page_size:20}` 且忽略查询串。不同步读取会导致：
刷新一个带排序的 URL 时先渲染默认序首屏、再由客户端二次请求覆盖，产生可见闪变。
决策：服务端组件读取 `searchParams` 并传入同一查询构造函数，使首屏即落在正确排序视角。

**已落地（02），含一处范围收敛**：URL 只承载 **排序 + 分页**，筛选条件仍由 `stores/equipment.ts` 单一持有。
比 v1 设想的「排序与分页、筛选同构」窄，理由是筛选项含分类/位置的树形 id 与 `keyword`，全部塞进 URL 要额外
设计序列化格式，属于另一件事；但「同一状态不得有两份真相」这条已经落实——`localPage/localPageSize` 与
store 里对列表失效的 `page/pageSize` 都已删除，分页与排序的唯一写入点是 `patchQuery`。

其余实现事实：
- `writeEquipmentUrlQuery` 在值等于默认时**删除**参数（分享链接保持短），并原样保留其它未知参数（不清空别人的查询串）。
- SSR 与客户端共用 `parseEquipmentUrlRecord` / `parseEquipmentUrlParams`（同一套解析 + 同一套白名单校验），
  首屏即落在 URL 的排序视角，闪变消除。
- 被丢弃的脏参数以 `rejectedSort` 返回，客户端交给 `FilterSummary` 提示；**SSR 侧只能静默丢弃**
  （服务端组件无法弹 message），因此该提示是「客户端水合后出现」，不是首屏即有。
- fetch effect 的缺陷按 D10 要求修复：改为 `filterSignature + page + page_size + sort` 组成的 `fetchKey` 去重，
  筛选变化时强制 `page: 1`，`page_size` 不再被任何筛选变化重置回 20。

### D11 — 排序状态标签并入 `FilterSummary`，不新增胶囊

`FilterSummary.tsx` 已在渲染可点击、可清除的状态标签（`📍 位置`、`🏷️ 分类`）。右上角再放「排序状态胶囊」
会与之竞争同一个「当前查询状态」出口。改为在 `FilterSummary` 追加排序 token 与「恢复默认」动作；
注意该组件在无任何筛选时 `return null`，排序非默认时也需渲染。

**已落地（02），并据此关闭 R5**：排序列被列配置隐藏时**保留排序、不回落默认序**。理由是 URL 是唯一真相——
`?sort_by=book_value` 的分享链接打开后若因为该列被隐藏就悄悄换成 `asset_no` 序，用户看到的数据与自己刚点过的
表头语义都不符，且地址栏与界面不一致比「排序列看不见」更糟。此时表头没有指示器可点，
当前排序完全由 `FilterSummary` 的排序标签承载（标签文本来自 `SORT_BY_LABEL`），「恢复默认」仍可一键退出。
连带事实：默认可见列（`EquipmentTable.tsx` 的 `visibleColumns` 初始化）为 7 项，**不含 `current_cost` / `book_value`**，
因此 E2E 要覆盖这两列排序必须先在列配置弹窗里勾选——这不是缺陷，是验收脚本的前置步骤。

### D12 — 未知排序字段显式失败

`SORT_MAP.get(sort_by, asset_no)` 的静默兜底改为 `422`，错误信息带支持字段列表。
实现机制：`sort_by`/`sort_order` 用 `Literal` 声明（FastAPI 自动产出 422，且 OpenAPI 反映为 enum 供 02 类型对齐）。
这是 D2 的前置保障：没有它，前后端清单漂移只表现为「排序看起来生效了但结果是错的」。

**已落地（01/02）——「显式失败」必须做两半，只做后端那一半会新增一种坏体验**：
- **后端**：`Literal` 让 FastAPI 在进入业务代码前产出 422，且其 `msg` 天然列出全部 8 个合法值，
  满足「错误信息带支持字段列表」——已有用例断言响应体同时出现 `asset_no`/`book_value`/`department_name`。
  `repository` 里对未知 `sort_by` 抛 `ValueError` 只是防止越层直接调仓库，不是用户可见路径。
- **前端**：URL 是不可信输入。若把 `?sort_by=x` 原样发给后端，用户看到的是列表报错空转而不知原因。
  因此解析阶段就**丢弃**脏参数回落默认序，同时把被丢弃的原始值经 `rejectedSort` 交给 `FilterSummary` 明示，
  让用户知道「当前不是按你要的字段排」。语义与 D12 一致：不静默改变结果，而是把偏离摆在台面上。

## Testing Decisions

- **修正假测试（阻塞项）**：`tests/modules/equipment/test_sorting.py` 在测试函数内重新内联了一遍 `order_by`，
  从未调用 `repo.get_equipments`，因此改名、改白名单、改自然序前后它都是绿的。
  重写为真正调用 repository 并断言返回列表顺序，否则 ticket 01 的「Verify Repository layer generates correct SQL」不成立。
  **已修正**：现在全部用例走 `get_equipments(...)` / HTTP 端点，没有任何一处自己拼 `order_by`；
  改名、缩/扩白名单、改自然序都会让它变红（这正是它该有的性质）。
- **自然序表驱动测试**：覆盖前缀桶靠后 + 变长数值段按数值递增（fixture 链 `009900001 < 09900002 < 9900003
  < 9900004 < Z9900005`，刻意避开与生产真实编号同值，防污染既有 2972 行的断言）、两种格式混排、
  以及无尾数值异常编号不抛错且置后。
- **分页确定性测试**：同一排序参数重复执行序列一致（单次确定性）+ 排序键完全打平时逐页取全量无重无漏（真 tiebreak）
  + 全量 `status` 逐页行数守恒（验证 D6）。
- **契约测试**：未知 `sort_by` → 422 **且响应体列出支持字段**；`sort_order` 非 `asc|desc` → 422；
  部门排序结果与名称列文字单调一致（D4）。
- **空值断言改判**：撤销 v1 对 `asset_no` 的「NULL 稳定排在末尾」断言（该列 NOT NULL，永不可能有数据满足）。
  NULLS LAST 断言改挂到 `commissioning_date`（当前 2 行）与成本列，并按「列 × asc/desc」双参覆盖——
  只测 asc 会漏掉「desc 时 NULL 跑到最前」这种常见错法。断言用显式期望序列而非条件表达式，
  避免 `expected if order else ...` 写成恒真。
- **前端 e2e（Playwright 已配置）**：点表头 → URL 更新 → 刷新保持 → 恢复默认 → `page_size` 不被排序重置 →
  契约无漂移守卫（读 `backend/openapi.json` 比 `EQUIPMENT_SORT_FIELDS`）。落地时有三个绕不开的环境约束：
  ① 表格用 `fixed` 列 + `scroll.x`，窄视口下右侧固定列会**压住表头命中区**，点击落到相邻 `th`，
  故本组用例固定 `viewport 1680×950`；② `networkidle` 在本页不是稳定信号（存在轮询），等待一律改成
  断言 `aria-sort` 或行内容；③ 默认可见列不含 `current_cost`/`book_value`，这两列的用例需先在列配置弹窗勾选。
- **无障碍**：断言 antd 自动产出的 `aria-sort`（复用 D7 后免费获得，不需自建夹具）。
  键盘部分只验收 `Enter`——antd v6 不响应 Space（D7 / R6），用例注释里写明该边界而不是留个必红的断言。
- **生成物收尾（已完成）**：`sort_by` 在 `backend/openapi.json` 中确认为 8 值 `enum`，
  `generated/schema.ts` 已重生成，E2E 漂移守卫把它钉成 CI 事实。管线有两个非显然点：
  宿主机无 `uv`，导出必须在容器内跑（`docker exec -i erp-backend uv run python scripts/ci/export_openapi.py`）；
  且该脚本写的是**容器内** `/app/openapi.json`，必须 `docker cp` 回 `backend/openapi.json` 再跑 `pnpm generate:api`，
  否则会拿旧契约生成类型。

## 分票计划

| Ticket | 文件 | 内容 | 依赖 | 状态 |
| --- | --- | --- | --- | --- |
| 01（返工） | `01-backend-sort-api.md` | D1 参数名、D2 白名单扩至 8 项、D3 自然序、D4 部门排序键、D5 状态业务序、D6 tiebreak、D12 422、空值语义改按列、修正假测试、重新生成 API 类型 | 无 | 代码完成，待人工验收 |
| 02（重写） | `02-frontend-ui-sync.md` | D7 复用 antd `sorter`、D2 可点列以生成类型 `EquipmentSortBy` 做类型对齐、D10 URL 单一数据源（含 effect 依赖修复与 SSR 读 `searchParams`）、D8 排版与右对齐、D11 `FilterSummary`、D9 动效 | 01 | 代码完成，待人工验收 |
| 03（重写） | `03-integration-e2e.md` | 8 列逐列联调、筛选共存、刷新与分享 URL、422 负例路径、R5 隐藏列行为收敛、Playwright 用例 | 01, 02 | 代码完成，待人工验收 |
| 04（重写） | `04-qa-accessibility.md` | 按 Testing Decisions 验收：自然序、异常编号、分页确定性、空值改判、契约负例、`aria-sort`、测试真实性 | 03 | 代码完成，仅 R4 待业务确认 |

01→02 是硬依赖（前端可点列必须等于后端白名单）。v1 把 02 标为「can start immediately」会让两侧各写一份清单，
正是 D12 要防的漂移。

验收口径（复核时按此跑，不要重新推导）：
`cd backend && uv run pytest tests/modules/equipment/test_sorting.py tests/modules/equipment/test_import_v4_contract.py -q`
→ 36 passed（宿主机无 `uv` 时用 `docker exec -i erp-backend ...`，且需 R8 的 tests 挂载生效）；
`cd frontend && pnpm exec playwright test e2e/equipment-sorting.spec.ts` → 10 passed。

## Out of Scope

- **游标（keyset）分页**：维持 offset。2972 行下无必要性，正确性由 D6 tiebreak 保障。
- **多列组合排序**。
- **排序偏好持久化**（localStorage 或服务端用户配置）。
- **行密度调整与虚拟滚动**。

## Risks & Open Questions

- **R1（业务，优先）**：957 条纯数字编号疑似历史遗留。若业务能统一为 `Z` 前缀定长，D3 自然序需求整体消失。
  现状：D3 已按混合格式实现并被测试钉住，因此**清理与否不再阻塞交付**，只决定 D3 那段表达式将来能否删除。
- **R2（成本，已实测）**：2972 行下 8 个字段 × 2 方向的首页取数均在几十毫秒级（单字段首页约 0.04s，
  `status` 全量 15 页扫完约 0.25s），**本期不引入索引**。用例把「首页 < 2s」写成断言而非依赖人肉感受；
  数据量到 5 万行以上时该用例仍会先给出信号，届时按 D3 迁移 stored generated column + 索引。
- **R3（契约，范围大于本模块）**：`api/equipment.py:265-267` 对每行 `await _equipment_to_response(e, db)`
  造成 N+1，排序不加剧它但列表是热点。同期发现更普遍的一条：模块内多个端点返回注解与 `response_model`
  用了 `ApiResponse`（`data: Any`），OpenAPI 生成不出字段，前端只能手写类型兜底。
  **本期已修 v4 导入的 `preview` / `batch` 两个端点**（新增 `ImportV4PreviewApiResponse` /
  `ImportV4BatchApiResponse` 精确 envelope + `test_import_v4_contract.py` 钉住引用与字段集），
  其余端点与 N+1 一起另开票，不混进排序。
- **R4（业务，仍开放）**：D5 的状态业务序需确认，当前默认优先级是推测。
- **R5（已关闭）**：隐藏排序列的行为由 D11 决策收敛为「保留排序 + `FilterSummary` 承载标签」。
- **R6（无障碍偏差）**：antd v6 表头不响应 Space，键盘切序仅 Enter。若要满足「Space 也可」需自建
  `onKeyDown` 并因此替换内置单元格渲染——与 D7（复用内置、白拿 `aria-sort`）直接冲突。
  建议接受现状并向无障碍验收方说明，不为一个按键放弃整套内置语义。
- **R7（已关闭 — 布局改造为三段式一屏显示）**：台账列多 + `scroll.x`，「操作」列 `fixed: 'end'` 在窄视口下覆盖表头命中区，
  用户点击可能落在相邻表头上。E2E 用 1680 视口只是**绕开**它，没有修它。
  
  **迭代 v1（自然滚动方案被否决）**：曾尝试「自然页面滚动 + sticky 表头」，但用户反馈无法在一屏内看到完整内容，
  分页控件需要滚动才能看到，体验不佳。
  
  **迭代 v2（当前方案：三段式一屏显示）**：经用户明确要求，改为「三段式布局 + 表格内部滚动」，确保：
  - 整个页面固定高度（`100vh`），无页面级滚动
  - 第一段（控制层）：标题 + 统计 + 筛选，紧凑化设计
  - 第二段（数据层）：表格区域内部滚动（`overflow: auto`），表头 sticky 固定
  - 第三段（导航层）：分页控件固定在底部，始终可见
  
  具体改动：
  - `frontend/src/app/(dashboard)/equipment/assets/EquipmentPage.tsx` — 页面根容器 `height: 100vh; overflow: hidden`，
    三段式 flex 布局，第一段压缩间距，表格区域添加 `overflow: auto`
  - `frontend/src/components/equipment/EquipmentTable.tsx` — 添加 `scroll={{ x: 'max-content', y: '100%' }}`，
    表头通过 sticky 固定在表格区域顶部
  - `frontend/src/components/equipment/StatsCards.tsx` — 压缩样式，数字 20px，标签 11px，内边距 8px 12px
  - `frontend/src/lib/api/equipment-query.ts` — `DEFAULT_EQUIPMENT_PAGE_SIZE` 从 20 改为 15
  - `frontend/src/styles/industrial-theme.css` — 移除自定义滚动条样式

  **效果**：无页面级滚动，三段内容一屏显示；表格内部可滚动，表头固定；分页控件始终可见。

  **迭代 v2（用户反馈：去锁高后仍看不到统计与表头）**：v1 改完发现真正的问题是「纵向密度」而非
  「滚动」——标题 + 5 张大卡 + FilterSummary + 筛选条 + 表头堆 ~412px，首屏只能看 7 行。再迭代：

  - **StatsCards 改用 compact 模式**（已有 `compact={true}` 分支，单行胶囊条）
  - **FilterSummary 新增 `compact` 模式**：inline pill 标签组，无外壳、无总数、无「恢复默认」；与 default 模式共享 `tags` 数组避免双份漂移
  - **新建 `EquipmentFilterBar`**：把筛选 Select/Input + inline 标签 + 列配置/导入/新增按钮外移到独立文件，标签始终 inline 不换行
  - **EquipmentPage 改造**：标题 → sticky 工具栏（top:0 / z-index:3）→ flex 行（sticky 侧边栏 top:var / 右侧卡片仅 foldButton + Table）
  - **ResizeObserver 测工具栏高度 → CSS 变量 `--equipment-toolbar-h`**：侧边栏读这个变量决定自己的 sticky top，初值兜底 96px
  - **Modal 状态上提到 EquipmentPage**：`columnConfigOpen` / `importOpen` / `visibleColumns` 由 EquipmentPage 持有，按钮在工具栏里、模态浮在页面层；`EquipmentTable` 接收 `visibleColumns` 受控展示
  - **侧边栏也做 sticky**：`position: sticky; top: var(--equipment-toolbar-h, 96px); max-height: calc(100vh - var(--equipment-toolbar-h, 96px) - 24px);` —— 工具栏下方常驻分类/位置树
  - **改动文件**：
    - `frontend/src/app/(dashboard)/equipment/assets/EquipmentPage.tsx` — sticky 工具栏 + sticky 侧边栏 + ResizeObserver + modal 状态上提
    - `frontend/src/components/equipment/EquipmentFilterBar.tsx` — 新建，承载筛选条 + inline 标签 + 操作按钮
    - `frontend/src/components/equipment/FilterSummary.tsx` — 新增 `compact` prop，default/compact 共用 tags
    - `frontend/src/components/equipment/EquipmentTable.tsx` — 删除 filter bar / ColumnConfigModal / EquipmentImportModal / visibleColumns state + localStorage useEffect；清理 statusConfig/statusOptions 死代码
    - `frontend/src/components/equipment/index.tsx` — 导出 `EquipmentFilterBar` / `EquipmentImportModal` / `ColumnConfigModal`；barrel 文件加 `'use client'`
    - `frontend/src/styles/industrial-theme.css` — 新增 `.equipment-sidebar-sticky` 规则

  `pnpm typecheck`（tsc --noEmit）通过，E2E 选测 `equipment-sorting.spec.ts` 中「列配置」按钮（`getByRole('button', { name: '列配置' })`）与「排序参数无效」tag 选择器仍命中（按钮文字未改、tag 文本仍含 `排序参数无效`）。

  **迭代 v3（用户反馈：v2 落地后表头与数据行位置冲突）**：v2 在 `industrial-theme.css` 给 `.equipment-ledger
  .ant-table-thead > tr > th` 加了 `position: sticky; top: var(--equipment-toolbar-h, 96px)`，
  实测却出现两类视觉冲突：

  1. 主表头被推到数据行中间位置（截图：表头一行浮在第 3 条设备数据附近）；
  2. 下拉设备台账弹窗里的表格里表头同样错位，与 `fixed: 'end'` 操作列的重复表头叠加。

  根因是 **antd v6 + `scroll.x: 'max-content'` 的 sticky 不可用**：`.ant-table-container` 被设为
  `overflow-x: auto`，按 CSS 规范一个轴上 `auto` 会让另一个轴也建立滚动上下文，sticky 元素实际粘在
  容器内部而非页面顶端。再加上 antd v6 对 `fixed` 列复制 thead（main + left-fixed + right-fixed 共 3 份），
  三份表头在同一容器里各自尝试 sticky，相互叠加后视觉错位。

  **迭代 v3 → v4（两次浏览器实测后收敛到 antd 内置 sticky）**：v2 在 `industrial-theme.css` 给 th 手写
  `position: sticky; top: var(--equipment-toolbar-h)`，实测表头被推到数据行中间、与 fixed 列重复表头叠加。
  v3 先假设根因是 `'max-content'` 的容器滚动上下文，改 `scroll.x: 2980` + 去 `min-w-0` 想让
  `.ant-table-container` 不溢出——实测更糟：**表头行渲染但列名全部空白**，滚动时表格数据穿透 sticky
  工具栏，导入/新增按钮浮在数据行上。

  **根因（读 rc-table 1.10.2 源码确认）**：`scroll.x` 存在且无 `scroll.y` 时，rc-table 给滚动容器
  `.ant-table-content` 加 `overflow-x: auto; overflow-y: hidden`（`Table.js` scrollXStyle/scrollYStyle 分支）。
  `overflow-y: hidden` 让容器自身成为 sticky 吸附框，th 上的 `top: N` 只会在容器内部下推表头、
  与数据行叠加或被裁切——手写 th sticky 在这个结构里**原理上不可行**，与 `scroll.x` 取值无关。

  **最终方案（v4）**：改用 rc-table 内置 `sticky` prop。开启后 rc-table 走 Fixed Header 分支，
  渲染**独立表头** `.ant-table-sticky-holder`（`FixedHolder`：`position: sticky` 由 antd 官方样式提供、
  `top: offsetHeader` 内联样式、z-index 按列数自动 `calc(列数×2 + zIndexTableFixed + 1)`），
  表体在 `.ant-table-body` 内横向滚动、表头滚动位置由 rc-table JS 同步。好处：

  1. 表头不再依赖 th 粘性，`overflow-y: hidden` 容器影响不到它；
  2. 横向滚动回到表格容器内部——工具栏不再被推走（v3 曾让整页横滚、工具栏滚出视口）；
  3. 附带 viewport 底部的 sticky 横向滚动条（StickyScrollBar），宽表在窄视口下可拖动；
  4. fixed 列与 sticky 表头的 z-index 全部由 antd 自动分层，无需手写覆盖。

  实际改动三处文件：
  - `frontend/src/components/equipment/EquipmentTable.tsx` — `scroll` 回到 `{ x: 'max-content' }`；
    新增 `sticky={{ offsetHeader: stickyTop }}`，`stickyTop` 为父组件传入的工具栏实测高度。
  - `frontend/src/app/(dashboard)/equipment/assets/EquipmentPage.tsx` — ResizeObserver 同时写
    state `toolbarH` 与 CSS 变量；`toolbarH` 传给 `EquipmentTable` 的 `stickyTop`；right-card
    恢复 `min-w-0`（横向滚动回表格内部后，卡片不再需要被内容撑宽）。
  - `frontend/src/styles/industrial-theme.css` — 删除 v2/v3 的 th sticky 规则与 fixed 列 z-index
    覆盖，留注释说明为什么必须走内置 sticky。

  教训：给 antd Table 做 sticky 表头，先查 `scroll` prop 引发的容器 overflow 结构，**用组件内置能力
  （`sticky` prop）而不是在手写 CSS 里和它的布局对抗**。v2/v3 两次失败都是没先读 rc-table 源码、
  按「普通 div + sticky」的心智模型猜浏览器行为。

  `pnpm typecheck`（tsc --noEmit）通过，E2E 选测 `equipment-sorting.spec.ts` 中「列配置」按钮与
  「排序参数无效」tag 选择器仍命中（按钮文字未改、tag 文本仍含 `排序参数无效`）。
- **R8（环境，需审批）**：宿主机无 `uv`、`backend/tests/` 未挂载进容器，导致跑测试要每次 `docker cp`。
  已在 `docker-compose.dev.yml` 加 `./backend/tests:/app/tests:ro`。该文件属**受保护部署文件**，
  改动经用户明确指示但**仍需架构负责人批准**，且只在下一次 `docker compose up -d` 后生效；
  `docker compose config` 已验证合法，运行中的栈未重建。
- **R9（既有失败，非本期引入）**：设备模块另有 7 个用例长期红，源于 `service/equipment.py:501` 的
  「安全熔断：Excel 中缺失 2009 台在用设备」，与排序无关。复核时按验收口径只跑排序两个文件即为全绿，
  跑整模块会看到这 7 个红——不要误判成本期回归。
