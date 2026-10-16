# 能源管理模块 PRD

> 版本 v1.0 · 2026-10-15 · 分支 `lzhc-zhuang-energy` · 基线 commit `386c23c8`
> 覆盖范围：`backend/app/modules/energy/` + `frontend/src/{app/(dashboard)/energy,components/energy,actions/energy.ts,lib/api/*/energy.ts,stores/energy.ts,types/energy.ts}`

## 0. 文档定位与维护规则

**定位**：能源模块的**唯一功能规格书**。回答四个问题：这个模块为谁解决什么问题、数据从哪来到哪去、每个页面的行为边界在哪、出了问题谁来怎么修。

**与其它文档的关系**（平级互引，不隶属）：

| 文档 | 职责 | 本文如何引用 |
|---|---|---|
| [energy-bitable-field-mapping.md](./energy-bitable-field-mapping.md) | 月度交叉表**字段契约**：表结构、30 个实体的四侧叫法对照、9 条别名、FAQ | 第 4 章链路 1、第 3 章车间实体 |
| [energy-workshop-unification.md](./energy-workshop-unification.md) | 「车间实体统一 + 分布拆分」**单个工作包**的变更说明与验收实测 | 第 13 章变更记录、第 10 章修复脚本 |
| [AGENTS.md](../../AGENTS.md) | 全仓库工程规范 | 全文冲突判定依据，第 12 章缺陷登记引用其条款 |
| `backend/openapi.json` → `frontend/src/types/generated/schema` | 接口**字段级**契约 | 第 7 章只列路径+用途+调用页面，字段一律指向这里 |

**维护规则**

1. 新增/删除/改名一个页面 → 必须同步第 5 章对应小节和第 7 章「调用页面」列。
2. 新增字段或改变**计算口径**（汇总范围、分档阈值、单位、判重键）→ 必须先改第 6 章，再改代码。口径与代码不一致时，以第 6 章为准并登记缺陷。
3. 新增落库数据源（第六张来源表、第二种导入方式）→ 改第 4 章链路表 + 第 9 章 runbook。
4. 发现缺陷 → 进第 12 章登记表（编号 `D-xx`），不要散落在 commit message 里。
5. 每次提交涉及能源模块 → 第 13 章追加一行。
6. **文档内禁止出现** `app_token`、`table_id` 取值、飞书链接、任何凭证或连接串。环境变量只写名字，不写值。
7. 本文出现的**业务口径**（第 1、2、6 章）已由能源模块负责人 2026-10-15 逐条确认，确认结论标注在对应小节；未经确认的推断不得写成口径，只能写成「现状描述 + 待确认」。

## 1. 业务目标与范围

### 1.1 目标

| # | 目标 | 落地形态 | 判据 |
|---|---|---|---|
| G1 | **全厂能耗追溯**：任何一个车间在任意时间窗内用了多少电/水/汽/气，可查到、可核对到飞书源表 | 总览页 + 月度记录页 + 月度交叉表导入链路 | 库内 `energy_monthly_records` 与源表逐车间逐月可对齐（第 4 章链路 1 验收） |
| G2 | **单耗考核**：车间月度电单耗（kWh/kg）与目标值对比，给出偏差与原因分析 | AI 分析页 + 单耗目标 + 偏差分档 | 第 6 章 6.4 公式与分档可复现 |
| G3 | **超标预警**：日用量超过警戒线时生成可处理的预警记录 | 日表导入 + 预警管理页「预警记录」Tab | 第 6 章 6.5 分档规则；记录状态可流转到已处理/已忽略 |

### 1.2 非目标（本期明确不做）

- **不做实时 SCADA**。采集是小时粒度、可补采的轮询（第 4 章链路 5），不承诺秒级/分钟级实时性，不接入控制回路。
- **不替代设备台账**。`energy_device_configs` 只存「哪个平台的哪个采集点对应哪个车间/哪种能源」，不承载设备档案、维保、检定周期。
- **不做预警通知送达**（已确认）。`energy_alert_rules` 的 `notify_method` / `notify_users` / `notify_frequency` / `effective_time` 四个字段只是表单留存，**没有任何消费方**（无飞书/邮件/短信推送代码）。本期交付口径只到「预警记录落库 + 页面可查可处理」。见缺陷 `D-14`。
- **不接生产模块取真实产量**（已确认，列为下期）。本期单耗的产量与产品明细由用户在 AI 分析页手填。真实产量台账已存在于 production 模块（`GET /api/v1/production/product-output` 与 `/summary`、`/workshops`），下期对接必须走该模块的 `public_api.py`，不得直接 import 其内部实现；能源侧前端现在猜的 `GET /energy/production/output` 并不存在。见 `D-02`、`D-03`。
- **不做折标煤/碳排放折算**（已确认）。单耗分子只算电，四种能源不相加、不折算为标准煤当量。
- **不做车间层级树**。`EnergyWorkshop.parent_id` 字段存在但无维护入口、无递归查询，页面不展示层级。

### 1.3 范围边界

- 数据覆盖期：2024-01-03 ~ 至今（34 张月度表已全量回填）。
- 组织覆盖期：30 个未删除车间实体（第 3 章 3.2 与映射文档的叫法对照表）。
- 不在范围内：管线跑损统计、能源购售结算、峰谷电价成本优化、设备级能效对标。`energy_daily_data.cost` 字段可留存费用数值，但**没有任何页面消费它**（`D-41`）。

## 2. 角色与权限

**口径（已确认）**：本章只描述现状，不编造角色矩阵。

- 现状是 Phase 1：41 个端点处理函数（`backend/app/modules/energy/api.py`）全部声明 `current_user: RequiredUser`（`app/core/deps`），**模块内没有任何角色/权限区分**，没有 `require_permission`、没有数据行级过滤。另有 `GET /api/v1/energy/` 由 `app/shared/module_api.py:10` 的工厂注入，返回模块元信息。
- `current_user` 可能为 `None`（Phase 1 预留），因此「已登录」不等于「已识别到人」。预警记录的 `processed_by`、单耗目标的 `created_by` 在这种情况下会留空。
- 前端 `/energy` 全部路由靠外层登录（飞书 SSO cookie / JWT）挡住，`menu-config.ts:61-72` 无权限位；设置页 `app/(dashboard)/energy/settings/page.tsx:5` 复用全局 `ModuleSettingsClient`，模块内不判权限。
- 因此当前的实际安全边界是：**能登录系统 = 能改能耗数据、能删记录、能触发飞书导入与手动采集**。任何写端点都没有二次校验。

**风险与后续要求**（不是本期承诺）：

| 能力 | 当前谁能用 | 需要的最小约束 |
|---|---|---|
| 修改/删除月度记录、软删除车间 | 任意登录用户 | 只有能源管理员；删除需审计 |
| 设定/修改单耗目标 | 任意登录用户 | 车间负责人只能改自己车间 |
| 触发飞书导入 / 手动采集 | 任意登录用户 | 只有能源管理员，且做并发互斥 |
| 修改自动采集开关（设置页） | 任意登录用户 | 模块负责人（平台层 `core.module_settings` 已有自己的权限模型，不在本模块） |

## 3. 术语与数据模型

### 3.1 术语

| 术语 | 含义 |
|---|---|
| 车间实体 | `energy_workshops` 的一行，能耗归属的最小单位。同一部门在电/水/汽/气四种来源里的不同写法必须收敛成一个实体 |
| 规范实体名 | 落库用的唯一名称（如 `质量控制部`），别名（如 `QC`）不入库 |
| 月度交叉表 | 飞书多维表格内按 `YYYY-MM` 命名的一张表，行是车间、列是日期，同一张表内自上而下分电/汽/水三个 section |
| 日表 | 记录全厂单日总量与「警戒线」的多维表格数据表，预警判定的输入 |
| 警戒线 | 日表里逐行给出的阈值数值，业务口径的唯一预警基准 |
| 折算产量 | 各产品产量 × 折算系数 后相加的标准品产量（kg），单耗的分母 |
| 补采 | 采集进程落后于计划时，把缺失的整点一次性补齐（第 4 章链路 5） |

### 3.2 数据模型：10 张表逐个职责

Schema 统一为 `energy`，均继承 `app/shared/base_model.py` 的 `BaseModel`（`id`/`created_at`/`updated_at`/`created_by`/`updated_by`/`is_deleted`）。模型定义在 `backend/app/modules/energy/models.py`。

| # | 表 | 一句话职责 | 关键约束 | 主要写入方 |
|---|---|---|---|---|
| 1 | `energy_workshops` | 车间/部门主数据，能耗归属单位 | `uq_energy_workshop_code(code)` — **不含 `is_deleted`**，软删除行继续占编码（`D-08`）；`excluded_energy_types varchar[]` 标记合计行（6.1，迁移 `0069`） | `bitable_sync.py` 同步、车间管理页 CRUD、导入器 `_get_or_create_workshop` 兜底新建 |
| 2 | `energy_device_configs` | 三方平台采集点 ↔ 车间 ↔ 能源类型的映射与采集参数 | `uq_energy_device_config_platform_device(platform_code, platform_device_code, is_deleted)`；`collection_interval > 0` | 数据源配置页 CRUD、`seed_energy_data.py`（假数据，见 `D-19`） |
| 3 | `energy_data` | 小时粒度的采集值（累计值），带原始响应 | `uq_energy_data_device_timestamp(device_config_id, timestamp)` | 仅 `repository.upsert_energy_data`，由手动采集与调度循环调用 |
| 4 | `energy_collect_logs` | 每轮采集的批次结果（应采/成功/错误） | 无唯一约束 | `repository.create_collect_log`（`service.trigger_collection`、`scheduler._do_collect`） |
| 5 | `energy_monthly_records` | 月度交叉表/飞书导入的能耗明细，值列名叫 `value` | `uq_energy_monthly_record(workshop_id, energy_type, record_date)` — **不含 `date_range_end`**（`D-07`） | `bitable_cross_import.py`、`bitable_sync.py`、`feishu_import.py`、月度页 CRUD |
| 6 | `energy_daily_data` | 全厂单日四类用量 + 警戒线，预警判定输入 | `uq_energy_daily_data_date_type_category(date, energy_type, category)` | `bitable_daily_import.py` |
| 7 | `energy_alert_rules` | 预警规则**配置表单的留存**（monitor_metric/threshold_type/通知字段） | 六个 CheckConstraint 限定枚举 | 预警管理页「预警规则」Tab；**从不参与判定**（`D-01`） |
| 8 | `energy_alert_records` | 实际生成的预警事件与处理流转 | `rule_id` 可空（迁移 `0048`）；`alert_level`/`status` 枚举约束 | `bitable_daily_import.check_alerts`（`rule_id=None`、`unit=""`、无车间维度，`D-15`） |
| 9 | `energy_unit_consumption_targets` | 车间 × 月份的目标单耗（kWh/kg） | `uk_workshop_month(workshop_id, target_month)` | AI 分析页的目标弹窗（`POST/PUT /targets`） |
| 10 | `energy_product_conversions` | 产品 → 标准品折算系数 | `uk_product_name`；跨模块外键指向 `identity`（迁移 `0059`） | **无任何写入方**：没有 API、没有页面，`D-03` |

### 3.3 `energy_type` 四值与单位

| `energy_type` | 中文 | 单位 | 规范实体数 | 落库来源 |
|---|---|---|---|---|
| `electricity` | 电 | `kWh` | 27 | 月度交叉表电 section |
| `water` | 水 | `m³` | 20 | 月度交叉表水 section |
| `steam` | 汽（蒸汽） | `t` | 14 | 月度交叉表汽 section |
| `natural_gas` | 气（天然气） | `Nm³` | 1（仅 RTO） | 汽 section 尾部的天然气行（`D-06`） |

- 四值由 `energy_monthly_records` / `energy_device_configs` / `energy_alert_rules` 上的 CheckConstraint 强制。
- ⚠️ `models.py:32 EnergyType` 枚举**只有 electricity/water/steam 三值**，缺 `natural_gas`；代码里凡是取枚举的地方都不能表达气。列为 `D-05`。
- 数据源配置页与预警规则抽屉的能源类型下拉**也缺 natural_gas**（`D-16`）。

### 3.4 `record_date` 与 `date_range_end`

| 场景 | `record_date` | `date_range_end` | 例 |
|---|---|---|---|
| 单日读数 | 该日 | `NULL` | `2026-10-08` / `NULL` |
| 多日汇总（源表一列覆盖 2~3 天） | 范围**起始日** | 范围结束日 | `2026-05-30` / `2026-06-01` |

- 日期表头三种格式（`2026-06-02`、`2026-05-30-06-01`、`2026-07-01-03`）由 `_parse_date_header` 解析，其余写法解析为 `None` 并整列跳过。
- **跨天记录的读口径不唯一**：第 6 章 6.1 的汇总/分布/趋势按 `record_date` 单点归期，跨天记录整体算进起始日；第 6 章 6.4 单耗链路走 `service.prepare_daily_stats`（`service.py:575-618`），把 `value / days` **平均分摊到区间内每一天**。两套口径共存，页面数字不能互相对账。列为 `D-09`。
- `get_monthly_energy_total`（`repository.py:864-885`）用 `record_date >= start AND record_date < end` 且**完全不看 `date_range_end`**：跨月范围的记录会被漏计或错月。列为 `D-10`。

### 3.5 软删除口径

- 删除业务数据一律置 `is_deleted = true`，不做物理删除。
- 「未删除」是所有统计与列表的默认前提，但必须**逐条查询显式声明**：`get_energy_statistics` 同时过滤记录与车间的 `is_deleted`（`repository.py:255-256`），`get_overview_summary`/`get_overview_trend` 只过滤记录未过滤车间，`get_monthly_summary`/`get_monthly_energy_total` 只过滤记录。
- 车间实体合并（第 10 章）是软删除 + 改挂 `workshop_id`，可逆；软删除时必须让出 `code`（`<原code>#merged#<uuid前8>`），否则日后重建同名车间撞 `uq_energy_workshop_code`。

## 4. 数据来源与链路

模块侧目录 `backend/app/modules/energy/`：`api.py` `schemas.py` `service.py` `repository.py` `models.py` `scheduler.py` `job_store.py` `public_api.py` + 4 个导入器 + `adapters/{base,platform_a,platform_b,platform_c}.py`。

### 4.1 五条链路

| # | 链路 | 实现 | 入口 | 落库 | 关键口径 |
|---|---|---|---|---|---|
| 1 | **月度交叉表导入** | `bitable_cross_import.py` | `POST /api/v1/energy/sync/bitable/cross-import`（后台任务） | `energy_monthly_records` | 表名**全等**匹配 `YYYY-MM`；车间名三步解析（归一化 → 别名 → 查/建）；只有 `value > 0` 落库；按 `(workshop_id, energy_type, record_date)` 存在即更新 |
| 2 | **日表导入 + 预警** | `bitable_daily_import.py` | `POST /api/v1/energy/sync/bitable/daily-import`，页面文案「导入每日数据并检查预警」 | `energy_daily_data` → `energy_alert_records` | 读取源表「总数」「警戒线」；`is_alert = total_value > alert_threshold`；随后 `check_alerts` 按 1.1/1.2 倍分档生成记录 |
| 3 | **车间主数据同步** | `bitable_sync.py` | `POST /api/v1/energy/sync/bitable/workshops` | `energy_workshops` | 源表列 `编码/名称/分类/排序/启用`；name 与 code 分别建两个字典、都带 `is_deleted == false` |
| 4 | **飞书表格导入（旧链路）** | `feishu_import.py` | `POST /api/v1/energy/monthly/import/feishu` | `energy_monthly_records`（`source='feishu'`） | 与链路 1 并存；前端按钮曾打错路径（`D-17`，已修） |
| 5 | **三方平台采集** | `adapters/*` + `scheduler.py` | 后台 worker `energy.collection`；手动 `POST /api/v1/energy/collect/trigger` | `energy_data` + `energy_collect_logs` | `TICK_INTERVAL=300` 秒轮询、按设备 `collection_interval` 判定到期、**支持补采**（`MAX_BACKFILL_HOURS=168`）、平台 A 真·指数退避重试 |

### 4.2 链路 1 的解析链（唯一必须三步同时成立的口径）

```
源表原始叫法
   ↓ _normalize_workshop_name      strip()；纯数字补「车间」（101 → 101车间）；不再按「、」截断
   ↓ WORKSHOP_ALIASES / 「车间映射」表   精确匹配（比对前 strip），sheet 优先于代码常量
   ↓ _get_or_create_workshop       按 name 查 → 按 code 查（都带 is_deleted=false）→ 新建
```

别名清单、四侧叫法对照、汇总表跳过规则、section 切换正则等**字段级契约全部在** [energy-bitable-field-mapping.md](./energy-bitable-field-mapping.md)，本文不重复。**只改库内数据不改导入器，下一次导入会把错误实体重新建出来** —— 因此任何车间合并必须「导入器别名 + 迁移脚本」两处同改（第 10 章）。

### 4.3 链路 5 的时序与容错

- 注册方式：`app/shared/lifecycle.py` 的 `register_background_worker()`，三个常驻循环 `energy.collection` / `energy.bitable_monthly_sync` / `energy.bitable_daily_sync`（`__init__.py:43/59/75`）。**不使用 `TaskDefinition`**。
- 到期判定：每 `TICK_INTERVAL=300` 秒检查一次，取该批设备里最早的 `last_collected_at`，用 `_get_target_hours_since`（`scheduler.py:35`）算出需要补的整点列表，上限 `MAX_BACKFILL_HOURS=168` 小时。
- 外部调用重试：`adapters/platform_a.py:126-127` `_MAX_RETRIES=3` + `_RETRY_BACKOFF=(1,2,4)`，只对超时/连接错误/`RemoteProtocolError`/5xx 重试，其它异常直接抛；分页有 `MAX_PAGES` 截断。⚠️ 飞书月度同步用的是**固定 `sleep(60)` × 3 次**（`scheduler.py:259-296`），与 AGENTS.md 的指数退避要求不一致；每日同步**无重试**，异常只 `logger.exception`。列为 `D-18`。
- 失败可见性：采集失败写进 `energy_collect_logs.status='failed'/'partial'` 与 `error_message`；导入器的行级异常聚合成 `errors[:10]` 只回给调用方，**不进任何日志表**（`D-20`）。
- 异步任务状态：链路 1/2/3 与 `/sync/bitable`、`/sync/bitable/monthly` 都是 `job_store.py` 的**进程内 dict**（`sync_job_store` 单例）+ `app/core/tasks.py` 的 `spawn_task`（就是 `asyncio.create_task` + 异常记日志）。状态只有 `running/done/failed`，无进度百分比、无 TTL 清理、**重启即丢、多副本不可见**。列为 `D-11`。

## 5. 功能规格（按页面）

导航入口在 `frontend/src/lib/menu-config.ts:61-72`，只登记了 6 项：能源总览、月度记录、数据源配置、预警管理、采集日志、AI 分析。`/energy/workshops` 与 `/energy/settings` 两个 `page.tsx` 存在但**菜单不可达**（`D-21`）。

每页固定 8 小节：目的 / 路由与入口 / 依赖接口 / 取数与缓存 key / 交互与口径 / 边界与空态 / 验收用例 / 已知缺陷。

### 5.1 能源总览 `/energy`

| 小节 | 内容 |
|---|---|
| 目的 | 让能源管理员一眼看到所选时间窗内全厂四类能源的总量、构成与走势 |
| 路由与入口 | `/energy`；菜单「能源总览」；页面标题「能源总览」（`components/energy/EnergyOverview.tsx:97`） |
| 依赖接口 | 只读 `GET /api/v1/energy/overview`，经 `lib/api/client/energy.ts:40` `fetchEnergyOverviewClient`。无写操作 |
| 取数与缓存 key | React Query `useQuery`，key = `['energy-overview', overviewTimeRange, selectedEnergyType, today]`（`EnergyOverview.tsx:49`）。`today` 在挂载时固化（`:25-46`），否则 key 每次渲染都变会无限重取。时间范围状态在 `stores/energy.ts`（Zustand） |
| 交互与口径 | Segmented 预设「今日 / 近7天 / 近30天」，默认 `today`（`stores/energy.ts:107`）；能源类型 Select「全部/电力/水/蒸汽/天然气」；刷新按钮 `refetch`。区域分布饼图 `DistributionChart` 按 `energy_type` 用卡片内 Segmented 分开画，**只在同单位内算占比**（第 6 章 6.2）。⚠️ 默认「今日」，而月度数据是 3~4 天一列的填报节奏，**默认进页面全 0 与空态是正常现象，不是 bug**，要看数点「近30天」 |
| 边界与空态 | 该类型窗口内无非零记录 → 「该能源类型在当前时间范围内暂无数据」（`:172`）；无可切类型时不渲染分段控件；请求失败 → `message.error('获取能源数据失败')`（`:61`）；加载态透传骨架 |
| 验收用例 | ① 点「近30天」→ 四类能源卡片出现非零合计；② 选「水」→ StatsCards 只水卡高亮、饼图自动切到水的分段；③ 电的分段合计应与 `overview` 响应里 electricity 的 `total_value` 逐位一致；④ 汽的分段切片数少于 14 时，差额可用窗口内零值车间（如 `103车间`、`环保中心`）解释；⑤ 停后端 → 页顶出现错误提示且不清空已有图表 |
| 已知缺陷 | `page.tsx` 声明 `force-dynamic` 但页面内容全部由 Client 组件取数，无 server 取数（`:1-7`）；饼图切片可达 58 片，可读性差（`D-22`） |

### 5.2 月度记录 `/energy/monthly`

| 小节 | 内容 |
|---|---|
| 目的 | 明细级核对与人工修正：查看/新增/删除某车间某能源某日的能耗值，并从飞书来源批量导入 |
| 路由与入口 | `/energy/monthly`；菜单「月度记录」；副标题「支持从飞书表格批量导入」（`app/(dashboard)/energy/monthly/page.tsx:19,29`） |
| 依赖接口 | 读 `GET /monthly`、`GET /monthly/summary`、`GET /workshops`（均 `lib/api/client/`）；删除走 Server Action `deleteMonthlyRecordAction`；导入走 `crossImportFromBitableAction`（`POST /sync/bitable/cross-import`）与 `importFromFeishuAction`（`POST /monthly/import/feishu`，`D-17` 已修），导入后轮询 `GET /jobs/{job_id}` |
| 取数与缓存 key | 列表 `['energy-monthly-records', {workshopFilter, energyTypeFilter, startDate, endDate, page, pageSize}]`（`MonthlyRecordTable.tsx:105`）；汇总 `['energy-monthly-summary', {...}]`（`:121`）；车间下拉 `['energy-workshops']`（`:132`）。日期在进 key 前格式化成字符串（`:96-98`），否则 dayjs 对象每次渲染重建导致缓存永不命中。写操作后按前缀显式失效两个 key（`:148-151`） |
| 交互与口径 | 筛选：车间（单选）、能源类型、RangePicker；分页默认 20 条可改（`:89,322`）；两个导入按钮（`:272-277`）；表格列展示 `value`+`unit`，跨天记录显示 `record_date` ~ `date_range_end`。筛选按 `workshop_id` 精确匹配 —— 这就是历史上「选质量控制部看不到水量」的根因，现由车间实体统一解决 |
| 边界与空态 | 空结果渲染空表；删除有 `modal.confirm` 二次确认；导入任务失败在 Modal 内显示 `errors[:10]`；`value` 改成 0 **不会**删除既有记录，也不会新增（第 6 章 6.6） |
| 验收用例 | ① 选车间「质量控制部」→ 同屏应同时出现电与水的记录（历史上水记在 `QC` 上）；② 筛选后卡片汇总与列表逐行求和一致；③ 「交叉表导入」按 `2026-09` 走完「预览 → 确认」→ 任务 `done`，重查该月出现新记录且车间总数仍为 30；④ 删除一条记录 → 列表与汇总同步减少；⑤ 按年导入统计数字当前恒为 0（`D-04`），验收只看库内行数不看它 |
| 已知缺陷 | `D-04` 年度合计恒 0；`page.tsx` 只是 `'use client'` 套壳，未走 Server Component 取数。（`D-17` 飞书导入按钮 404 已修） |

### 5.3 车间管理 `/energy/workshops`（菜单不可达）

| 小节 | 内容 |
|---|---|
| 目的 | 维护车间主数据：编码、名称、分类、排序、启用、合计行标记 |
| 路由与入口 | `/energy/workshops`，标题「车间管理」（`workshops/page.tsx:8`）；**菜单无入口**，只能直连 URL |
| 依赖接口 | 读 `GET /workshops`（分页版 `fetchWorkshopsPageClient`）；写 Server Action `createWorkshop` / `updateWorkshop` / `deleteWorkshop` + `getWorkshopById` |
| 取数与缓存 key | 列表 `['energy-workshops', {categoryFilter, page, pageSize}]`（`WorkshopTable.tsx:94`）；抽屉单条 `['workshop', workshopId]`（`WorkshopDrawer.tsx:33`）。写后 `invalidateQueries({queryKey:['energy-workshops']})`（`:107`） |
| 交互与口径 | 分类筛选四值（workshop/position/support/utility）；分页默认 20；抽屉字段：`code`（必填，≤50）、`name`（必填，≤100）、`category`、`excluded_energy_types`（多选，可空：电力/自来水/蒸汽/天然气）、`sort_order`（min 0）、`is_active`（`WorkshopDrawer.tsx:95-145`）。删除为软删除。`excluded_energy_types` 非空时列表名称列显示「合计行·电」一类徽标（`WorkshopTable.tsx`），语义见 6.1 与 6.8.1 |
| 边界与空态 | 列表请求失败 → `message.error('加载车间列表失败')`（`:99`）；删除前 `modal.confirm`；`category` 目前实际全是 `workshop`（第 6 章 6.7）；`excluded_energy_types` 为空数组 = 全部计入，历史车间由迁移 `0069` 初始化 |
| 验收用例 | ① 新建车间 → 月度记录页的车间下拉立刻出现该项；② 把某车间 `is_active` 关掉 → 它不再出现在筛选栏，但历史记录仍在；③ 用已软删除车间的 `code` 新建 → 当前会撞 `uq_energy_workshop_code`（`D-08`），预期是给出可读错误而不是 500；④ 给某车间勾选 `electricity` 后保存 → 能源总览卡片/饼图/趋势的全厂电量立刻减少该车间电量，但月度记录页选到该车间仍能看到它自己的值 |
| 已知缺陷 | 菜单不可达 `D-21`；`WorkshopDrawer` 用 `useEffect` + `setFieldsValue` 取数填表，违反 AGENTS.md（`D-23`）；车间缓存 key 三处不同源（`D-13`） |

### 5.4 数据源配置 `/energy/devices`

| 小节 | 内容 |
|---|---|
| 目的 | 登记三方平台的采集点，决定自动采集与手动采集抓什么、多久抓一次 |
| 路由与入口 | `/energy/devices`，标题「数据源配置」（`devices/page.tsx:46`）；菜单「数据源配置」 |
| 依赖接口 | 读 Server Action `getEnergyDevices`（`GET /devices`）；写 `createEnergyDevice` / `updateEnergyDevice` / `deleteEnergyDevice`；平台列表 `GET /platforms`（`lib/api/client/energy.ts:48`） |
| 取数与缓存 key | `['energy-devices', deviceFilters]`（`devices/page.tsx:16`）；`deviceFilters` 含 `keyword/energy_type/workshop/is_enabled/page/page_size`（`stores/energy.ts:55-62`），默认 `page_size=10`；状态在 Zustand `stores/energy.ts` |
| 交互与口径 | 筛选：名称搜索、能源类型（**缺天然气**，`D-16`）、启用状态；新增/编辑抽屉字段：平台、接入编码（支持 `+ -` 公式表达多个测点）、设备名称、能源类型、车间、单位、采集间隔（min 1 / max 1440 分钟）、监控级别（normal/important/urgent）、启用开关（`DeviceDrawer.tsx:272-468`）；`workshop` 存的是**车间名字符串**不是外键 |
| 边界与空态 | 平台列表接口失败时回落 3 条内置假平台（`:99-104`）；无匹配数据显示空表；写成功后 `revalidatePath('/energy/devices')` |
| 验收用例 | ① 新建一条 `collection_interval=60` 的启用配置 → 下一轮 tick 后 `energy_collect_logs` 出现该平台的批次且 `device_count` 含它；② 关掉 `is_enabled` → 采集批次里不再计入；③ 采集间隔填 0 或 1500 → 表单拒绝（CheckConstraint `collection_interval > 0` + 前端 max 1440） |
| 已知缺陷 | `DeviceDrawer.tsx:119-128` `useEffect` 取数（`D-23`）；`DevicesPageClient.tsx` 是无人引用的孤儿（`D-24`）；能源类型下拉缺 natural_gas |

### 5.5 预警管理 `/energy/alerts`

| 小节 | 内容 |
|---|---|
| 目的 | 处理日用量超标事件（记录 Tab），并维护预警规则表单（规则 Tab，当前仅留存） |
| 路由与入口 | `/energy/alerts`，标题「预警管理」，两个 Tab「预警记录 / 预警规则」（`alerts/page.tsx:238,306`） |
| 依赖接口 | 读 `GET /alerts/records`、`GET /alerts/rules`（client 分页版）；写 `processAlertRecord`（`PUT /alerts/records/{id}/process`）、`deleteAlertRule`、`createAlertRule`（Server Action）；导入按钮 `syncBitableDailyDataAction`（`POST /sync/bitable/daily-import`）+ 轮询 `GET /jobs/{job_id}` |
| 取数与缓存 key | 规则 `['alert-rules', {rulesPage, rulesPageSize}]`（`:100`）；记录 `['alert-records', {recordsPage, recordsPageSize, filterDate, filterEnergyType}]`（`:120`），`filterDate` 转成 `startOf/endOf day` 的 ISO 进 params（`:124-126`）；分页默认 10 |
| 交互与口径 | 记录 Tab：导入数据、DatePicker、能源类型筛选、刷新；处理弹窗字段 `status`（默认 processed，必填）+ `process_note`。规则 Tab 抽屉字段：规则名、能源类型、监控指标（instant/daily_total/monthly_total）、阈值类型（greater_than/less_than/equal）、阈值（min 0 必填）、单位（必填）、级别（info/warning/critical/emergency）、通知方式多选、通知用户、通知频率、生效时段（`AlertConfigDrawer.tsx:195-244`）。⚠️ **规则不参与判定**：判定只认日表警戒线（第 6 章 6.5） |
| 边界与空态 | 无记录时提示「暂无预警记录…请点击导入数据」（`AlertRecordTable.tsx:121-131`）；导入成功消息含新增/更新/预警数（`:214`） |
| 验收用例 | ① 点「导入数据」→ 当天 `total_value > 警戒线` 的行生成记录且等级按 1.1/1.2 倍分档；② 把某条 pending 记录处理为已处理 → 状态、处理人、处理时间、备注都落库；③ 同一天的同一 `(date, energy_type, category)` 重复导入 → 不重复生成预警（靠 `alert_record_id IS NULL` 守卫）；④ 新建规则 → 列表出现，但**不会产生任何预警或通知** |
| 已知缺陷 | `D-01` 规则未接线；`D-14` 通知字段无消费方；`D-15` 记录无车间维度、`unit=""`；`actions/energy.ts:115,127,138` 的 `revalidatePath('/energy/alert-rules')`、`'/energy/alert-records'` 指向**不存在的路由**（真实为 `/energy/alerts`），缓存失效落空（`D-25`）；`AlertConfigDrawer.tsx:82-112` `useEffect`+`setTimeout` 取数（`D-23`）；能源类型选项缺 natural_gas（`alerts/page.tsx:15-19`）；`AlertsPageClient.tsx` 孤儿（`D-24`） |

### 5.6 采集日志 `/energy/collect-logs`

| 小节 | 内容 |
|---|---|
| 目的 | 排查「今天数据为什么没进来」：看每轮采集的成功率与失败设备明细 |
| 路由与入口 | `/energy/collect-logs`，标题「采集日志」（`collect-logs/page.tsx:93`） |
| 依赖接口 | 读 Server Action `getCollectLogs`（`GET /collect/logs`）；写 `triggerCollect`（`POST /collect/trigger`）；详情 `GET /collect/logs/{log_id}/detail` |
| 取数与缓存 key | 列表 `['collect-logs', logFilters]`（`:27`；`logFilters` 含 `platform_code/status/page/page_size`，默认 10，`stores/energy.ts:74-79`）；详情 `['collect-log-detail', logId]`（`CollectLogDetailDrawer.tsx:166`）；Zustand |
| 交互与口径 | 筛选：采集状态（成功/部分成功/失败）；「手动采集」触发全部平台，行内「重试」按该行 `platform_code` 触发（`:57-64,162`）；详情抽屉展示应采数、成功数与设备级明细表 |
| 边界与空态 | 详情无关联数据 → Empty「暂无数据 / 未找到关联的设备采集数据」（Drawer `:401-409`）；触发采集失败只 `console.error`，**没有任何用户提示**（`:50-52`） |
| 验收用例 | ① 点「手动采集」→ 列表新增一条本轮日志；② 打开该日志详情 → 设备行与 `energy_data` 里 `collected_at` 落在该日志 ±30 秒的记录一致；③ 状态筛选「失败」→ 只出现 `status='failed'` 的批次且 `error_message` 非空 |
| 已知缺陷 | `D-12`：日志与数据无外键，靠 `repository.py:411-452` 的 ±30 秒时间窗反推，补采（多小时批量 upsert）会漏或串；触发失败静默；`CollectLogsPageClient.tsx` 孤儿。（`D-26` 详情抽屉路径已修：原请求 `/energy/collect-logs/${logId}`，后端真实是 `/api/v1/energy/collect/logs/{log_id}/detail`） |

### 5.7 AI 分析 `/energy/ai-analysis`

| 小节 | 内容 |
|---|---|
| 目的 | 车间月度电单耗核算 + 目标偏差 + LLM 分析与建议 |
| 路由与入口 | `/energy/ai-analysis`，标题「AI 能耗智能分析」（`ai-analysis/page.tsx:159`） |
| 依赖接口 | 读 `GET /workshops`、`GET /targets/{workshop_id}/{target_month}`、`GET /production/output`（**后端不存在**；真实产量台账在 production 模块的 `GET /api/v1/production/product-output`，下期跨模块对接需走该模块 `public_api.py`）；写 `POST /ai-analysis-v2`、`POST /targets`、`PUT /targets/{target_id}`。**这三个写接口全部从浏览器直接 fetch**（`lib/api/client/energy.ts:106-177`），违反 AGENTS.md「写操作必须走 Server Actions」 |
| 取数与缓存 key | 车间 `['workshops']`（`:42`）；目标 `['target', workshopId, analysisMonth]`（`:53`，两个参数都非空才 `enabled`）；设定目标成功后失效同 key 并复算（`:128-135`）。其余是 `useState` 本地态 |
| 交互与口径 | 车间 Select + MonthPicker（`YYYY-MM`）；**产品产量列表手填**：表格内 `product_name` 文本 + `quantity` 数字（min 0）逐行编辑，单位固定 `kg` 不可改（`:68,197,206`），可增删行；「从生产模块同步」按钮调 `fetchProductionOutput`（路径不存在，`D-02`）。校验：月份匹配 `/^\d{4}-\d{2}$/`（`:102`）、产品明细非空（`:107`），车间+月份+产量三项齐才允许点分析（`:228`）。目标弹窗 `TargetModal`：目标月份继承所选月份，目标单耗 `InputNumber` min 0.0001 / max 9999.9999 / precision 4 / step 0.1，后缀 `kWh/kg`（`TargetModal.tsx:108-118`），`handleOk` 校验 workshopId、数值、>0（`:46`）；已有目标走 update，否则 create（`:55-67`）。⚠️ 后端 schema 的上限是 `le=100`（`schemas.py:322`），前端允许到 9999.9999 → 超限提交会被后端 422 拒（`D-27`） |
| 边界与空态 | 未设目标 → 显示「未设定」+「➕设定目标」（`:253-261`），`deviation_status='unknown'` → 文案「未知（未设定目标）」（`:306`）；该车间当月无能耗记录 → 后端抛 `NotFoundException('能耗数据', ...)`（`service.py:816-817`），页面显示错误；LLM 输出畸形/不可用 → 降级为固定文案，不整链失败 |
| 验收用例 | ① 选车间+月份且该月有电耗 → 自动查出目标并显示单耗与偏差；② 填两条产品产量点分析 → 返回 `actual_unit_consumption`（4 位小数）、`target_unit_consumption`（无目标显示 `—`）、`deviation_rate`（带正负与颜色）、`ai_suggestion.summary/detailed_analysis/recommendations[]/confidence_level`；③ 设定目标成功后卡片立即复算且偏差状态改变；④ 断言折算系数缺失的产品按 `factor=1.0` 参与分母（`service.py:840`）；⑤ 把 `energy_product_conversions` 里某产品系数配成 2 → 折算产量翻倍、单耗减半 |
| 已知缺陷 | 第 6 章 6.4 的三项口径偏差：分子含非电能源（`D-28`）、偏差取绝对值（`D-29`）、日均分摊窗口下界失效（`D-30`）；写接口绕过 Server Action（`D-37`）；`AIAnalysisResult`/`AISuggestion`/`UnitConsumptionTarget`/`ProductionOutputItem` 全是手写 API 类型（`lib/api/client/energy.ts:97-194`，`D-36`）；车间缓存 key 与列表页不同源（`D-13`）；`TargetModal.tsx:38-43` 在 render 期 setState |

### 5.8 设置 `/energy/settings`（菜单不可达）

| 小节 | 内容 |
|---|---|
| 目的 | 开关自动采集等运行时配置 |
| 路由与入口 | `/energy/settings`，标题「能源管理配置」，描述「配置能源模块的自动采集功能开关」（`settings/page.tsx:5-9`）；**菜单无入口**。实现为纯复用 `ModuleSettingsClient moduleCode="energy"` |
| 依赖接口 | 平台层 `getModuleSettings(moduleCode)` / `updateModuleSetting`（`components/settings/ModuleSettingsClient.tsx:20-23`），非能源模块自有端点 |
| 取数与缓存 key | `['module-settings', moduleCode]`（`:48`），保存后失效同 key（`:76`） |
| 交互与口径 | Table 列出配置项 `key`/类型/当前值；编辑弹窗按 `value_type` 渲染控件：bool → Switch、int → InputNumber、json → TextArea、其余 → Input（`:102-129`） |
| 边界与空态 | 值缺失显示「未设置」（`:98`）；Table loading 态；模块内不判权限 |
| 验收用例 | ① 把 `ENERGY_AUTO_COLLECT_ENABLED` 打开 → 调度循环在下一次 tick 读到新值并开始采集（`scheduler.py:152` 每 tick 重读，无需重启）；② 关闭 → 后续 tick 停止采集，`energy_collect_logs` 不再增长；③ 改成非布尔字面量 → 后端配置校验拒绝 |
| 已知缺陷 | 菜单不可达（`D-21`）；两个 Bitable 自动同步开关**没有进种子表**，只能靠环境变量（`D-31`） |

## 6. 计算口径与规则

本章口径**不含实现缺陷描述**；缺陷一律进第 12 章登记表并在本节交叉引用。口径与代码不一致时，以本章为准。

### 6.1 汇总口径

- 统计范围 = 时间窗内**未删除**的 `energy_monthly_records`，且其车间实体未删除（各查询对此过滤不一致，见 `D-39`）。
- **合计行剔除**：车间实体 `excluded_energy_types` 里列出的能源类型**不计入全厂口径**（`repository.py:_not_rollup_record`）。粒度是 `(车间实体, 能源类型)`，不是整个车间 — `RTO` 只剔电，它的 `natural_gas` 是全厂唯一气源（实测：`energy_monthly_records` 里 `natural_gas` 只有 `RTO` 一个实体、573 行、全为 `Nm³`），整车间剔除会把气系列清零。
- 受该口径约束的只有全厂聚合：`GET /overview`（汇总卡片 + 趋势 + 区域分布）、`GET /monthly/summary`（**不带 `workshop_id` 时**）、`GET /data/statistics`。月度记录明细列表、车间筛选、单车间合计（`get_monthly_energy_total`，AI 单耗分析的分子）**保留原值**，否则车间维度看不出自己报了什么。
- 归期规则：按 `record_date` 单点归期。`date_range_end` 非空的多日汇总记录**整体算进 `record_date` 那一天**（第 3 章 3.4）。因此按日曲线会出现「列首日期尖峰」，这是既定口径而非错误。
- 单位不换算：`value` 与 `unit` 成对呈现，任何汇总值必须与单位同屏显示。`kWh`、`m³`、`t`、`Nm³` 之间**禁止相加**（`D-28` 是当前唯一的违反点，属缺陷）。
- 零值不参与汇总（6.6）。

### 6.2 分布口径（区域分布饼图）

- 分组键 = `(车间实体名, unit, energy_type)`，占比**只在同一 `energy_type` 内部计算**，分母为该能源类型窗口内合计。跨单位合并占比在物理上无意义，禁止。
- 切片集合已应用 6.1 的合计行剔除，因此电的饼图**不含 `动力运行` 与 `RTO`**（两者的电分别等于 6 台机组之和、已含在 `环保中心` 内）；`RTO` 仍出现在气的饼图里。气饼图只有 1 片属预期，不是数据缺失。
- 只画窗口内**存在非零记录**的车间实体。因此切片数 ≤ 该能源规范实体数（电 27 / 水 20 / 汽 14 / 气 1），差额必须能用「窗口内零值」或「合计行剔除」解释。例：近 30 天汽只有 12 片，因为 `103车间`、`环保中心` 该窗口用汽为 0。
- 前端在卡片内用 Segmented 切电/水/汽/气，选中项在当前可用类型集合变化时回落到第一个可用类型；无可切类型时不显示分段控件。

### 6.3 趋势口径

- `get_overview_trend`（`repository.py:340-376`）按 `(record_date, energy_type)` 分组求和，可选按 `energy_type` 过滤。
- 只返回**有记录的日期**，不补零、不外推缺口。因此趋势图上相邻两点之间的间隔可能代表 2~4 天的合并填报列。
- 采集链路（`energy_data`）与趋势口径**不共用数据源**：总览/趋势/分布全部只读月度记录表，`energy_data` 目前只服务采集日志详情核对。

### 6.4 单耗与偏差（G2）

**口径（已确认）**

- 分子 = 该车间该月的**电耗合计**，单位 `kWh`。水/汽/气**不进**单耗分子。
- 分母 = 折算标准品产量 = Σ(产品产量 × 折算系数)，单位 `kg`。折算系数按产品名从 `energy_product_conversions` 取，**取不到按 `1.0`**（即该产品即标准品）。
- 实际单耗 = 分子 / 分母，`round(…, 4)`，单位 `kWh/kg`。分母 ≤ 0 视为无效输入并直接报错，不返回 0。
- 目标单耗按 `(车间, 月份)` 唯一，取值域 0.0001 ~ 100（后端 `schemas.py:322` 的 `gt=0, le=100`）。前端 `TargetModal` 的 max 9999.9999 与之冲突，以后端为准（`D-27`）。
- 偏差率 = (实际单耗 − 目标单耗) / 目标单耗 × 100%，`round(…, 2)`。
- **偏差分档只算超标（正向）**：
  | 偏差率 | 状态 | 业务含义 |
  |---|---|---|
  | 无目标 | `unknown` | 未设定目标，不做判定 |
  | ≤ +5% | `normal` | 达标 |
  | +5% < x ≤ +15% | `warning` | 超标，需关注 |
  | > +15% | `critical` | 严重超标，需整改 |
  | < 0（低于目标） | `normal` | 节能，**不计预警**。异常偏低（漏报产量等）由人工在分析里判读，不用分档表达 |

**与现状实现的差异**（不改口径，代码待修）：分子未按能源类型过滤（`D-28`，`repository.py:864-885`）；分档对绝对值判定，节省 20% 也判 critical（`D-29`，`service.py:782-793`）；日均分摊窗口的下界条件对 `date_range_end IS NULL` 的记录不生效（`D-30`，`service.py:585`）。

### 6.5 预警判定（G3）

**口径（已确认：以日表「警戒线」为唯一判定基准）**

- 触发条件：`total_value > alert_threshold`，落库时同步置 `energy_daily_data.is_alert`。
- 等级分档（`bitable_daily_import.py:227-232`）：
  | 倍数 | 等级 |
  |---|---|
  | > 警戒线 × 1.2 | `critical` |
  | > 警戒线 × 1.1 | `warning` |
  | 仅 > 警戒线 | `info` |
- 幂等守卫：只为 `is_alert = true` **且 `alert_record_id IS NULL`** 的日数据生成记录，生成后回填 `alert_record_id`，因此同日重复导入不产生重复预警。
- `energy_alert_rules` 的 `monitor_metric` / `threshold_type` / `threshold_value` / 生效时段 / 通知配置**全部不参与判定**（`D-01`）；本期不做通知送达（`D-14`）。
- 阈值来源：数值由飞书日表逐行给定，**不在本模块配置**。谁维护、按什么规则调线，属源表侧流程，本文不定义。

### 6.6 零值与未填报

**口径（已确认）**：`value > 0` 才落库；`0` 与空单元格都视为**未填报**，不落库。

- 后果 1：库内无法区分「没用」和「没填」，需要区分时回源表看。
- 后果 2：把源表某条从 5 改成 0 再导入，**不会删除**既有记录，`value` 也不会被改写（该行走 `value > 0` 守卫）。修正数据要么填正确值，要么走第 10 章脚本或月度页删除。
- 后果 3：饼图切片数少于实体数是正常现象（6.2）。

### 6.7 车间分类 `category`

**口径（已确认为目标口径）**：`WorkshopCategory` 四值 —— `workshop` 生产车间 / `position` 岗位 / `support` 辅助部门 / `utility` 动力设施；归类标准见映射文档「建议的 category 归类」表（401~405 岗位 → position；仓库/办公楼/饭堂/质量控制部/环保中心 → support；冷水机组、盐水机组、空压氮气系统、纯化用水、锅炉用水、RTO → utility；其余 → workshop）。

- 现状：导入器从不传分类，落库默认 `workshop`，四值形同虚设（`D-33`）。
- 因此**当前任何按分类的筛选都只是按现状过滤**，不代表业务归类；分类维度的统计不做承诺。
- 落地路径：`车间映射` sheet 的 `分类` 列（映射文档列定义）→ `bitable_sync.py` 同步 → 一次性回填脚本。

### 6.8 车间实体与别名

- 一个部门在库里**只有一个**未删除实体；别名只在解析链中间态存在，不落库（第 4 章 4.2）。
- `动力车间` 与 `动力运行` 是两个独立组织，**已裁定不合并**。
- 新增同义叫法必须同时改两处（`WORKSHOP_ALIASES` 与迁移脚本 `WORKSHOP_UNIFICATION`，见第 10 章），否则「改数据 → 下次导入打回原形」。

#### 6.8.1 叫法与包含关系（源表写法 → 实体 → 汇总处理）

| 源表叫法 | 规范实体 | 与谁重复 | 全厂汇总处理 |
|---|---|---|---|
| `动力运行` | `动力运行` | = `201盐水机组`+`103冷水机组`+`4号楼冷水机组`+`500T冷水机组`+`500T盐水机组`+`空压氮气系统` 的**用电之和** | 只剔 `electricity`（`ROLLUP_WORKSHOPS`） |
| `RTO用电`、`RTO(天然气）` | `RTO`（两行归一实体，`ea51d979`；该 commit 只合并了实体，**没解决重复计数**，见 §13 `b34d7f25`） | 电已含在 `环保中心(含RTO)` 里；气是全厂**唯一**气源 | 只剔 `electricity`，`natural_gas` 保留 |
| `环保中心(含RTO)`、`废水站` | `环保中心` | 容器实体，包含 `RTO` 的电 | 保留；对 `RTO` 的电做 ⊇ 校验 |

- 实测重复量（`energy_monthly_records`，`electricity`，未删除）：2026-07 原始 2,392,722 → 剔除后 1,590,438 kWh（重复 802,284，33.53%）；2026-08 3,339,338 → 2,165,388（重复 1,173,950，35.16%）；2026-09 2,628,791 → 1,741,834（重复 886,957，33.74%）。
- 逐月核对 `动力运行` 与 6 台机组之和（库内全部 34 个月，2024-01 ~ 2026-10）：**32 个月差值为 0，2 个月有小差**（2025-09 少 2,000 kWh = 0.29%；2025-11 少 800 kWh = 0.14%，属源表手工汇总的尾差）。**没有任何月份超过 1% 容差**，因此导入期一致性告警（`_check_rollup_consistency`）在正常情况下静默；一旦源表增删机组而常量未同步，告警会指出偏差而不是静默错算。
- 告警只记 `logger.warning` 并随交叉表导入任务的 job 结果返回（`rollup_warnings`），**不自动改数**：多维表格行名会变，静默修数会掩盖源表问题。

## 7. 接口契约索引

**字段级契约不在本文重复**：请求/响应字段以 `backend/openapi.json` 为准，前端类型由 `pnpm generate:api` 生成到 `frontend/src/types/generated/schema`。下表只登记 路径 + 用途 + 调用页面。

共 **42 个 operation**：`api.py` 内 41 个处理函数 + `GET /api/v1/energy/`（模块元信息，由 `app/shared/module_api.py:10` 的工厂注入，因此 `api.py` 里搜不到它）。

### 7.1 设备配置与采集

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/platforms` | GET | 已登记平台列表 | 数据源配置 |
| `/api/v1/energy/devices` | GET / POST | 采集点列表 / 新增 | 数据源配置 |
| `/api/v1/energy/devices/{config_id}` | GET / PUT / DELETE | 单条读写与软删除 | 数据源配置 |
| `/api/v1/energy/collect/trigger` | POST | 手动触发采集（同步端点） | 采集日志 |
| `/api/v1/energy/collect/logs` | GET | 采集批次日志列表 | 采集日志 |
| `/api/v1/energy/collect/logs/{log_id}/detail` | GET | 单批日志的设备级明细 | 采集日志详情抽屉（`D-26` 已修，路径此前写错） |
| `/api/v1/energy/data` | GET | 查 `energy_data` 原始采集值 | 无页面（运维核对用） |

### 7.2 车间与月度记录

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/workshops` | GET / POST | 车间列表 / 新增 | 车间管理、月度记录与 AI 分析的下拉数据源 |
| `/api/v1/energy/workshops/{workshop_id}` | GET / PUT / DELETE | 单条读写与软删除 | 车间管理 |
| `/api/v1/energy/monthly` | GET / POST | 月度明细列表 / 新增 | 列表由月度记录页使用；`POST` 只有 `actions/energy.ts:186` 的包装，**无 UI 入口** |
| `/api/v1/energy/monthly/{record_id}` | GET / DELETE | 单条读 / 软删除 | 删除由月度记录页使用；`GET` 无 UI 入口。**后端没有 PUT** —— 修正数值只能删除重建或改源表重导入（6.6） |
| `/api/v1/energy/monthly/batch` | POST | 批量新增 | 无前端调用（预留） |
| `/api/v1/energy/monthly/summary` | GET | 按能源类型汇总 | 月度记录页卡片 |
| `/api/v1/energy/monthly/import/feishu` | POST | 飞书表格导入（链路 4） | 月度记录的「飞书导入」（`D-17` 已修，前端曾少 `/monthly` 段） |

### 7.3 多维表格同步与异步任务

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/sync/bitable` | POST | 同步全部（车间+月度） | 无前端调用（运维手动） |
| `/api/v1/energy/sync/bitable/workshops` | POST | 链路 3 车间主数据 | 无前端调用 |
| `/api/v1/energy/sync/bitable/monthly` | POST | 月度记录同步 | 无前端调用 |
| `/api/v1/energy/sync/bitable/cross-import` | POST | 链路 1 月度交叉表导入 | 月度记录「交叉表导入」 |
| `/api/v1/energy/sync/bitable/daily-import` | POST | 链路 2 日表导入并检查预警 | 预警管理「导入数据」 |
| `/api/v1/energy/jobs/{job_id}` | GET | 异步任务状态（进程内，`D-11`） | 上述两个导入弹窗轮询 |

### 7.4 预警

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/alerts/rules` | GET / POST | 规则列表 / 新增（仅留存，不接线） | 预警管理 · 预警规则 Tab |
| `/api/v1/energy/alerts/rules/{rule_id}` | GET / PUT / DELETE | 单条读写与删除 | 预警管理 · 预警规则 Tab |
| `/api/v1/energy/alerts/records` | GET | 预警记录列表 | 预警管理 · 预警记录 Tab |
| `/api/v1/energy/alerts/records/{record_id}/process` | PUT | 处理（状态/处理人/备注） | 预警管理 · 处理弹窗 |

### 7.5 总览与统计

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/overview` | GET | 汇总卡片 + 区域分布 + 趋势 | 能源总览 |
| `/api/v1/energy/data/statistics` | GET | 按车间/产线/设备分组统计 | 无前端调用（`group_by` 非 workshop 时实际也按车间，`D-35`） |

### 7.6 单耗目标与 AI 分析

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/targets` | POST | 创建月度目标单耗 | AI 分析 · 设定目标 |
| `/api/v1/energy/targets/{target_id}` | PUT | 修改目标 | AI 分析 · 设定目标 |
| `/api/v1/energy/targets/{workshop_id}/{target_month}` | GET | 查目标（无目标返回 null） | AI 分析 |
| `/api/v1/energy/ai-analysis-v2` | POST | 单耗核算 + 偏差 + LLM 建议 | AI 分析 · 开始分析 |

### 7.7 前端引用了但后端不存在的端点

| 前端调用位置 | 路径 | 状态 |
|---|---|---|
| `lib/api/client/energy.ts:194` | `GET /energy/production/output` | 不存在，`D-02`；真实来源为 `GET /api/v1/production/product-output`（production 模块） |
| `lib/api/server/energy.ts:263` | ~~`POST /energy/import/feishu`~~ | **已修**：改为 `/energy/monthly/import/feishu`，见 `D-17` |
| `lib/api/server/energy.ts:285` | `POST /energy/alerts/check` | 不存在，且只有 `actions/energy.ts:223` 的孤儿包装引用，`D-45` |
| `lib/api/server/energy.ts:292` | `GET /energy/alerts/dates` | 不存在，同上孤儿包装，`D-45` |
| `lib/api/client/energy.ts:44` | ~~`GET /energy/collect-logs/{logId}`~~ | **已修**：改为 `/energy/collect/logs/{logId}/detail`，见 `D-26` |

对账方法（可复跑）：把 `openapi.json` 的 `/energy` 路径参数段归一为通配，再扫 `lib/api/{client,server}/energy.ts` 里每个函数体的模板串与 `method:`，比对「路径不存在」与「路径存在但方法不符」。修完后该模块仅剩 `D-02` 与 `D-45` 两组不匹配。

## 8. 配置项

分两层，遵循 AGENTS.md 的配置分层规则：**凭证进部署环境变量**，**开关与运营参数进运行时 `core.module_settings`**。

### 8.1 部署层（`.env` + `app/core/config.py`）

| 字段 | 默认值 | 环境变量 | 消费方 |
|---|---|---|---|
| `ENERGY_AUTO_COLLECT_ENABLED` | `False` | `ENERGY_AUTO_COLLECT_ENABLED` | `config.py:168`；调度循环读运行时配置为准（见 8.2） |
| `ENERGY_BITABLE_AUTO_SYNC_ENABLED` | `False` | 同上命名 | `config.py:169`；月度自动同步开关 |
| `ENERGY_BITABLE_SYNC_HOUR` | `17` | 同上命名 | `config.py:170`；月度同步执行小时 |
| `feishu.energy.app_token` | `""` | `FEISHU__ENERGY__APP_TOKEN` | 月度交叉表/日表/车间同步所在 base 的凭证（值不写入任何文档） |
| `feishu.energy.workshop_table_id` | `""` | `FEISHU__ENERGY__WORKSHOP_TABLE_ID` | 车间主数据表 |
| `feishu.energy.monthly_table_id` | `""` | `FEISHU__ENERGY__MONTHLY_TABLE_ID` | 月度表 |
| `feishu.energy.alert_app_token` | `""` | `FEISHU__ENERGY__ALERT_APP_TOKEN` | 日表/预警来源 base |
| `feishu.energy.daily_sync_hour` | `17` | `FEISHU__ENERGY__DAILY_SYNC_HOUR` | 每日同步执行小时（`scheduler.py:321`） |

嵌套结构由 `FeishuSettings`（`config.py:110-117`）定义，分隔符 `env_nested_delimiter="__"`（`config.py:161`）。

### 8.2 运行时层（`core.module_settings`，设置页 `/energy/settings`）

| key | 类型 | 默认 | 语义 | 生效方式 |
|---|---|---|---|---|
| `energy / ENERGY_AUTO_COLLECT_ENABLED` | bool | `false` | 自动采集总开关 | `scheduler.py:144` 启动判断 + `:152` **每 tick 重读，改完无需重启** |

种子来源：`scripts/seed/seed_module_settings.py:63-69`。**`ENERGY_BITABLE_AUTO_SYNC_ENABLED` 与 `ENERGY_BITABLE_SYNC_HOUR` 没有进种子表**，只能在设置页外部靠环境变量控制（`D-31`）。

### 8.3 读取优先级与已知不一致

- 月度自动开关与执行小时：**环境变量优先，回退运行时配置**（`scheduler.py:230-233`、`241-243`）。这意味着在设置页改了但 env 里显式给了值时，页面值不生效 —— 排障时先看 env。
- 每日同步小时：**只读 `Settings`**（`scheduler.py:321`），设置页无法影响。
- 自动采集开关：**只读运行时配置**（`scheduler.py:144/152`），env 值不生效。
- 三处口径互不相同，列为 `D-40`。AGENTS.md 禁止在模块代码里用 `os.getenv()` 读运行时配置，`scheduler.py` 的 env 优先逻辑属违规点。

### 8.4 环境变量文件现状

| 文件 | 是否含 `FEISHU__ENERGY__*` |
|---|---|
| 仓库根 `.env` | 含两个非空 `APP_TOKEN`（本地开发用，**该文件从未提交进 Git**，由 `.gitignore:2` 覆盖），缺 `WORKSHOP_TABLE_ID` / `MONTHLY_TABLE_ID` |
| `.env.example` | 8 项齐全（`WORKSHOP_TABLE_ID`/`MONTHLY_TABLE_ID` 留空） |
| `.env.dev.example`、`.env.uat.example` | 8 项齐全 |
| `backend/.env.development`、`backend/.env.ci.example` | **无 ENERGY 项** |

新增/修改 `.env` 时必须同步 `.env.example`（AGENTS.md）。凭证只允许出现在部署 env，不得进数据库、文档、Git。

## 9. 排障手册（runbook）

约定：所有 SQL 用参数化占位符（`:month_start` 等），由应用层脚本或 psql 参数绑定执行，**禁止**把运行时值拼进语句。表都在 `energy` schema，月度值列名叫 `value`。

本地执行环境要点（会踩的坑）：后端跑在容器 `erp-backend`（工作目录 `/app`），宿主机没有 `python`/`uv`，一切 Python 命令走容器；`backend/app` 与 `backend/scripts` 是**只读 bind mount**（改宿主机文件容器内立即可见，但 `docker cp` 进去会被拒）；`backend/tests` **不是**挂载，跑单个测试文件要先 `docker cp` 进容器；改了 `app/` 代码后常驻进程需要 `docker restart erp-backend`。查库不要直接 `docker exec erp-postgres psql`（库名不是 `livzon`），写脚本用 `from app.core.database import async_session_factory`，`docker cp` 到 `/tmp/` 后 `docker exec -w /app -e PYTHONPATH=/app erp-backend uv run python /tmp/xxx.py`。

### R1 某月数据缺失（导入没报错，库里没有）

- 先定位：`bitable_cross_import.py` 的表名匹配 —— 单月按表名**全等** `YYYY-MM`，`2026-6`、`2026年6月` 会**静默不导入**（映射文档「表结构契约」）。
- 校验：`SELECT count(*) FROM energy.energy_monthly_records WHERE record_date >= :month_start AND record_date < :month_end AND is_deleted = false;` 再看采集/导入侧 `logger` 的 `tables_imported`。
- 修复：把 base 里的表名改成 `YYYY-MM` 全等格式后重跑该月；不要用按年导入来兜底（`D-04` 会让统计数字恒为 0，但数据仍会入库）。

### R2 车间筛选看不到某能源

- 先定位：该部门在电/水/汽/气四个 section 的**叫法不同**被建成了两个实体（`QC` vs `质量控制部`）。筛选按 `workshop_id` 精确过滤，记录互斥。
- 校验：`SELECT name, count(*) FROM energy.energy_workshops WHERE is_deleted = false GROUP BY name ORDER BY 2 DESC;` 未删除实体应为 **30**；`SELECT w.name, r.energy_type, count(*) FROM energy.energy_monthly_records r JOIN energy.energy_workshops w ON w.id = r.workshop_id WHERE r.is_deleted = false AND w.is_deleted = false GROUP BY 1,2;` 看该实体是否四侧齐。
- 修复：按第 10 章「两处同改」补别名 → 跑合并脚本 `--apply` → 重跑该区间导入 → 复检实体数回到 30。

### R3 饼图数字与源表对不上

- 先定位：区分四种情况。① 切片数比实体数少 → **正常**，窗口内零值不落库（6.6）；② 数字差一天/几天 → 该列在源表是多日汇总列，整体归到 `record_date`（6.1）；③ 电的量比源表**少** → 检查是否 `RTO用电` 之类被当成汇总行跳过（`ea51d979` 之前会丢约 16,834 kWh/月）；④ 页面比源表**多**（尤其电）→ 合计行重复计数，见 6.8.1。
- 口径提醒：页面/接口显示的是**剔除合计行后**的全厂口径（`动力运行` 与 `RTO` 的电不计入，见 6.1、`D-43`），而按车间明细列表逐行相加会得到含合计行的更大数值。对账前先确认用的是哪个口径，两者差值应等于 `SELECT sum(value) FROM energy.energy_monthly_records r JOIN energy.energy_workshops w ON w.id=r.workshop_id WHERE w.name IN ('动力运行','RTO') AND r.energy_type='electricity' AND r.is_deleted=false`（同窗口）。
- 校验：按 `energy_type` 对账：`SELECT energy_type, unit, count(*), sum(value) FROM energy.energy_monthly_records WHERE is_deleted = false GROUP BY 1,2;` 核对基准（2026-10-15 实测）electricity 16,488 / natural_gas 573 / steam 5,946 / water 10,332，总计 33,339 条。**注意这条 SQL 是含合计行的原始总量，不等于页面数**。
- 修复：若是跳过行导致，改 `SKIP_WORKSHOP_PATTERNS` 与别名后重跑；若是重复计数导致，在车间管理页勾选该项的「不计入全厂汇总」或补 `ROLLUP_WORKSHOPS` 常量（三种新建车间路径都要打标，见 10.1）；若是口径差异，改源表填报方式，不改代码。

### R4 库里又出现重复车间名

- 先定位：说明「只改了数据没改导入器」或「只改了导入器没改数据」。生效点有两处常量（第 10 章）。
- 校验：`SELECT name, count(*) FROM energy.energy_workshops GROUP BY name HAVING count(*) > 1;` 以及 `SELECT name, id, is_deleted FROM energy.energy_workshops WHERE name IN (:alias, :canonical);`
- 修复：`WORKSHOP_ALIASES` + `WORKSHOP_UNIFICATION` 同改 → 合并脚本先 `--audit-path` dry-run 看动作清单 → `--apply` → 重跑导入验证不反弹。

### R5 采集不触发

- 先定位顺序：① 运行时开关 `energy / ENERGY_AUTO_COLLECT_ENABLED`（设置页或 `core.module_settings`）；② 是否有 `is_enabled=true` 且未软删除的设备配置；③ 该设备 `collection_interval` 是否还没到期；④ 是否在 `MAX_BACKFILL_HOURS=168` 之外。
- 校验：`SELECT count(*) FROM energy.energy_device_configs WHERE is_enabled = true AND is_deleted = false;`；`SELECT platform_code, collect_time, status, device_count, success_count, error_message FROM energy.energy_collect_logs ORDER BY collect_time DESC LIMIT 10;`；日志里找 `energy.collection` worker 的 tick 记录。
- 修复：开关打开后**无需重启**（`scheduler.py:152` 每 tick 重读）；手动兜底用 `POST /api/v1/energy/collect/trigger`（或采集日志页「手动采集」）。注意采集值进 `energy_data`，**不会**改变总览/趋势/饼图（6.3、`D-42`）。

### R6 预警漏报或误报

- 先定位：判定只看日表「警戒线」（6.5），**与预警规则页无关**。漏报先查日表该行的「总数/警戒线」是否为空 —— `bitable_daily_import.py:80-88` 两者任一为空则整行跳过。
- 校验：`SELECT date, energy_type, category, total_value, alert_threshold, is_alert, alert_record_id FROM energy.energy_daily_data WHERE date = :check_date ORDER BY energy_type;` 与 `SELECT * FROM energy.energy_alert_records WHERE alert_time::date = :check_date;`
- 修复：补源表数值后重跑 `POST /sync/bitable/daily-import`；已生成记录的重复由 `alert_record_id IS NULL` 守卫挡住；等级不符则核对倍数分档（1.1/1.2）。误报若源于警戒线设错，改源表不改代码。

### R7 AI 分析必现失败

- 先定位三层：① 该车间该月有无电耗记录（`service.py:816` 会抛「能耗数据」未找到）；② LLM 调用是否成功（网关信封、畸形输出）；③ 前后端字段契约（`product_name` 键名，`748ef6e0` 的根因）。
- 校验：`SELECT count(*), sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND energy_type = 'electricity' AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false;`；后端日志找 `LLMOutputError` / `LLMProviderError`；跑 `uv run pytest tests/modules/energy/test_unit_consumption.py -q`（11 个降级路径用例）。
- 修复：按日志判因 —— 网关信封问题看 `fe2b0fa4` 的解包逻辑；结论缺失看 `506ed3fd` 的容忍分支；不要通过放宽 `expected_keys` 来"修"业务字段缺失。

### R8 导入返回 0 条 / 任务一直 running

- 先定位：`job_store.py` 是**进程内 dict**（`D-11`）—— 重启即丢、多副本不可见；一直 running 先看后端是否在任务执行中被重启。
- 校验：`GET /api/v1/energy/jobs/{job_id}`；后端日志里的 `errors[:10]`（行级异常**不落库**，`D-20`）。
- 修复：确认 `FEISHU__ENERGY__APP_TOKEN`（月度 base）与 `FEISHU__ENERGY__ALERT_APP_TOKEN`（日表 base）是否指向正确 base；权限不足或 token 失效表现为任务 failed 而非页面报错。长期方案是迁 `app/core/jobs.py` 任务队列（AGENTS.md 一次性异步任务约定）。

### R9 点「飞书导入」按钮报错

- 现状：`D-17` 已修（`lib/api/server/energy.ts:263` 现请求 `/api/v1/energy/monthly/import/feishu`）。若又报 404，先确认这条路径没被改回去。
- 先定位：`grep -n "import/feishu" frontend/src/lib/api/server/energy.ts backend/app/modules/energy/api.py` 两边对一遍；后端路由是 `@monthly_router.post("/import/feishu")` + `include_router(prefix="/monthly")` 装配出来的，直接搜完整路径搜不到。
- 校验：浏览器 Network 看状态码；`curl -X POST` 该路径，**401 = 路由存在只缺认证，404 = 路径错**，405 = 方法不对。
- 修复：改前端路径一处即可（属缺陷修复，不属口径变更）。急用时改用「交叉表导入」按钮走链路 1。

### R10 采集日志详情抽屉空白

- 现状：`D-26` 已修（`lib/api/client/energy.ts:44` 现请求 `/energy/collect/logs/${logId}/detail`）。
- 先定位：直接 `GET /api/v1/energy/collect/logs/{log_id}/detail` 与页面实际请求对比；同样用 401/404 区分「认证缺失」与「路径错」。
- 修复：若路径已对但详情仍空，是 `±30` 秒时间窗对补采串数据（`D-12`），需要按 `energy_data.collected_at` 核对。

### R11 设置页改了开关不生效

- 先定位：三处读取优先级不同（`D-40`）：自动采集只读运行时配置；月度同步 **env 优先、回退运行时配置**；每日同步小时**只读 env**。
- 校验：`SELECT key, value FROM core.module_settings WHERE module_code = 'energy';` 与部署环境变量对照。
- 修复：若 env 显式给了值，页面值会被盖掉 —— 清掉 env 值或按 8.3 的优先级说明操作。

### R12 单耗数字与总览对不上 / 提交目标报 422

- 先定位：单耗分子含四类能源裸值相加（`D-28`）+ 分母用折算产量，而总览按类型分开显示，两者**本就不可互推**（6.1 vs 6.4）。422 一般是目标单耗超过后端 `le=100`（`D-27`）。
- 校验：`SELECT energy_type, sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false GROUP BY 1;` 手算电单耗对比页面值。
- 修复：修 `D-28` 后两者可对齐；`TargetModal` 的 max 应降到 100 与后端一致。

## 10. 数据修复与迁移工具索引

### 10.1 车间别名合并脚本

`backend/scripts/migration/merge_energy_workshop_aliases.py` —— 能源模块**唯一**专用修复脚本。

| 约定 | 实现位置 | 要求 |
|---|---|---|
| 默认 dry-run | `--apply`（`:235`）才写库 | 任何环境先跑 dry-run 看动作清单 |
| 审计输出 | `--audit-path`（`:236`）写 JSON `{apply, actions[], blocked[]}` | 保留 JSON，它是**唯一**反向恢复依据 |
| 不变量守卫 | `:214-216` | 迁移前后按 `energy_type` 的 `count(*)` 与 `sum(value)` 必须全等，否则返回失败 |
| 重叠守卫 | `_find_conflicts`（`:74-82`）+ `REPOINT_TABLES`（`:46-49`）+ `CONFLICT_COLUMNS`（`:52-55`） | 逐对断言 `(energy_type, record_date)` 无重叠，重叠则该对跳过并报错 |
| 让出编码 | `:189-196` | 软删除时把 `code` 改写为 `<原code>#merged#<uuid前8>`（因 `uq_energy_workshop_code` 不含 `is_deleted`） |
| 名称字符串跟改 | `NAME_STRING_TABLES`（`:58`） | `energy_device_configs.workshop` 是字符串，必须跟着改名 |
| 幂等 | `_find_active`（`:130-132`） | 找不到别名即跳过；第二次运行 0 动作 |
| 顺序敏感 | `WORKSHOP_UNIFICATION`（`:34-43`，现 7 条） | 多条规则指向同一规范实体时，先跑的负责「改名」建出实体，后面的才能「合并」 |
| 不做的事 | — | 不做物理删除、不生成 Alembic 迁移、不改 `energy_alert_*` 与 `energy_daily_data`（无 workshop 列） |

**新增别名必须同时改两处**（缺一即「改数据 → 下次导入打回原形」）：

1. `backend/app/modules/energy/bitable_cross_import.py:30` `WORKSHOP_ALIASES`（现 9 条）
2. `backend/scripts/migration/merge_energy_workshop_aliases.py:34` `WORKSHOP_UNIFICATION`（现 7 条）

**新增合计行实体**改一处常量，但要注意三个建车间的入口都读它：

1. `models.py` `ROLLUP_WORKSHOPS`（打标源）；配套 `bitable_cross_import.py` 的 `ROLLUP_COMPONENTS` / `ROLLUP_CONTAINERS` 只用于一致性告警，源表增删机组时必须同步改，否则要么静默错算要么一直报偏差
2. `bitable_cross_import.py` `_get_or_create_workshop`、`bitable_sync.py`、`feishu_import.py` 三条路径**只在新建时**打标 —— 已存在的车间以车间管理页的人工配置为准，导入不会覆盖也不会取消
3. 库里已有的实体要么由迁移打标（`0069` 的做法），要么在 `/energy/workshops` 勾选，二者都要再跑一次 11.4 的对账

**执行范围**：数据迁移脚本只在本地执行验证；UAT / 生产由模块负责人自行执行同一脚本 `--apply`，随后触发按年/按月导入复测。

### 10.2 禁用脚本

`backend/scripts/seed/seed_energy_data.py`（当前未跟踪，**故意不入库**）会 `commit` 写入 4 个车间 + 5 条设备配置 + `random` 生成的 7 天小时级假数（`:72-126`）。它污染本地库并直接导致 `D-32` 三个用例失败。**任何环境都不要执行**。

### 10.3 相关 Alembic 迁移

| 迁移 | 内容 |
|---|---|
| `0001_baseline_full_schema` | 建 `energy_device_configs` / `energy_data` / `energy_collect_logs` / `energy_alert_rules` / `energy_alert_records`（唯一允许跨 schema 的基线） |
| `0045_energy_add_workshop_and_steam` | 建 `energy_workshops` + `energy_monthly_records`，含 `uq_energy_workshop_code`（`:40`）与 `uq_energy_monthly_record`（`:63`） |
| `0047_add_energy_daily_data_table` | 建 `energy_daily_data`，唯一键 `uq_energy_daily_data_date_type_category`（`:43`） |
| `0048_make_rule_id_nullable_in_energy_alert` | `energy_alert_records.rule_id` 改可空（`:23`），支撑无规则来源的日表预警 |
| `0054_add_energy_unit_consumption_targets` | 建单耗目标表，`uk_workshop_month`（`:36`） |
| `0059_add_energy_product_conversion_table` | 建折算系数表，`uk_product_name`（`:42`）+ 跨模块外键 `fk_epc_created_by`（`:45`） |
| `0060_merge_migration_heads` | 合并 `0056` + `0059` 双头（`:15`） |
| `0069_energy_add_workshop_excluded_energy_types` | `energy_workshops` 加 `excluded_energy_types varchar(20)[] NOT NULL DEFAULT '{}'`，并给 `动力运行`/`RTO` 打 `electricity` 标（`D-43`）。数据打标用静态字面量 SQL，不拼运行时输入 |

CI 约束：`scripts/ci/check_migration_numbers.py`（`:92-135`，四位顺序编号、文件名前缀必须等于 revision 前缀、不得重复、`down_revision` 必须存在）与 `check_migration_scope.py`（`:29-43`，单模块 schema 原则；`energy` 模块拥有 `energy` schema；跨模块 `referent_schema` 豁免但需架构负责人审批）。

## 11. 测试与验收基线

### 11.1 现有用例

`backend/tests/modules/energy/` 共 8 个文件 90 例（87 passed / 3 failed，3 例即 `D-32`）：

| 文件 | 例数 | 覆盖面 |
|---|---|---|
| `test_endpoint_paths.py` | 4 | `D-17`/`D-26` 回归护栏：正确路径可用（详情返回结构完整、导入 mock 掉飞书后按 `FeishuImportModal` 的真实载荷打通）**且**错误路径确实 404。模板串里的路径是运行时字符串，静态类型检查发现不了，所以两侧都要断言 |
| `test_bitable_workshop_alias.py` | 9 | 导入器别名解析、软删除不重用、水电气三叫法归一、RTO 电耗不被当汇总行丢弃、`车间映射` sheet 覆盖常量、缺表回退。飞书客户端 monkeypatch |
| `test_rollup_exclusion.py` | 15 | 合计行剔除：四个聚合口径只剔标记的能源类型、单车间口径不剔、软删除计入、导入器新建打标 / 不覆盖人工取消打标、一致性告警三态、`/overview` 与 `/workshops` 契约、生产叫法登记表守护。用 `2001-05` 独立日期 + `合计行甲` 等自造名，monkeypatch 三个常量，与库内数据解耦 |
| `test_unit_consumption.py` | 32 | 单耗计算 6 + 偏差率 5 + 偏差状态 4 + AI prompt 构造 3 + AI 数据契约 3 + LLM 降级 11。LLM 用 `patch(... llm_client.chat_json, AsyncMock)` |
| `test_api.py` | 9 | 设备 CRUD、触发采集、采集日志、统计、总览的响应契约 |
| `test_repository.py` | 8 | 设备配置查询与 `upsert_energy_data` |
| `test_service.py` | 7 | service 层设备 CRUD 与采集分支 |
| `test_models.py` | 6 | 模型与枚举定义 |

运行：`docker exec -w /app erp-backend uv run pytest tests/modules/energy/ -q`（`tests/` 不是挂载目录，单文件需先 `docker cp`）。静态检查：同容器内 `uv run ruff check <files>`、`uv run mypy <file>`。

### 11.2 三个既有失败用例（`D-32`）

成因：用例断言依赖 `energy_device_configs` 为空/唯一，而本地库有 `seed_energy_data.py` 写入的 5 行 zhiheng 假种子（`is_enabled=True`，3 条 `workshop=发酵车间`）；根 `tests/conftest.py:92-113` 只 rollback，不清表。

| 用例 | 位置 | 断言 vs 实际 |
|---|---|---|
| 列表按车间过滤 | `tests/modules/energy/test_repository.py:30` | `assert total == 1`，实得 4 |
| 按平台取启用设备 | `tests/modules/energy/test_repository.py:92` | `assert len(devices) == 1`，实得 6 |
| 按平台聚合设备数 | `tests/modules/energy/test_service.py:58` | `assert result["zhiheng"]["device_count"] == 0`，实得 5/6 |

修法（按优先级）：① mock 掉 `repo.get_enabled_devices_by_platform`（`patch(..., AsyncMock(return_value=[...]))`），断言与库内既有数据解耦；② fixture 用带 uuid 后缀的唯一 `platform_code`/`workshop` 自造数据，并在 `try/finally` 里删除；③ autouse fixture 前后快照该表。禁止为了让本地跑绿而删库里的行 —— 那是在掩盖 `D-19`。

### 11.3 覆盖缺口

无用例：预警规则/记录 CRUD、月度记录判重与 `date_range_end`、采集日志列表与详情（±30 秒窗口逻辑）、单耗目标持久化、`bitable_sync.py` / `bitable_daily_import.py` 主流程（仅别名解析被测）、`bitable_cross_import.py` 的表格解析与入库主流程（只测车间打标和合计行校验）、`adapters/platform_a.py` 的重试与分页。`get_overview_summary`/`get_energy_statistics`/`get_overview_trend` 与 `get_monthly_summary` **只有合计行剔除这一条被测**（`test_rollup_exclusion.py`），其余过滤组合仍无用例；车间 CRUD 只测 `excluded_energy_types` 的读写往返。`repository.py` 的函数只有 13 个被用例触达（`get_enabled_devices_by_platform` 多为 patch 替身，不算真实覆盖）。三方平台适配器**未被 mock**，测试里若真实调用会打外部网络。

### 11.4 对账基线（实测 2026-10-15）

- 未删除车间 **30**；月度记录 **33,339** 条，覆盖 2024-01-03 ~ 2026-10-09；按类型 electricity 16,488 / natural_gas 573 / steam 5,946 / water 10,332。
- 各能源规范实体数（分布核对基准）：电 27 / 水 20 / 汽 14 / 气 1。
- 近 30 天（2026-09-15 ~ 2026-10-15）**两个口径都要记**：
  - 全厂汇总口径（剔除合计行，页面与 `GET /monthly/summary`、`GET /data/statistics` 显示的数）：电 **1,574,929** kWh；水 22,618 m³；汽 2,605 t；气 4,977 Nm³。
  - 含合计行口径（按车间明细列表把每一行相加，含 `动力运行` 与 `RTO` 的电）：电 2,365,668 kWh，重复 790,739 kWh = `RTO` 16,834 + `动力运行` 773,905（33.43%）。
  - 水/汽/气两口径相同 —— 目前只有电存在合计行重复。
- `RTO` 实体同时持有 electricity 16,834 kWh（已标 `excluded_energy_types=['electricity']`）与 natural_gas 4,977 Nm³（未剔，全厂唯一气源）。
- 2026-04-01 之前的 28,717 条是全量重跑 34 张月度表回填的**真实历史数据，已确认保留**。
- 车间实体统一的 10 条验收实测见 [energy-workshop-unification.md](./energy-workshop-unification.md) §4。

## 12. 已知缺陷与遗留项登记表

状态含义：**待修**=本模块内可修；**下期**=已确认为下期需求；**非目标**=本期明确不做；**需审批**=需架构负责人或对应负责人处理；**数据侧**=需在飞书源表解决。

| 编号 | 缺陷 | 影响 | 位置 | 状态 |
|---|---|---|---|---|
| D-01 | 预警规则表从不参与判定，判定只认日表警戒线 | 用户以为配了规则就生效；6 个枚举字段与抽屉全表单形同虚设 | `energy_alert_rules` / `bitable_daily_import.py:227` | 待修（接线方案需业务确认，见 6.5） |
| D-02 | 前端请求 `GET /energy/production/output`（后端不存在），产量靠手填，另有随机 mock 产量函数；真实产量台账已在 production 模块 `/api/v1/production/product-output` | AI 分析页「从生产模块同步」必 404；单耗分母不可信 | `lib/api/client/energy.ts:194`、`service.py:621` | 下期（跨模块经 production `public_api.py` 取数） |
| D-03 | 折算系数表无任何写入入口 | 系数缺失时静默按 1.0，跨产品车间单耗可比性存疑 | `models.py:350`、无 API/页面 | 待修（需 CRUD + 页面） |
| D-04 | `import_year` 年度合计恒为 0 | 按年导入返回统计误导（数据本身正常入库） | `bitable_cross_import.py`（读 `created`/`updated`，实际键 `total_created`/`total_updated`） | 待修 |
| D-05 | `EnergyType` 枚举缺 `natural_gas` | 任何取枚举的代码无法表达气 | `models.py:32-35` | 待修 |
| D-06 | 天然气靠子串识别且**永久改写** `current_energy_type` | 源表把气行插到汽 section 中间，其后所有汽行会被记成天然气 | `bitable_cross_import.py`（映射文档缺陷 5） | 数据侧（需源表加独立标题行）+ 待修 |
| D-07 | `uq_energy_monthly_record` 不含 `date_range_end` | 同日期范围的两条表计互相覆盖 | `models.py:158-163` | 需审批（改约束要迁移） |
| D-08 | `uq_energy_workshop_code` 不含 `is_deleted`；`name` 与 `code` 共用一个查询命名空间 | 软删除行占着编码，重建同名车间撞唯一约束 | `models.py:62`、`bitable_cross_import.py` `_get_or_create_workshop` | 待修（需迁移，合并脚本已用 `#merged#` 让出） |
| D-09 | 两套日口径共存：汇总按 `record_date` 单点归期，单耗链路按日均分 | 页面数字不能互相对账 | `repository.py:227/306/340` vs `service.py:575-618` | 待修（6.1 已定口径：按单点归期） |
| D-10 | `get_monthly_energy_total` 不看 `date_range_end` 且用 `record_date < end` | 跨月范围记录漏计/错月 | `repository.py:864-885` | 待修 |
| D-11 | 异步任务状态是进程内 dict：重启丢、无进度、无 TTL、多副本不可见 | 导入任务"卡住"无法取证；内存无上限增长 | `job_store.py:7-28`、`app/core/tasks.py:20-48` | 需审批（应迁 `app/core/jobs.py`） |
| D-12 | 采集日志与采集值无外键，靠 ±30 秒窗口反推 | 补采（多小时批量 upsert）会漏或串数据 | `repository.py:411-452` | 待修 |
| D-13 | 车间缓存 key 三处不同源：`['workshops']` / `['energy-workshops']` / `['workshop', id]` | 改完车间另一页读到旧数据 | `ai-analysis/page.tsx:42`、`WorkshopTable.tsx:94`、`WorkshopDrawer.tsx:33` | 待修 |
| D-14 | 通知四字段无任何消费方 | 「配置了通知」是假象 | `models.py:246-253` | 非目标（已确认） |
| D-15 | 预警记录无车间维度、`unit=""`、`rule_id=None` | 预警只能按能源类型看，定位不到车间；页面单位空白 | `bitable_daily_import.py:235-245` | 待修 |
| D-16 | 设备与预警的能源类型下拉缺天然气 | 气类配置无法录入 | `DeviceDrawer.tsx:322-328`、`alerts/page.tsx:15-19` | 待修 |
| D-17 | 飞书导入按钮请求路径少一段，固定 404 | 月度页「飞书导入」不可用 | `lib/api/server/energy.ts:263` vs `api.py:936` | **已修**（路径改为 `/monthly/import/feishu`；请求体与响应本就是生成类型，无需改。回归护栏见 `test_endpoint_paths.py`） |
| D-18 | 重试策略三处不统一：平台 A 指数退避、飞书月度 `sleep(60)`×3、每日同步无重试 | 与 AGENTS.md 重试约定不符；失败行为不可预期 | `adapters/platform_a.py:126`、`scheduler.py:259-296/323-362` | 待修 |
| D-19 | 假种子脚本污染本地库 | 直接导致 D-32；本地对账数字失真 | `scripts/seed/seed_energy_data.py` | 需用户决定（不入库；本地是否清理待批） |
| D-20 | 导入行级异常只回调用方，不落任何日志表 | 事后无法追溯某行为什么没进来 | `bitable_cross_import.py:460,471`、`bitable_daily_import.py:174,185` | 待修 |
| D-21 | `/energy/workshops` 与 `/energy/settings` 菜单无入口 | 车间与设置只能直连 URL，主数据无法在 UI 维护 | `lib/menu-config.ts:61-72` | 待修 |
| D-22 | 饼图切片可达 58 片 | 可读性差、标签重叠 | `components/energy/DistributionChart.tsx` | 待修（Top-N + 其他） |
| D-23 | 三个抽屉用 `useEffect` + `setState` 取数填表 | 违反 React Hooks 规范与 React Compiler 前提 | `WorkshopDrawer.tsx:43-56`、`DeviceDrawer.tsx:119-128`、`AlertConfigDrawer.tsx:82-112` | 待修（计划 PR6） |
| D-24 | 孤儿代码 | 死代码误导维护 | `AlertsPageClient.tsx`、`CollectLogsPageClient.tsx`、`DevicesPageClient.tsx`、`actions/energy.ts:144 getWorkshops`、`lib/api/server/energy.ts:195 fetchWorkshops` | 待修（计划 PR4） |
| D-25 | `revalidatePath` 指向不存在的路由 `/energy/alert-rules`、`/energy/alert-records` | 写操作后页面缓存不失效 | `actions/energy.ts:115,127,138` | 待修 |
| D-26 | 采集日志详情前端路径与后端不一致，必然 404 | 排障主入口不可用 | `lib/api/client/energy.ts:44` vs `api.py:362` | **已修**（路径改为 `/collect/logs/{logId}/detail`；`apiGet` 已解 `data` 信封，`CollectLogDetail` 为生成类型。回归护栏见 `test_endpoint_paths.py`） |
| D-27 | 目标单耗上限前后端不一致（100 vs 9999.9999） | 提交大值报 422，用户不知原因 | `schemas.py:322` vs `TargetModal.tsx:108-118` | 待修 |
| D-28 | 单耗分子把四类能源裸值相加当 kWh | 与 6.4 口径冲突，单耗与偏差值不可信 | `repository.py:864-885` | 待修（口径已确认：只算电） |
| D-29 | 偏差分档取绝对值，节能 20% 也判 critical | 与 6.4 分档口径冲突 | `service.py:782-793` | 待修（口径已确认：只算超标） |
| D-30 | `prepare_daily_stats` 对 `date_range_end IS NULL` 的记录不施加窗口下界 | AI 分析会把窗口之前的单日记录算进来 | `service.py:585` | 待修 |
| D-31 | 两个 Bitable 自动同步开关未进种子表 | 只能在设置页外部配置，UI 看不到 | `scripts/seed/seed_module_settings.py:63-69` | 待修 |
| D-32 | 3 个既有失败用例假设设备配置表为空 | 模块测试不绿，CI 判定被稀释 | `test_repository.py:30,92`、`test_service.py:58` | 待修（11.2 修法） |
| D-33 | `category` 从未被导入器设置，四值形同虚设 | 分类筛选无业务含义（6.7） | `bitable_cross_import.py`、映射文档缺陷 2 | 待修（依赖 D-38） |
| D-34 | `.env.local` 曾提交进 Git 历史，后被删除 | 现工作树无此文件、`.gitignore:41` 已覆盖，但历史 blob 仍可检出（`A dfcd952d` 2026-06-22 → `M 845cb8e9` 06-27 → `D 18a66339` 07-01 / `D 62037cab` 07-06）。若其中的凭证是真实值，须视为已泄露 | 历史提交里的 `.env.local`（值不在本文出现）。**注**：本文曾误记为「仓库根 `.env` 被提交」——根 `.env` 从未进 Git（`git log -- .env` 为 0，`.gitignore:2` 覆盖），已更正 | 需核实 + 审批（先确认历史 blob 是否含真实凭证，再决定轮换与历史清除） |
| D-35 | `data/statistics` 的 `group_by` 非 `workshop` 时静默按车间 | 产线/设备维度统计不可用且不报错 | `repository.py:260-262` | 待修 |
| D-36 | 前端手写 API 类型（4 个响应模型） | 与 OpenAPI 漂移，违反契约条款 | `lib/api/client/energy.ts:97-194` | 待修（改用生成类型） |
| D-37 | AI 分析页三个写接口从浏览器直接 fetch | 绕过 CSRF/revalidation/错误边界 | `ai-analysis/page.tsx`、`TargetModal.tsx` | 待修（迁 Server Actions） |
| D-38 | `车间映射` sheet 尚未在多维表格创建 | 别名只能改代码，数据侧无法自助维护 | 飞书侧（映射文档缺陷 6） | 数据侧 |
| D-39 | 统计查询对车间 `is_deleted` 的过滤不一致 | 软删除车间的总量会混入部分口径 | `repository.py:255-256`（有）vs `306-337`、`823-861`（无） | 待修（`get_monthly_summary` 漏 `is_deleted` 已随 `D-43` 一并修；`get_overview_summary`/`get_overview_trend` 仍不看车间软删除） |
| D-40 | 配置读取优先级三处不一致（见 8.3） | 设置页改动对两个自动同步无效；违反 `os.getenv` 禁令 | `scheduler.py:144/152/230-233/241-243/321` | 需审批 |
| D-41 | `energy_daily_data` 的 `cost` / `municipal_meter` / `error_value` 无消费方 | 费用与市政总表对账能力未交付 | `models.py:317-319` | 非目标（范围外） |
| D-42 | 采集链路（`energy_data`）与填报链路（`energy_monthly_records`）无对账机制 | 两个数据源各说各话，总览只认填报值 | 6.3、第 4 章链路 5 | 待修（需业务定谁为准） |
| D-43 | 合计行与构成项同时入库，全厂电耗重复计数 | 全厂电虚高 33~35%（近 30 天重复 790,739 kWh）；饼图与汇总卡片与源表对不上 | `models.py` `ROLLUP_WORKSHOPS`、`repository.py` `_not_rollup_record`、迁移 `0069` | 已修（列 + 四处聚合口径剔除 + 导入期一致性告警，见 6.1、6.8.1） |
| D-44 | `get_monthly_summary` 按 `(energy_type, unit)` 分组，却用 `energy_type` 作结果 dict 的键 | 同一能源类型出现多种单位时后一行**静默覆盖**前一行，总量偏小且不报错 | `repository.py`（分组 `group_by(energy_type, unit)` / `summary[row.energy_type] = …`） | 待修（需与业务确认跨单位是否分别返回或强制换算，不宜静默相加） |
| D-45 | 两个前端函数指向后端从未存在的路由：`POST /energy/alerts/check`、`GET /energy/alerts/dates` | 目前**无用户可见影响** —— 只有 `actions/energy.ts:223/229` 的包装引用它们，没有任何页面调用；但一旦有人接上按钮就是必现 404，且会被误认为后端故障 | `lib/api/server/energy.ts:285,292`、`actions/energy.ts:223,229` | 待修（二选一：删掉这两个死包装，或在 `alerts` 路由补上等价端点；需业务确认是否要「按日期手动触发预警」能力） |

## 13. 变更记录

按 commit 追加，一行一个工作包。

| 日期 | commit | 内容 | 影响章节 |
|---|---|---|---|
| 2026-10-12 | `748ef6e0` | 修 AI 智能建议必现失败：`construct_ai_prompt` 读 `item['name']` 而生产者给 `product_name`，带产品的分析 100% 抛 `KeyError`；改用全局单例 `llm_client.chat_json` + `expected_keys`，异常收窄到 `LLMError` 并 `logger.exception`；`calculate_unit_consumption` 接受浮点产量，修掉 `int()` 截断导致 <1 归零的 500 | 5.7、R7 |
| 2026-10-13 | `506ed3fd` | 容忍畸形 LLM 输出：网关返回常是 `{建议,具体措施,预期效果}` 对象数组、偶发缺 `confidence_level`；改为只要求至少一段结论文本，其余字段按类型收敛 | 5.7、R7 |
| 2026-10-13 | `fe2b0fa4` | 解开网关 `json_object` 信封：约半数响应被包成 `{"type":"json_object","content":{…}}`，只读顶层字段会把完整结论误判为「AI 不可用」 | 5.7、R7 |
| 2026-10-13 | `825aeb4f` | AI 分析页三处 UI：`&gt;` 被当字符串字面量渲染、产品表格缺稳定 rowKey、antd v6 弃用 `Alert.message` | 5.7 |
| 2026-10-13 | `56f89ce8` | 测试先断言 `chat_json` 已被调用再取 `await_args`（mypy strict 下类型为 `_Call | None`） | 11.1 |
| 2026-10-15 | `4d936c37` | 三个页面冷加载不取数：把 `useEffect`+`setState` 迁到声明式 `useQuery`，queryKey 用固化 `today` 与格式化日期字符串 | 5.1、5.2、5.3 |
| 2026-10-15 | `d976e3b0` | 合并多维表格里的同义车间名：`WORKSHOP_ALIASES` + `车间映射` 覆盖 + 合并脚本 + 9 条单测 | 4.2、6.8、10.1 |
| 2026-10-15 | `100ff179` | 区域分布饼图按电/水/汽/气分开画：后端回传 `energy_type`，前端卡片内 Segmented | 5.1、6.2 |
| 2026-10-15 | `ea51d979` | RTO 电耗与气耗归到同一车间实体：去掉 `RTO用电` 跳过（每月约 16,834 kWh 曾被整行丢弃）+ 补 `303车间` 别名。**⚠ 方向有误，见下方 `b34d7f25`** | 6.8、R3 |
| 2026-10-15 | `386c23c8` | 补两份文档：月度交叉表字段映射、车间统一变更说明 | 0、4.2、10.1 |
| 2026-10-16 | `b34d7f25` | **更正 `ea51d979` 的方向 + 落地合计行剔除**。`ea51d979` 把 `RTO用电` 与 `RTO(天然气）` 合成一个实体，只解决了「电耗被整行丢弃」，却让 `RTO` 的电与容器 `环保中心(含RTO)` 的电同时计入全厂，重复计数由此重新引入；同理 `动力运行` 本来就是 6 台机组用电之和，一直与机组并计。正确做法是保留单一实体 + 按 `(车间, 能源类型)` 剔除：`energy_workshops.excluded_energy_types varchar[]` + 迁移 `0069`（建列并给 `动力运行`/`RTO` 打 `electricity` 标）；`ROLLUP_WORKSHOPS` 常量作为三种新建车间路径的唯一打标源；`repository.py` 新增 `_not_rollup_record()`，四处全厂口径接入（`get_overview_summary`、`get_energy_statistics`、`get_overview_trend`、`get_monthly_summary`），单车间口径不动；顺带修 `get_monthly_summary` 漏 `is_deleted`；交叉表导入新增 `_check_rollup_consistency`（容差 1%，只告警不改数，随 job 结果返回 `rollup_warnings`）；前端车间抽屉多选 + 列表「合计行」徽标，类型重生成；新增 `test_rollup_exclusion.py` 15 例 | 3.2、5.3、6.1、6.2、6.8.1、10.1、11.1、11.3、11.4、R3、D-39/D-43/D-44 |
| 2026-10-16 | `e86e2f7c` | 修掉两处必然 404 的前端端点路径（`D-17` 飞书导入少 `/monthly` 段、`D-26` 采集日志详情写成 `/energy/collect-logs/{id}`）。只改路径——请求体与响应都是生成类型，`apiGet` 已解 `data` 信封。后端路由由 `@monthly_router.post(...)` + `include_router(prefix="/monthly")` 装配，全文搜路径搜不到，这是当初写错没被发现的原因。同时把 `alerts/check` 与 `alerts/dates` 两个死包装登记为 `D-45`。配套 `test_endpoint_paths.py` 4 例（正确路径可用 + 错误路径确实 404，飞书按 AGENTS.md 必须 mock）；`FeishuImportModal` 的真实载荷即 mock 的入参，顺带锁住请求体契约 | 4、5.2、5.6、7、7.7、R9、R10、11.1、D-17/D-26/D-45 |
| 2026-10-16 | 本文更正 | **`D-34` 原判定有误**：本文曾记为「仓库根 `.env` 提交了真实 `app_token`」，实际根 `.env` 从未进 Git（`git log -- .env` 为 0 个提交，`.gitignore:2` 覆盖）。真实的历史暴露面是 `.env.local`：`A dfcd952d` → `M 845cb8e9` → `D 18a66339`/`D 62037cab`，工作树已无、`.gitignore:41` 已覆盖，但历史 blob 仍可检出。是否含真实凭证**未经核实**，故状态从「需审批」降为「需核实 + 审批」 | 8.4、D-34、13 待办 |
| 2026-10-16 | 本文 v1.0 | 首版模块 PRD：8 项业务口径经能源模块负责人确认（单耗只算电、预警以警戒线为准、产量本期手填、通知非目标、偏差只算超标、权限只写现状、`category` 写为目标口径、0 视为未填报） | 全文 |

**待办**（不属于文档缺陷，属工程排期）：车间实体统一的 UAT/生产执行由模块负责人完成；`D-34` 需先核实历史 `.env.local` blob 是否含真实凭证，再定责轮换/清除。

