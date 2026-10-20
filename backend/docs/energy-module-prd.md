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
| [energy-handoff-2026-10-16.md](./energy-handoff-2026-10-16.md) | 一个窗口的**交接便条**：当时未 commit 的工作包、待手测清单、本地环境踩坑 | 便条里的工作包状态已随 `ad725422` 落库而失效，不再逐条维护；进度、口径、基线一律以本文为准。只有它 §4 的本地环境操作要点（容器、只读探针、`psql -i` 姿势）是本文没有的 |
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
- **跨天记录的读口径**：第 6 章 6.1 的汇总/分布/趋势与 6.4 的单耗分子都按 `record_date` **单点归期**，跨天记录整体算进起始日。曾记为「另一套」的日均分摊 `service.prepare_daily_stats`（`service.py:590-633`，把 `value / days` 平均分到区间内每一天）**没有任何调用方**（v1 死代码，与 `D-30` 同族），所以运行时只有一套口径，页面数字之间可对账。`D-09` 相应更正。
- `get_monthly_energy_total`（`repository.py:959-987`）用 `record_date >= start AND record_date < end` 且**完全不看 `date_range_end`**：跨月范围的记录会被漏计或错月。列为 `D-10`。

### 3.5 软删除口径

- 删除业务数据一律置 `is_deleted = true`，不做物理删除。
- 「未删除」是所有统计与列表的默认前提，但必须**逐条查询显式声明**：`get_energy_statistics` 同时过滤记录与车间的 `is_deleted`（`repository.py:299-300`），`get_overview_summary`/`get_overview_trend` 只过滤记录未过滤车间，`get_monthly_summary`/`get_monthly_energy_total` 只过滤记录。
- 车间实体合并（第 10 章）是软删除 + 改挂 `workshop_id`，可逆；软删除时必须让出 `code`（`<原code>#merged#<uuid前8>`），否则日后重建同名车间撞 `uq_energy_workshop_code`。
- **导入命中软删行时必须复活**（置回 `is_deleted = false`，三处：`repository.batch_upsert_monthly_records`、`bitable_cross_import.import_month`、`bitable_daily_import.import_table`）。原因：`uq_energy_monthly_record` 与 `uq_energy_daily_data_date_type_category` 都**不含 `is_deleted`**（与 `uq_energy_device_config_platform_device` 相反），所以判重查询不能加 `is_deleted = false` 过滤——加了只会让插入分支撞 `UniqueViolation`，而不是绕过软删行。这条口径决定了「UI 删月度记录 → 改源表 → 重导入」是可行的修正路径（`D-46`）；复活时打 INFO 日志 `Reviving soft-deleted …`，便于排障时区分「导入成功但页面看不到」与「导入并恢复」。每日数据表当前**没有**软删除入口（有 DELETE 端点的是月度/车间/设备/预警规则/预警记录），其复活属预防性一致。预警记录的删除是软删除，并且**必须清掉** `energy_daily_data.alert_record_id`：留着引用等于永久屏蔽那一行，而多维表格的日数据每天都会被修正，改对之后重新导入应当按新用量重新判定（口径见 5.5）。

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
| 依赖接口 | 只读 `GET /api/v1/energy/overview`，经 `lib/api/client/energy.ts:35` `fetchEnergyOverviewClient`。无写操作 |
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
| 依赖接口 | 读 `GET /monthly`、`GET /monthly/summary`、`GET /workshops`（均 `lib/api/client/`）；删除走 Server Action `deleteMonthlyRecordAction`；导入走 `crossImportFromBitableAction`（`POST /sync/bitable/cross-import`，**异步任务，只回 `{job_id, status:"running"}`**）与 `importFromFeishuAction`（`POST /monthly/import/feishu`，同步返回计数，`D-17` 已修）。交叉表弹窗提交后由 `useEnergySyncJob` 每 1.5s 轮询 `GET /jobs/{job_id}`（`lib/api/client/energy.ts` 的 `fetchSyncJobClient`），`status=done` 才渲染计数并调 `onSuccess()` → `refreshMonthly()` 失效两个查询（`D-48` 已修）。此前本文写「导入后轮询」是错的（轮询从未实现），现已真正实现 |
| 取数与缓存 key | 列表 `['energy-monthly-records', {workshopFilter, energyTypeFilter, startDate, endDate, page, pageSize}]`（`MonthlyRecordTable.tsx:105`）；汇总 `['energy-monthly-summary', {...}]`（`:121`）；车间下拉 `['energy-workshops']`（`:132`）。日期在进 key 前格式化成字符串（`:96-98`），否则 dayjs 对象每次渲染重建导致缓存永不命中。写操作后按前缀显式失效两个 key（`:148-151`） |
| 交互与口径 | 筛选：车间（单选）、能源类型、RangePicker；分页默认 20 条可改（`:89,322`）；两个导入按钮（`:272-277`）；表格列展示 `value`+`unit`，跨天记录显示 `record_date` ~ `date_range_end`。筛选按 `workshop_id` 精确匹配 —— 这就是历史上「选质量控制部看不到水量」的根因，现由车间实体统一解决。**排序必须是全序**：原先只按 `record_date DESC` 排，而交叉表一次写入的几十条 `record_date` 完全并列，Postgres 不保证并列行的顺序，于是同一车间会在第 1 页和第 2 页各出现一次（加了车间/日期筛选后只剩一页，看起来就"正常"了）。现补上唯一键的其余两列 `workshop_id, energy_type` 决胜（`D-53` 已修） |
| 边界与空态 | 空结果渲染空表；删除有 `modal.confirm` 二次确认；交叉表导入弹窗有 5 个态：`running`（`Result status="info"`「导入进行中」，此态下「完成」按钮禁用，避免误以为已结束）、`done`（计数 + 错误明细最多 10 条，`total_errors>0` 时用 `warning`）、`failed`（`Result status="error"` + `error` 文案）、`unavailable`（轮询 404：状态存在后端进程内，重启即丢，`D-11`——提示「可能已写入，请刷新列表确认」，**不当作失败**）、`timeout`（>180s 停止轮询，同文案）（`D-48` 已修）；`value` 改成 0 **不会**删除既有记录，也不会新增（第 6 章 6.6） |
| 验收用例 | ① 选车间「质量控制部」→ 同屏应同时出现电与水的记录（历史上水记在 `QC` 上）；② 筛选后卡片汇总与列表逐行求和一致；③ 「交叉表导入」按 `2026-09` 走完「预览 → 确认」→ 任务 `done`，重查该月出现新记录且车间总数仍为 30；④ 删除一条记录 → 列表与汇总同步减少；⑤ 按年导入统计数字当前恒为 0（`D-04`），验收只看库内行数不看它；⑥ 不加任何筛选连翻两页 → 每行恰好出现一次（同一 `record_date` 的几十条不得重复，`D-53`） |
| 已知缺陷 | `D-04` 年度合计恒 0；`page.tsx` 只是 `'use client'` 套壳，未走 Server Component 取数。（`D-17` 飞书导入按钮 404 已修） |

### 5.3 车间管理 `/energy/workshops`（菜单不可达）

| 小节 | 内容 |
|---|---|
| 目的 | 维护车间主数据：编码、名称、分类、排序、启用、合计行标记 |
| 路由与入口 | `/energy/workshops`，标题「车间管理」（`workshops/page.tsx:8`）；**菜单无入口**，只能直连 URL |
| 依赖接口 | 读 `GET /workshops`（分页版 `fetchWorkshopsPageClient`）；写 Server Action `createWorkshop` / `updateWorkshop` / `deleteWorkshop` + `getWorkshopById` |
| 取数与缓存 key | 列表 `['energy-workshops', {categoryFilter, page, pageSize}]`（`WorkshopTable.tsx:102`）；抽屉单条 `['energy-workshops', 'detail', workshopId]`（`WorkshopDrawer.tsx:42`）。写后 `invalidateQueries({queryKey:['energy-workshops']})`（`WorkshopTable.tsx:115`）——裸前缀匹配即可覆盖列表、抽屉详情（`:42`）、月度页下拉（`MonthlyRecordTable.tsx:132`）与 AI 分析页选项（`ai-analysis/page.tsx:44`）四处 |
| 交互与口径 | 分类筛选四值（workshop/position/support/utility）；分页默认 20；抽屉字段：`code`（必填，≤50）、`name`（必填，≤100）、`category`、`excluded_energy_types`（多选，可空：电力/自来水/蒸汽/天然气）、`sort_order`（min 0）、`is_active`（`WorkshopDrawer.tsx:101-146`）。删除为软删除。`excluded_energy_types` 非空时列表名称列显示「合计行·电」一类徽标（`WorkshopTable.tsx`），语义见 6.1 与 6.8.1 |
| 边界与空态 | 列表请求失败 → `message.error('加载车间列表失败')`（`:99`）；删除前 `modal.confirm`；`category` 目前实际全是 `workshop`（第 6 章 6.7）；`excluded_energy_types` 为空数组 = 全部计入，历史车间由迁移 `0069` 初始化 |
| 验收用例 | ① 新建车间 → 月度记录页的车间下拉立刻出现该项；② 把某车间 `is_active` 关掉 → 它不再出现在筛选栏，但历史记录仍在；③ 用已软删除车间的 `code` 新建 → 当前会撞 `uq_energy_workshop_code`（`D-08`），预期是给出可读错误而不是 500；④ 给某车间勾选 `electricity` 后保存 → 能源总览卡片/饼图/趋势的全厂电量立刻减少该车间电量，但月度记录页选到该车间仍能看到它自己的值 |
| 已知缺陷 | 菜单不可达 `D-21`；`WorkshopDrawer` 用 `useEffect` + `setFieldsValue` 取数填表，违反 AGENTS.md（`D-23`）。~~车间缓存 key 三处不同源（`D-13`）~~ 已修：四处统一挂 `['energy-workshops']` 前缀 |

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
| 路由与入口 | `/energy/alerts`，标题「预警管理」，两个 Tab「预警记录 / 预警规则」（`alerts/page.tsx:283,351`） |
| 依赖接口 | 读 `GET /alerts/records`、`GET /alerts/rules`（client 分页版）；写 `processAlertRecord`（`PUT /alerts/records/{id}/process`）、`deleteAlertRecord`（`DELETE /alerts/records/{id}`，**新增**）、`deleteAlertRule`、`createAlertRule`（Server Action）；导入按钮 `syncBitableDailyDataAction`（`POST /sync/bitable/daily-import`，同为异步任务）。**已接轮询**：提交只存 `job_id`，`useEnergySyncJob` 轮到 `done` 才弹「新增 N 条，更新 M 条，自动生成 K 条预警记录」并 `refetchRecords()`；`failed`/`unavailable`/`timeout` 各有独立文案（`D-48` 已修）。此前它把 job 句柄当同步结果，toast 必然写成「新增 undefined 条」 |
| 取数与缓存 key | 规则 `['alert-rules', {rulesPage, rulesPageSize}]`（`:101`）；记录 `['alert-records', {recordsPage, recordsPageSize, filterDate, filterEnergyType}]`（`:121`），`filterDate` 转成**该数据日的 UTC 日窗口**（`00:00`–`23:59:59.999`）进 params（`:124-129`），与 `alert_time` 的存储口径一致（`D-50`）；分页默认 10 |
| 交互与口径 | 记录 Tab：导入数据、DatePicker、能源类型筛选、刷新；处理弹窗字段 `status`（默认 processed，必填）+ `process_note`；操作列两个按钮 —— pending 才有「处理」，任何状态都有「删除」（danger link，`modal.confirm` 二次确认，`AlertRecordTable.tsx:108-124`）。**删除口径 = 软删除 + 清反向引用**：置 `energy_alert_records.is_deleted = true`，同时把 `energy_daily_data.alert_record_id` 置回 `NULL`，但不动日数据行本身（`total_value`/`is_alert` 原样）。于是「删除 → 重导入」按新的用量重新判定：**仍超线就再生成一条，源表改到线下就不再生成**。改这条口径的理由是多维表格日数据每天被修正，永久屏蔽会让修正后的超标再也报不出来；代价是删掉的误报下次导入会回来 —— 不想它回来只能改源表或把状态处理掉。「预警日期」列只显示日期（`YYYY-MM-DD`，取 `alert_time` 的 UTC 日），因为预警按天判定、时刻无业务含义（`D-50`）；这个日期**必须等于多维表格「时间」列显示的那一天** —— 表格单元格按东八区录入，解析时必须换算到东八区再取日，按 UTC 取会整体早一天（`D-52` 已修）。规则 Tab 抽屉字段：规则名、能源类型、监控指标（instant/daily_total/monthly_total）、阈值类型（greater_than/less_than/equal）、阈值（min 0 必填）、单位（必填）、级别（info/warning/critical/emergency）、通知方式多选、通知用户、通知频率、生效时段（`AlertConfigDrawer.tsx:195-244`）。⚠️ **规则不参与判定**：判定只认日表警戒线（第 6 章 6.5） |
| 边界与空态 | 无记录时提示「暂无预警记录…请点击导入数据」（`AlertRecordTable.tsx:127-137`）；导入 toast 含新增/更新/预警数，且只在轮询到 `done` 后才出现（`alerts/page.tsx:257-258`）。**「更新 M 条」的口径是「值真变化的行数」**（`D-51`）：源表没改时 M=0，不再等于日表全部行数 |
| 验收用例 | ① 点「导入数据」→ 当天 `total_value > 警戒线` 的行生成记录且等级按 1.1/1.2 倍分档；② 把某条 pending 记录处理为已处理 → 状态、处理人、处理时间、备注都落库；③ 同一天的同一 `(date, energy_type, category)` 重复导入 → 不重复生成预警（靠 `alert_record_id IS NULL` 守卫）；④ 新建规则 → 列表出现，但**不会产生任何预警或通知**；⑤ 删除一条预警记录 → 列表不再出现、库里 `is_deleted = true`、日数据行的 `total_value`/`is_alert` 纹丝不动但 `alert_record_id` 被清空；⑥ 删完立刻再点「导入数据」，源表仍超线 → **重新生成一条新预警记录**（不是复用被删那条）；把源表改到线下再重导 → 不再生成（⑤⑥ 由 `test_alert_record_delete.py` 全链路覆盖）；⑦ 对已删除的 id 再删一次 → 404，不是 200；⑧ 列表与处理弹窗的「预警日期」等于多维表格「时间」列显示的那一天，不出现 07:59:59 这种跨日时刻（`D-50`、`D-52`）；⑨ 同一天多条预警时翻页不重复（`D-53`） |
| 已知缺陷 | `D-01` 规则未接线；`D-14` 通知字段无消费方；`D-15` 记录无车间维度、`unit=""`；~~`actions/energy.ts` 的 `revalidatePath('/energy/alert-rules')`、`'/energy/alert-records'` 指向**不存在的路由**~~ 已修（`D-25`：四处改成真实路由 `/energy/alerts`）。但**这页数据全走浏览器侧 React Query，`revalidatePath` 对它本身是空操作**，改对只是消除「已经失效」的错觉，不代表写操作后页面会自动刷新；`AlertConfigDrawer.tsx:82-112` `useEffect`+`setTimeout` 取数（`D-23`）；能源类型选项缺 natural_gas（`AlertConfigDrawer.tsx:15-19`）；`AlertsPageClient.tsx` 孤儿（`D-24`） |

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
| 已知缺陷 | `D-12`：日志与数据无外键，靠 `repository.py:482-483` 的 ±30 秒时间窗反推，补采（多小时批量 upsert）会漏或串；触发失败静默；`CollectLogsPageClient.tsx` 孤儿。（`D-26` 详情抽屉路径已修：原请求 `/energy/collect-logs/${logId}`，后端真实是 `/api/v1/energy/collect/logs/{log_id}/detail`） |

### 5.7 AI 分析 `/energy/ai-analysis`

| 小节 | 内容 |
|---|---|
| 目的 | 车间月度电单耗核算 + 目标偏差 + LLM 分析与建议 |
| 路由与入口 | `/energy/ai-analysis`，标题「AI 能耗智能分析」（`ai-analysis/page.tsx:175`） |
| 依赖接口 | 读 `GET /workshops?production_only=true`、`GET /targets/{workshop_id}/{target_month}`、`GET /production/output`（**后端不存在**；真实产量台账在 production 模块的 `GET /api/v1/production/product-output`，下期跨模块对接需走该模块 `public_api.py`）；写 `POST /ai-analysis-v2`、`POST /targets`、`PUT /targets/{target_id}`。**这三个写接口全部从浏览器直接 fetch**（`lib/api/client/energy.ts:119-195`），违反 AGENTS.md「写操作必须走 Server Actions」 |
| 车间范围口径 | **只有 9 个生产车间**：`101车间`、`102车间`、`103车间`、`105车间`、`201车间`、`202车间`、`301车间`、`302车间`、`303、106车间`。单耗 = 车间电耗 / 折算产量，对不上产品产量的辅助部门与机组（`动力运行`、`RTO`、各冷水机组等）算出来的「单耗」没有业务含义。白名单常量 `PRODUCTION_WORKSHOPS`（`models.py`，粒度是**车间名精确相等**，所以 `103车间` 不会命中 `103冷水机组`；`303、106车间` 是多维表格里的一个合并实体，保持一行不拆）。两道闸：读侧 `GET /workshops?production_only=true` 让选择器只出这 9 项；写侧 `prepare_ai_analysis_data` 对表外的车间直接 `BadRequestException` → 400。**主数据一行不删**——辅助部门与机组必须留在 `energy_workshops` 里，否则总览/全厂汇总对不上多维表格（`repository.py` 的聚合口径过滤 `is_deleted == false`）。`WorkshopCategory` 枚举在本库里几乎未用（30 行全是 `workshop`），不能当筛选依据，因此按名字匹配 |
| 取数与缓存 key | 车间 `['energy-workshops', 'ai-analysis-options']`（`:44`，与车间管理页同前缀，改完车间一次失效覆盖，`D-13`）；目标 `['target', workshopId, analysisMonth]`（`:55`，两个参数都非空才 `enabled`）；设定目标成功后失效同 key 并复算（`:146`）。其余是 `useState` 本地态 |
| 交互与口径 | 车间 Select + MonthPicker（`YYYY-MM`）；**产品产量列表手填**：表格内 `product_name` 文本 + `quantity` 数字逐行编辑，新增行的 `quantity` **是 `undefined`（输入框空、显示 placeholder）而不是预填 0**（`D-57`），单位固定 `kg`、列名「产量（kg）」并在 `InputNumber` 上挂 `addonAfter="kg"`（`:69`、`:217-231`），可增删行；「从生产模块同步」按钮调 `fetchProductionOutput`（路径不存在，`D-02`）。校验：月份匹配 `/^\d{4}-\d{2}$/`（`:104`）、产品明细非空（`:109`）、**逐行卡产品名非空与产量 > 0**（`:114-126`，这是 `D-56` 的前端防线），车间+月份+产量三项齐才允许点分析（`:252`）。目标弹窗 `TargetModal`：目标月份继承所选月份，目标单耗 `InputNumber` min 0.0001 / max 9999.9999 / precision 4 / step 0.1，后缀 `kWh/kg`（`TargetModal.tsx:108-118`），`handleOk` 校验 workshopId、数值、>0（`:46`）；已有目标走 update，否则 create（`:55-67`）。⚠️ 后端 schema 的上限是 `le=100`（`schemas.py:328`、`:334`），前端允许到 9999.9999 → 超限提交会被后端 422 拒（`D-27`） |
| 边界与空态 | 车间不在白名单（旧链接、脚本调用、车间被改名）→ 400「AI 能耗分析仅支持生产车间：…」。守卫在**取数和调用 LLM 之前**（`service.py:826-827`），所以既不会为辅助部门花一次模型调用，也不会先撞上「该月无能耗数据」的 404；车间本身不存在仍是 404（守卫在它之后）。未设目标 → 显示「未设定」+「➕设定目标」（`:277-284`），`deviation_status='unknown'` → 文案「未知（未设定目标）」（`:330`）；该车间当月无**电**耗记录 → 后端抛 `NotFoundException('能耗数据', '…无电耗数据')`（`service.py:842`），页面显示错误；产量全为 0 或空 → 前端逐行拦下（`:114-126`）；绕过前端直打接口 → 后端 `BadRequestException` → 400「折算后总产量必须大于 0，请填写每个产品的产量」（`service.py:873-874`）。`quantity` 键整个缺省也按 0 走同一条 400（`item.get("quantity", 0)`），不再抛裸 `ValueError` 让兜底 handler 报 500（`D-56` 已修）；LLM 输出畸形/不可用 → 降级为固定文案，不整链失败 |
| 验收用例 | ① 选车间+月份且该月有电耗 → 自动查出目标并显示单耗与偏差；② 填两条产品产量点分析 → 返回 `actual_unit_consumption`（4 位小数）、`target_unit_consumption`（无目标显示 `—`）、`deviation_rate`（带正负与颜色）、`ai_suggestion.summary/detailed_analysis/recommendations[]/confidence_level`；③ 设定目标成功后卡片立即复算且偏差状态改变；④ 断言折算系数缺失的产品按 `factor=1.0` 参与分母（`service.py:865`）；⑤ 把 `energy_product_conversions` 里某产品系数配成 2 → 折算产量翻倍、单耗减半；⑥ `GET /workshops?production_only=true` 只回 9 个生产车间，不带该参数仍能看到辅助部门（车间管理页不受影响）；⑦ 拿一个辅助部门 id POST `/ai-analysis-v2` → 400 且 `llm_client.chat_json` 未被调用；⑧ 分子只算电 —— 同一车间同月配齐电/水/汽/气四类行，`total_energy_kwh` 必须等于电那一类的和（护栏 `test_ai_energy_numerator.py`，含「裸值和 2000 vs 电 1000」对照组）；⑨ 负偏差（实际单耗低于目标）一律 `normal`，节能 20% 不再判 critical（护栏 `TestDeviationStatus::test_negative_deviation_is_normal`）；⑩ 点「添加产品」→ 新行的产量输入框**为空**（显示 placeholder，不是 0），列名与输入框后缀都带 `kg`；产量留空或填 0 点分析 → 前端 warning 拦住，不发请求（`D-57`，负责人 2026-10-16 已手测通过）；⑪ 绕过前端拿有电耗的生产车间直打 `POST /ai-analysis-v2`（`quantity: 0` 或整个缺省 `quantity`）→ **400**「折算后总产量必须大于 0」且 `llm_client.chat_json` 未被调用（`D-56` 已修，护栏 `test_ai_energy_numerator.py::TestZeroProductionIsBadRequest` 3 例） |
| 已知缺陷 | ~~第 6 章 6.4 的三项口径偏差~~ 本轮结清：分子含非电能源（`D-28`）**已修**、偏差取绝对值（`D-29`）**已修**、日均分摊窗口下界失效（`D-30`）**判定有误**（死代码，见 12 章）。仍开的：`D-27` 目标单耗上限前后端不一致（100 vs 9999.9999）、`D-02` 「从生产模块同步」打不存在的端点、`D-03` 折算系数表无任何写入入口（**实测表为空**，所以当前所有产品的 `factor` 都按 1.0，分母就是原始 kg）、`D-36` `AIAnalysisResult`/`AISuggestion`/`UnitConsumptionTarget`/`ProductionOutputItem` 全是手写 API 类型（`lib/api/client/energy.ts:110-196`）、`D-37` 三个写接口从浏览器直接 fetch、`TargetModal.tsx:38-43` 在 render 期 setState（未编号，与 `D-23` 同族）。~~车间缓存 key 与列表页不同源（`D-13`）~~ 已修：本页用 `['energy-workshops', 'ai-analysis-options']` |

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

- `get_overview_trend`（`repository.py:388-427`）按 `(record_date, energy_type)` 分组求和，可选按 `energy_type` 过滤。
- 只返回**有记录的日期**，不补零、不外推缺口。因此趋势图上相邻两点之间的间隔可能代表 2~4 天的合并填报列。
- 采集链路（`energy_data`）与趋势口径**不共用数据源**：总览/趋势/分布全部只读月度记录表，`energy_data` 目前只服务采集日志详情核对。

### 6.4 单耗与偏差（G2）

**口径（已确认）**

- 分子 = 该车间该月的**电耗合计**，单位 `kWh`。水/汽/气**不进**单耗分子。
- 分母 = 折算标准品产量 = Σ(产品产量 × 折算系数)，单位 `kg`。折算系数按产品名从 `energy_product_conversions` 取，**取不到按 `1.0`**（即该产品即标准品）。
- 实际单耗 = 分子 / 分母，`round(…, 4)`，单位 `kWh/kg`。分母 ≤ 0 视为无效输入并直接报错，不返回 0。
- 目标单耗按 `(车间, 月份)` 唯一，取值域 0.0001 ~ 100（后端 `schemas.py:328`、`:334` 的 `gt=0, le=100`）。前端 `TargetModal` 的 max 9999.9999 与之冲突，以后端为准（`D-27`）。
- 偏差率 = (实际单耗 − 目标单耗) / 目标单耗 × 100%，`round(…, 2)`。
- **偏差分档只算超标（正向）**：
  | 偏差率 | 状态 | 业务含义 |
  |---|---|---|
  | 无目标 | `unknown` | 未设定目标，不做判定 |
  | ≤ +5% | `normal` | 达标 |
  | +5% < x ≤ +15% | `warning` | 超标，需关注 |
  | > +15% | `critical` | 严重超标，需整改 |
  | < 0（低于目标） | `normal` | 节能，**不计预警**。异常偏低（漏报产量等）由人工在分析里判读，不用分档表达 |

**与现状实现的差异**：分子未按能源类型过滤（`D-28`）**已修** —— `get_monthly_energy_total` 增 `energy_type` 形参，`prepare_ai_analysis_data` 传 `EnergyType.ELECTRICITY`（`repository.py:959-987`、`service.py:837-839`）；分档对绝对值判定、节省 20% 也判 critical（`D-29`）**已修** —— `determine_deviation_status` 去掉 `abs()`，负偏差一律 `normal`（`service.py:797-810`）；日均分摊窗口的下界条件对 `date_range_end IS NULL` 的记录不生效（`D-30`）**判定有误**：`prepare_daily_stats` 多取的那些行在输出循环里被 `start_date <= current <= end_date` 挡掉（`service.py:623`），页面数字不受影响，而且该函数与 `fetch_mock_production`/`analyze_energy_with_ai`/`analyze_energy_with_vision` 都**没有任何调用方**（v1 死代码，实测 grep 全仓无引用），真实缺陷只是它漏了 `is_deleted` 过滤，属死代码内的瑕疵。护栏 `test_ai_energy_numerator.py` 的分子口径 6 例 + `TestDeviationStatus::test_negative_deviation_is_normal`。

### 6.5 预警判定（G3）

**口径（已确认：以日表「警戒线」为唯一判定基准）**

- 触发条件：`total_value > alert_threshold`，落库时同步置 `energy_daily_data.is_alert`。
- 等级分档（`bitable_daily_import.py:246-251`）：
  | 倍数 | 等级 |
  |---|---|
  | > 警戒线 × 1.2 | `critical` |
  | > 警戒线 × 1.1 | `warning` |
  | 仅 > 警戒线 | `info` |
- 幂等守卫：只为 `is_alert = true` **且 `alert_record_id IS NULL`** 的日数据生成记录，生成后回填 `alert_record_id`，因此同日重复导入不产生重复预警。这个反向引用同时是「这条预警已被确认过」的标记：删除预警记录会把它清空，于是下一次导入按新用量重新判定（`D-50` 那一版曾刻意保留，已改）。
- `energy_alert_rules` 的 `monitor_metric` / `threshold_type` / `threshold_value` / 生效时段 / 通知配置**全部不参与判定**（`D-01`）；本期不做通知送达（`D-14`）。
- 阈值来源：数值由飞书日表逐行给定，**不在本模块配置**。谁维护、按什么规则调线，属源表侧流程，本文不定义。
- **日期口径**：`energy_daily_data.date` 必须等于多维表格「时间」列显示的那一天。飞书日期单元格是 ms 时间戳，实测 5 张表恒为 `ms % 86_400_000 == 57_600_000`（16:00 UTC = 东八区 00:00），即按**东八区**录入 —— `_parse_timestamp` 必须 `astimezone(CST)` 再取日（`bitable_daily_import.py:62-68`）。按 UTC 取日会让整张日数据表早一天，连带 `check_alerts` 生成的预警日期、以及定时任务 `check_alerts(db, now.date())` 要查的那一天一起错开（`D-52`）。交叉表导入不受影响：它的日期来自**列头文本**（`bitable_cross_import.py:169-210`），不经过时间戳。

### 6.6 零值与未填报

**口径（已确认）**：`value > 0` 才落库；`0` 与空单元格都视为**未填报**，不落库。

- 后果 1：库内无法区分「没用」和「没填」，需要区分时回源表看。
- 后果 2：把源表某条从 5 改成 0 再导入，**不会删除**既有记录，`value` 也不会被改写（该行走 `value > 0` 守卫）。修正数据要么填正确值，要么走第 10 章脚本或月度页删除。**注意「月度页删除」之后只能重导入**（`D-46` 修复后导入会复活该行，3.5），手工重新新增会撞唯一约束（`D-47`）。
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

共 **43 个 operation**（`openapi.json` 里 `/api/v1/energy` 前缀实测计数）：`api.py` 内 42 个处理函数 + `GET /api/v1/energy/`（模块元信息，由 `app/shared/module_api.py:10` 的工厂注入，因此 `api.py` 里搜不到它）。

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
| `/api/v1/energy/monthly` | GET / POST | 月度明细列表 / 新增 | 列表由月度记录页使用；`POST` 只有 `actions/energy.ts:193` 的包装，**无 UI 入口** |
| `/api/v1/energy/monthly/{record_id}` | GET / DELETE | 单条读 / 软删除 | 删除由月度记录页使用；`GET` 无 UI 入口。**后端没有 PUT** —— 修正数值的可用路径是「页面上删除 → 改源表 → 重导入（`D-46` 修复后软删行会被复活，见 3.5）」；「删除 → 重新 POST」目前撞唯一约束（`D-47`）且不推荐 |
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
| `/api/v1/energy/jobs/{job_id}` | GET | 异步任务状态（进程内，`D-11`） | 响应定型为 `SyncJobStatus`（`status`/`result`/`error`），由 `useEnergySyncJob` 每 1.5s 轮询，交叉表导入弹窗与预警页「导入数据」都已接上（`D-48` 已修）。404 = 状态不可查，不是失败 |

### 7.4 预警

| 路径 | 方法 | 用途 | 调用页面 |
|---|---|---|---|
| `/api/v1/energy/alerts/rules` | GET / POST | 规则列表 / 新增（仅留存，不接线） | 预警管理 · 预警规则 Tab |
| `/api/v1/energy/alerts/rules/{rule_id}` | GET / PUT / DELETE | 单条读写与删除 | 预警管理 · 预警规则 Tab |
| `/api/v1/energy/alerts/records` | GET | 预警记录列表 | 预警管理 · 预警记录 Tab |
| `/api/v1/energy/alerts/records/{record_id}/process` | PUT | 处理（状态/处理人/备注） | 预警管理 · 处理弹窗 |
| `/api/v1/energy/alerts/records/{record_id}` | DELETE | 软删除预警记录并清空 `energy_daily_data.alert_record_id`（故重导入会按新用量重新判定） | 预警管理 · 记录操作列「删除」 |

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
| `lib/api/client/energy.ts:202` | `GET /energy/production/output` | 不存在，`D-02`；真实来源为 `GET /api/v1/production/product-output`（production 模块） |
| `lib/api/server/energy.ts:270` | ~~`POST /energy/import/feishu`~~ | **已修**：改为 `/energy/monthly/import/feishu`，见 `D-17` |
| `lib/api/server/energy.ts:295` | `POST /energy/alerts/check` | 不存在，且只有 `actions/energy.ts:226` 的孤儿包装引用，`D-45` |
| `lib/api/server/energy.ts:301` | `GET /energy/alerts/dates` | 不存在，同上孤儿包装，`D-45` |
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

本地执行环境要点（会踩的坑）：后端跑在容器 `erp-backend`（工作目录 `/app`），宿主机没有 `python`/`uv`，一切 Python 命令走容器；`backend/app` 是**只读** bind mount（宿主机改完容器内立即可见，但 `docker cp` 进去会被拒，`/app/app` 写不进去）；`backend/scripts` 是**可读写** bind mount，宿主机写完即可直接 `docker exec erp-backend uv run python scripts/...`，**不需要 `docker cp`**；`backend/tests` **不是**挂载，跑单个测试文件要先 `docker cp` 进容器；**`backend/` 根目录同样没挂**，所以 `export_openapi.py` 写出的 `/app/openapi.json` 要 `docker cp erp-backend:/app/openapi.json backend/openapi.json` 才落得回宿主机。dev 容器的 uvicorn **会热重载 `app/`**（实测改完 `api.py` 后 `curl :8000/openapi.json` 立刻出现新参数），但常驻调度任务是否随之重启未逐项核实，涉及 `scheduler.py` 行为的改动仍建议 `docker restart erp-backend`。宿主机**没有 `pnpm`**，前端命令走 `corepack pnpm <task>`。查库用 `docker exec -i erp-postgres psql -U postgres -d dazah`（库名是 `dazah`，不是 `livzon`；`-i` 必须带，否则 heredoc 的 SQL 不会送进去，命令静默无输出）。写脚本用 `from app.core.database import async_session_factory`，`docker cp` 到 `/tmp/` 后 `docker exec -w /app -e PYTHONPATH=/app erp-backend uv run python /tmp/xxx.py`。

### R1 某月数据缺失（导入没报错，库里没有）

- 先定位：`bitable_cross_import.py` 的表名匹配 —— 单月按表名**全等** `YYYY-MM`，`2026-6`、`2026年6月` 会**静默不导入**（映射文档「表结构契约」）。
- 校验：`SELECT count(*) FROM energy.energy_monthly_records WHERE record_date >= :month_start AND record_date < :month_end AND is_deleted = false;` 再看采集/导入侧 `logger` 的 `tables_imported`。
- 若上面 count 为 0、但作业回报 `updated: N, created: 0`：把条件换成 `is_deleted = true` 再数一次。这批行是被月度页软删除过的，导入命中它们后只会更新值。**`D-46` 修复后重导入会把它们复活**（3.5，日志有 `Reviving soft-deleted monthly record`）；修复前会停在「导入明明成功，页面和统计到处看不到」——这就是当初把它误判成导入坏了的原因。
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

- 先定位：判定只看日表「警戒线」（6.5），**与预警规则页无关**。漏报先查日表该行的「总数/警戒线」是否为空 —— `bitable_daily_import.py:85-88` 两者任一为空则整行跳过。
- 校验：`SELECT date, energy_type, category, total_value, alert_threshold, is_alert, alert_record_id FROM energy.energy_daily_data WHERE date = :check_date ORDER BY energy_type;` 与 `SELECT * FROM energy.energy_alert_records WHERE alert_time::date = :check_date;`
- 修复：补源表数值后重跑 `POST /sync/bitable/daily-import`；已生成记录的重复由 `alert_record_id IS NULL` 守卫挡住；等级不符则核对倍数分档（1.1/1.2）。误报若源于警戒线设错，改源表不改代码。删掉的预警在下一次导入时会按新用量重新判定（删除会清 `alert_record_id`），所以「删了又冒出来」是预期行为，不是缺陷。
- **预警的触发值/等级与当日用量对不上（甚至所在日根本不超标）**：`check_alerts` 只新建、**从不改写已生成的记录**，所以改源表 + 重导入**不会**修正旧预警，只会让日数据与预警各说各话（`D-52` 原地自愈后就是这样：188 条 10-15 批记录记的是**次日**的用量，55 条所在日实际未达标）。校验：`SELECT count(*) FROM energy.energy_alert_records a JOIN energy.energy_daily_data d ON d.energy_type=a.energy_type AND d.is_deleted=false AND d.date=(a.alert_time AT TIME ZONE 'UTC')::date WHERE a.is_deleted=false AND a.trigger_value IS DISTINCT FROM d.total_value;` 非 0 就有错位 → 跑 `scripts/migration/realign_energy_alerts_to_daily_data.py`（默认 dry-run，`--apply` 写库，可重复执行），再点一次「导入数据」重建。只想修**单条**别跑脚本：在页面删那条预警（会清反向引用）再导入即可。
- **预警日期与表格差一天**：日数据的日期必须等于表格「时间」列显示的那一天（6.5 日期口径，`D-52`）。校验 `SELECT max(date) FROM energy.energy_daily_data WHERE is_deleted = false;` 与表格里最后一天对比，少一天就是存量未修 → 跑 `scripts/migration/shift_energy_daily_date_to_cst.py`（见 10.2，**只能执行一次**）。⚠️ 前提：**修好代码后不能再跑** —— 全量重导入本身会让日期原地自愈，此时存量已经正确，再平移会把数据整体推早一天并撞唯一键回滚。判断存量该不该平移只看两点：`min(date)` 是否比表格第一天少一天、以及是否残留一个与次日数值逐字节相同的多出头一天（残留 = 已自愈，别再跑脚本）。

### R13 列表翻页时同一行重复出现

- 先定位：分页 `ORDER BY` 必须是全序（`D-53`）。并列行多时才会显现，所以**加了筛选就"好了"**——只剩一页而已。
- 校验：不筛选连翻两页，看同一主键是否出现两次；或 `SELECT record_date, count(*) FROM energy.energy_monthly_records WHERE is_deleted = false GROUP BY 1 ORDER BY 2 DESC LIMIT 5;` 单日几十条并列即触发条件。
- 修复：给该查询补决胜位（唯一键其余列或 `id`），不要改前端；五处已修，新增分页查询时照抄。

### R7 AI 分析必现失败

- 先定位三层：① 该车间该月有无**电**耗记录（`service.py:842` 会抛「能耗数据…无电耗数据」未找到）；② LLM 调用是否成功（网关信封、畸形输出）；③ 前后端字段契约（`product_name` 键名，`748ef6e0` 的根因）。
- 校验：`SELECT count(*), sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND energy_type = 'electricity' AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false;`；后端日志找 `LLMOutputError` / `LLMProviderError`；跑 `uv run pytest tests/modules/energy/test_unit_consumption.py -q`（11 个降级路径用例）。
- 修复：按日志判因 —— 网关信封问题看 `fe2b0fa4` 的解包逻辑；结论缺失看 `506ed3fd` 的容忍分支；不要通过放宽 `expected_keys` 来"修"业务字段缺失。
- **单耗数字莫名变小/某月突然掉一块**：先查该月有没有**跨月记录被删掉**。月度行的归属月只看 `record_date`（`D-10`），像 `record_date=2026-09-30` + `date_range_end=2026-10-08` 这种整段 11,650 kWh 只算进 9 月，一旦软删，9 月和 10 月**两边都不计**（2026-10-16 的 `102车间` 就是这个形状，见 11.4）。校验：`SELECT record_date, date_range_end, value, is_deleted FROM energy.energy_monthly_records WHERE workshop_id = :wid AND energy_type='electricity' AND record_date >= :month_start AND record_date < :month_end ORDER BY record_date;` —— 看有没有 `is_deleted = true` 且 `date_range_end` 跨过月界的行；要恢复就把该月交叉表重导入一次（`D-46` 的复活分支）。

### R8 导入返回 0 条 / 任务一直 running

- 先定位：`job_store.py` 是**进程内 dict**（`D-11`）—— 重启即丢、多副本不可见；一直 running 先看后端是否在任务执行中被重启。
- **提交成功 ≠ 导入完成**：`/sync/bitable*` 五个提交端点都在 ~50ms 内返回 `{job_id, status:"running"}`，计数只在 `GET /api/v1/energy/jobs/{job_id}` 的 `status=done` + `result` 里。两个导入 UI 已改为轮询到 `done` 才报数（`D-48` 已修），但轮询有两道兜底：进程内 store 重启后会 404（`D-11`，UI 显示「状态不可查」而非失败），超过 180s 停止轮询（显示「仍在进行」）。要确认是否真的入库，仍以 `GET /jobs/{job_id}` 或后端日志的 `Found/Parsed … records`、`Reviving soft-deleted …` 为准。
- 校验：`GET /api/v1/energy/jobs/{job_id}`；后端日志里的 `errors[:10]`（行级异常**不落库**，`D-20`）。
- 修复：确认 `FEISHU__ENERGY__APP_TOKEN`（月度 base）与 `FEISHU__ENERGY__ALERT_APP_TOKEN`（日表 base）是否指向正确 base；权限不足或 token 失效表现为任务 failed 而非页面报错。长期方案是迁 `app/core/jobs.py` 任务队列（AGENTS.md 一次性异步任务约定）。

### R9 点「飞书导入」按钮报错

- 现状：`D-17` 已修（`lib/api/server/energy.ts:270` 现请求 `/api/v1/energy/monthly/import/feishu`）。若又报 404，先确认这条路径没被改回去。
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

- 先定位：`D-28` 修后分子就是**该车间该月的电**，与总览按类型显示的「电」是同一个查询口径，两者**应当对得上**。还对不上时按顺序查三处：① 页面看的是不是全厂汇总（全厂口径会剔除 `动力运行`/`RTO` 的合计行，单车间口径不剔，见 6.1）；② 分母 —— `energy_product_conversions` **实测为空**（`D-03`），所以折算产量 == 手填的原始 kg，跨产品车间的「单耗」本来就不可比；③ 该车间该月有无其它三类的行（水/汽/气不进分子，看到总览的水汽气数大就觉得「单耗偏低」是错觉）。422 一般是目标单耗超过后端 `le=100`（`D-27`）。
- 校验：`SELECT energy_type, sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false GROUP BY 1;` —— `electricity` 那一行除以折算产量必须等于页面 `actual_unit_consumption`。2026-09 九车间电耗实测：`101车间` 31,228 / `102车间` 19,578 / `103车间` 6,169 / `105车间` 7,209 / `201车间` 41,047 / `202车间` 97,469 / `301车间` 93,233 / `302车间` 115,836 / `303、106车间` 95,132 kWh（均已用 `prepare_ai_analysis_data` 逐一走通实链路核对，与 SQL 聚合逐字节相等）。
- 修复：分子侧无需再动；把 `TargetModal` 的 max 降到 100 与后端一致（`D-27`），折算系数补进 `energy_product_conversions`（`D-03`）。

## 10. 数据修复与迁移工具索引

### 10.1 车间别名合并脚本

`backend/scripts/migration/merge_energy_workshop_aliases.py` —— 车间实体的专用修复脚本（日期口径的另见 10.2）。

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

### 10.2 日期口径修复脚本（一次性）

| 脚本 | 修什么 | 状态 |
|---|---|---|
| `scripts/migration/normalize_energy_alert_time.py` | `D-50`：把 `alert_time` 归一到当日 00:00 UTC，并清掉指向已软删预警的 `alert_record_id` | **已执行完毕**（本地实测两类待修行数均为 0），可视为用完，不需要再跑 |
| `scripts/migration/shift_energy_daily_date_to_cst.py` | `D-52`：把 `energy_daily_data.date` 与 `energy_alert_records.alert_time` 整体 +1 天，补回按东八区解析的那一天 | ❌ **未执行，且现在不得再执行**（2026-10-16 复核订正：本条此前被误记为「已由负责人执行」，误判依据是「预警 `alert_time::date` 与日行 `date` 0 处不一致」——这个判据**无效**，`alert_time` 本来就是从日行 `date` 生成的，一起错也一起对）。真实经过见 `updated_at` 取证：10-15 02:19 那批（解析口径还错着）写入的行里，`2025-12-31` 四行的 `updated_at` 仍等于 `created_at`（从未被再写入），而 `2026-01-01`/`2026-01-02` 的 `updated_at` 是 10-16 08:19 —— 说明 10-16 用**修好的解析代码做了一次全量重导入**，把每个数据日的值原地写到正确日期上，日期因此自愈；代价是唯一没被覆盖到的 `2025-12-31` 残留，其四类 `total_value`/`alert_threshold` 与 `2026-01-01` 逐字节相同（都是源表 01-01 那天的数），属**多出来的一天脏数据**（`is_alert=false`、无关联预警，但会进总览与趋势）。若脚本真跑过，`min(date)` 应是 2026-01-01 且不会有重复头一天。现在再跑会把已正确的数据整体推早一天，且 `2025-12-31 → 2026-01-01` 直接撞 `uq_energy_daily_data_date_type_category` 整体回滚。脚本本身**只能执行一次**（整表平移没有可复用判据），跑错方向用 `--days -1 --apply` 补回；下一次再需要平移必须先确认「代码解析口径」与「存量偏移」是否同时存在，不能照抄这次的操作 |
| `scripts/migration/realign_energy_alerts_to_daily_data.py` | `D-52` 的下游清理：软删「`trigger_value` 与当日实际用量不一致」的 live 预警，把指向已删记录的反向引用置回 `NULL`，再由一次导入按正确日数据重建 | ✅ **本地已执行**（2026-10-16：软删 188 条 10-15 批错位记录 → 点「导入数据」重建 → live 预警 205 条 = 超标日行 205 条，`trigger_value` 与当日不一致 0、幻影（所在日 `is_alert=false`）0、同日同类型重复 0；分类型 live：电 38 / 气 20 / 汽 77 / 水 70）。为什么必须清：`check_alerts` 只在 `alert_record_id IS NULL` 时新建、**从不改写已生成的记录**（`bitable_daily_import.py:233`），原地自愈只修日数据，那批把**次日**用量记到前一天的老记录会永久留在错日子上（实测链式：02-05 那条写着 1763，正是 02-06 的实际值），其中 55 条所在日子根本没到警戒线。脚本**可重复执行**（重建后 dry-run 报 0 行，已实测），默认 dry-run、`--apply` 才写库；UAT/生产若已用修好的代码重导入过同样要跑一次，若存量还停在「日期整体早一天」且从未重导入则它不会误删（那种状态下记录与所在日自洽），应先跑上一行的平移脚本修日期 |


### 10.3 禁用脚本

`backend/scripts/seed/seed_energy_data.py`（当前未跟踪，**故意不入库**）会 `commit` 写入 4 个车间 + 5 条设备配置 + `random` 生成的 7 天小时级假数（`:72-126`）。它污染本地库并曾直接导致 `D-32` 三个用例失败（该缺陷已修：用例改成与库内既有数据解耦，**但种子行本身仍在本地库里**，对账数字依旧失真）。**任何环境都不要执行**。顺带一条现状：这 29 个 ruff 报错也是 `ruff check scripts/` 唯一的失败来源，跑全量静态检查时别把它当成本轮回归。

### 10.4 相关 Alembic 迁移

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

`backend/tests/modules/energy/` 共 16 个文件 138 例，**全绿**（此前长期 3 例失败即 `D-32`，已修）：

| 文件 | 例数 | 覆盖面 |
|---|---|---|
| `test_ai_analysis_scope.py` | 7 | `D-54` AI 分析的车间范围：`PRODUCTION_WORKSHOPS` 的 9 个名字必须与 `energy_workshops` 里的 live 生产车间一一对上（登记表钉死，改名/新增车间不会静默漏出白名单）；`GET /workshops?production_only=true` 只回白名单、且等于库里全部 live 生产车间；不带参数（`category=support`）仍能看到辅助部门——对照组，证明主数据没被动过；`POST /ai-analysis-v2` 传辅助部门 → 400 且 `llm_client.chat_json` **未被调用**；`prepare_ai_analysis_data` 对辅助部门报 400 而不是「该月无能耗数据」的 404；`repository.list_workshops(name_in=…)` 是通用读取过滤，不含业务名（含 `name_in=[]` → 空表）。已验证：抽掉 service 守卫与 repository 过滤后各例转红 |
| `test_ai_energy_numerator.py` | 9 | `D-28` 单耗分子口径：同一车间同一月种齐电 1000 / 水 500 / 汽 200 / 气 300（裸值合计 2000），断言 `get_monthly_energy_total` 带 `energy_type='electricity'` 得 **1000**、不带过滤得 **2000**（对照组，证明生效不是巧合）；软删行不计入；`prepare_ai_analysis_data` 的 `total_energy_kwh == 1000.0`、`actual_unit_consumption == 100.0`；该月只有水/汽/气时抛 `NotFoundException('…无电耗数据')`；目标 110 时 `deviation_rate == -9.09` 且状态 `normal`。`TestZeroProductionIsBadRequest`（`D-56`）3 例：`quantity=0` 与整个缺省 `quantity` 都抛 `BadRequestException` 且 `status_code == 400`，HTTP 层再断 `POST /ai-analysis-v2` 真返回 400、文案含「产量」、`chat_json` 未被调用。用 `2001-05` 独立月 + 自造车间名，`monkeypatch` 把 `PRODUCTION_WORKSHOPS` 换成该车间。已验证：抽掉 repository 的 `energy_type` 过滤 → 4 例转红，只抽掉调用点实参 → 3 例转红，把 `abs()` 放回分档判定 → 本文件 1 例转红，把 `D-56` 那行改回裸 `ValueError` → 本文件 3 例转红（含 HTTP 层那条，裸异常会被 `auth_client` 直接抛出） |
| `test_bitable_daily_import.py` | 2 | `D-52` 日期口径：用表格里真实抓到的 ms（`1791907200000`，16:00 UTC = 东八区 00:00）断言 `_parse_timestamp` 与 `_parse_record` 得到的是**表格显示的那一天**，不是 UTC 那一天 |
| `test_list_pagination_order.py` | 2 | `D-53` 分页全序：`record_date` 完全并列的月度行、`alert_time` 完全并列的预警行，必须按补出的决胜位排序。固定 UUID + 哨兵日期让期望顺序与插入顺序错开且与存量数据隔离。已验证：分别抽回两处 `order_by` 后对应用例转红 |

| `test_alert_record_delete.py` | 6 | 预警记录软删除端点：200 + `is_deleted` 置位 + 从 `list_alert_records` 消失、未知 id 与重复删除都 404、删预警不动能耗数据行（`total_value`/`is_alert` 原样）但**清空 `alert_record_id`**、**仍超线时 `check_alerts` 会生成一条新记录**（并断言其 `alert_time` 是数据日 00:00 UTC，即 `D-50` 的护栏）、源表改到线下后不再生成。已验证：抽掉清反向引用那一行，`..._clears_back_reference` 与 `..._regenerated_while_still_over_threshold` 两例转红 |
| `test_sync_job_contract.py` | 11 | `D-48` 契约层 + `D-49`：OpenAPI 里 `SyncJobApiResponse.data` 必须解析到 `SyncJobStatus`（防止退回裸 `dict[str, Any]`，这是 D-48 能存在的根因）、5 个提交端点只回受理句柄不含计数、job 状态 running/done/failed 三态、契约外的键被丢弃、未知 job 404、按年导入的月度计数聚合。`spawn_task` 被 patch 成关闭协程，不真打飞书 |
| `test_soft_delete_revive.py` | 5 | `D-46` 回归护栏：三条导入链路（老飞书 `batch_upsert_monthly_records`、交叉表 `import_month`、每日 `import_table`）命中软删行后必须复活且被 `list_monthly_records` 读到；含「无同名行时仍走插入分支」对照组，和「复活不重复生成预警记录」的 `alert_record_id` 判重。飞书客户端 monkeypatch。已验证：抽掉三处 `is_deleted = False` 后恰好 3 例转红 |
| `test_endpoint_paths.py` | 4 | `D-17`/`D-26` 回归护栏：正确路径可用（详情返回结构完整、导入 mock 掉飞书后按 `FeishuImportModal` 的真实载荷打通）**且**错误路径确实 404。模板串里的路径是运行时字符串，静态类型检查发现不了，所以两侧都要断言 |
| `test_import_change_counts.py` | 5 | `D-51` 变更计数口径：`apply_changed_fields` 只在值真变时才赋值并返回 `True`（`Decimal("1.5")` vs `Decimal("1.50")` 必须判等，否则数值列每次导入都算变更）；`batch_upsert_monthly_records` 三次调用（插入 / 同值重复 / 改值）分别是 `(1,0)`、`(0,0)`、`(0,1)`；软删行同值复活仍算 1 次变更；每日与交叉表链路各跑两次同载荷导入，第二次必须 `total_updated = 0` 且 `total_parsed` 仍是源表行数。已验证：把 `apply_changed_fields` 的返回改成恒 `True`，5 例中 4 例转红 |
| `test_bitable_workshop_alias.py` | 9 | 导入器别名解析、软删除不重用、水电气三叫法归一、RTO 电耗不被当汇总行丢弃、`车间映射` sheet 覆盖常量、缺表回退。飞书客户端 monkeypatch |
| `test_rollup_exclusion.py` | 15 | 合计行剔除：四个聚合口径只剔标记的能源类型、单车间口径不剔、软删除计入、导入器新建打标 / 不覆盖人工取消打标、一致性告警三态、`/overview` 与 `/workshops` 契约、生产叫法登记表守护。用 `2001-05` 独立日期 + `合计行甲` 等自造名，monkeypatch 三个常量，与库内数据解耦 |
| `test_unit_consumption.py` | 33 | 单耗计算 6 + 偏差率 5 + 偏差状态 5（含 `test_negative_deviation_is_normal`，即 `D-29`）+ AI prompt 构造 3 + AI 数据契约 3 + LLM 降级 11。LLM 用 `patch(... llm_client.chat_json, AsyncMock)`；`_patched_energy_source` 里 mock 的车间名必须落在 `PRODUCTION_WORKSHOPS` 内（`101车间`），否则被 `D-54` 的生产车间守卫提前挡下、走不到被测计算路径 |
| `test_api.py` | 9 | 设备 CRUD、触发采集、采集日志、统计、总览的响应契约 |
| `test_repository.py` | 8 | 设备配置查询与 `upsert_energy_data`。列表过滤/按平台取启用设备两例用随机后缀的 `workshop`/`platform_code` 自造数据，与库内既有行解耦（`D-32`） |
| `test_service.py` | 7 | service 层设备 CRUD 与采集分支。「平台无设备」用例 mock `repo.get_enabled_devices_by_platform` 返回空表（`D-32`） |
| `test_models.py` | 6 | 模型与枚举定义 |

运行：`docker exec -w /app erp-backend uv run pytest tests/modules/energy/ -q`（`tests/` 不是挂载目录，单文件需先 `docker cp`）。静态检查：同容器内 `uv run ruff check <files>`、`uv run mypy <file>`。

### 11.2 三个既有失败用例（`D-32`，已修）

成因：用例断言依赖 `energy_device_configs` 为空/唯一，而本地库有 `seed_energy_data.py` 写入的 5 行 zhiheng 假种子（`is_enabled=True`，3 条 `workshop=发酵车间`）；根 `tests/conftest.py:92-113` 只 rollback，不清表。

| 用例 | 位置 | 当时的断言 vs 实际 | 处置 |
|---|---|---|---|
| 列表按车间过滤 | `tests/modules/energy/test_repository.py:20`（`test_list_device_configs_with_filters`，断言在 `:32`） | `assert total == 1`，实得 4 | ② 车间名加 `uuid4` 后缀，过滤条件即该后缀，别的行不可能命中 |
| 按平台取启用设备 | `tests/modules/energy/test_repository.py:83`（`test_get_enabled_devices_by_platform`） | `assert len(devices) == 1`，实得 6 | ② 平台编码加后缀（这条判的是「只返回 `is_enabled` 的行」，与既有数据无关） |
| 按平台聚合设备数 | `tests/modules/energy/test_service.py:58` | `assert result["zhiheng"]["device_count"] == 0`，实得 5/6 | ① mock `repo.get_enabled_devices_by_platform` 返回 `[]`。**这里不能用随机平台码**：`trigger_collection` 先查 `ADAPTERS`，未知平台直接走 `status="failed"` 分支，测不到「有适配器但无设备」 |

没有采用当时的候选 ③（autouse fixture 前后快照该表）——快照等于把「用例依赖环境数据」固化成机制。也**没有删库里的种子行**：`D-19` 那 5 行仍在本地库，只是测试不再受它影响；清理与否仍由负责人决定。

### 11.3 覆盖缺口

无用例：预警规则 CRUD、预警记录的**处理**（`PUT .../process`）与列表筛选参数（含 `D-50` 修掉的按日筛选窗口，只测了生成侧）；月度记录判重的 `date_range_end` 写入（「同名行存在且未删除」的正常分支与变更计数已由 `test_import_change_counts.py` 覆盖，软删复活分支由 `D-46` 覆盖）、采集日志列表与详情（±30 秒窗口逻辑）、单耗目标持久化、`bitable_sync.py` 主流程、`bitable_daily_import.py` 的 Decimal 与可选字段转换（时间戳那一半已由 `test_bitable_daily_import.py` 补上）——只有 `import_table` 的判重与复活分支被测。`bitable_cross_import.py` 的交叉表解析只在别名/合计行用例里间接触达，`import_month` 只测车间打标、合计行校验、软删复活和变更计数。`adapters/platform_a.py` 的重试与分页无用例。`get_overview_summary`/`get_energy_statistics`/`get_overview_trend` 与 `get_monthly_summary` **只有合计行剔除这一条被测**（`test_rollup_exclusion.py`），其余过滤组合仍无用例；车间 CRUD 只测 `excluded_energy_types` 的读写往返。`repository.py` 的 45 个顶层函数里只有 16 个被用例按名触达（`get_enabled_devices_by_platform` 多为 patch 替身，不算真实覆盖；本轮新增的 `apply_changed_fields` 有直接单测）。三方平台适配器**未被 mock**，测试里若真实调用会打外部网络。前端侧：`useEnergySyncJob` 的五态轮询没有任何自动化测试——本模块只有 Playwright e2e（`frontend/e2e/`），而它需要 `APP_ENV=test/e2e` + `E2E_AUTH_SECRET` 才拿得到会话，本地开发环境起不来，所以 `D-48` 的 UI 修复目前只有契约测试 + `typecheck`/`lint` + 人工点击背书。`D-53` 的五处排序修复里只有月度与预警两处有断言，`list_energy_data`/`list_collect_logs`/`list_alert_rules` 三处补的决胜位无用例（这三张表的并列条件目前还没在真实数据里出现，属预防性一致）。`D-13` 的四个车间 queryKey 只靠命名约定对齐，没有测试能挡住第五处新 key 又写错前缀。`D-54` 的两条护栏都有盲区：`test_production_workshop_registry_is_locked` 只钉常量内容，`test_production_only_filter_returns_all_live_production_rows` 又是「端点结果 == 库里名字在白名单内的行」的循环断言，所以**库里新增第 10 个生产车间时会静默落在白名单外**（选择器看不到它、分析 400），只能靠负责人改名/新增车间时同步维护 `PRODUCTION_WORKSHOPS`；前端选择器只显示 9 项这件事也没有任何自动化测试。**手测进展（2026-10-16）**：负责人已把交接文档 §3 的 9 条 UI 条目全部点完，未报新问题（`D-54` 的下拉 9 项在前一轮已单独确认过）。注意这只补上了「人工点击」那一层背书，上面列的自动化盲区一条都没减少 —— 页面行为今后仍只能靠回归测试而不是手测记录来防回归。**检查口径本身也有一处盲区（2026-10-18 核出）**：CI 的静态检查是**不对称**的 —— `scripts/ci/ci.sh:183` 跑 `ruff check .`（全仓，含 `scripts/`），而 `:204` 只跑 `mypy app tests`，**`scripts/` 完全不在类型检查范围内**。所以本模块放在 `scripts/migration/`、`scripts/test/` 的 5 个脚本从没被 strict mypy 挡过；本轮手工查出 7 处并已清零（`merge_energy_workshop_aliases.py` 四个函数缺 `AsyncSession`/返回注解、一处 `Returning Any`；`realign_energy_alerts_to_daily_data.py:113` 的 `Result` 上没有 `rowcount`）。既有基线同样不干净（main 上的 `scripts/migration/backfill_all.py` 同跑法 10 处），因此这不是本 PR 的回归而是仓库通行状态；但一次性脚本改的是真实数据，恰恰是类型检查最该挡住的那类错误。

### 11.4 对账基线（实测 2026-10-15，**2026-10-16 20:15 复核**，2026-10-17 凌晨二次复核逐条一致）

- 未删除车间 **30**；月度记录 live **33,336** 条（另有 6 条已软删），覆盖 2024-01-03 ~ 2026-10-09；按类型 electricity 16,487 / natural_gas 573 / steam 5,945 / water 10,331。**比 10-15 记的 33,339 少 3 条**，差额是 `102车间` `2026-09-30`（`date_range_end = 2026-10-08`）的电 11,650 kWh / 汽 6 t / 水 228 m³ 三行，于 10-16 **17:22（本地）** 被软删（`source` 仍是 `feishu_bitable`，`created_at` 属 10-15 01:53 那批交叉表导入）。**操作主体未经确认**：时间落在负责人的手测窗口内，agent 本轮只做过只读探针、没有写库。若是误删，重跑交叉表导入会按 `D-46` 的复活分支把它们捞回来。这 3 行同时是 `D-10`/`D-07` 的活样本：跨月记录整段计入 `record_date` 所在月（9 月），软删之后 `2026-09-30 ~ 10-08` 这段在 9 月和 10 月两个窗口里都不再计入，`102车间` 的 2026-09 电因此从 31,228 变成 **19,578** kWh。
- 车间按 AI 分析口径分层（2026-10-16 实测）：30 个 live 里**生产车间 9**（`PRODUCTION_WORKSHOPS` 全部命中，无静默漏项）、**非生产 21**（`103冷水机组`/`201盐水机组`/`4号楼冷水机组`/`500T冷水机组`/`500T盐水机组`/`空压氮气系统`/`纯化用水`/`锅炉用水`/`动力运行`/`动力车间`/`RTO`/`环保中心`/`401~405岗位`/`仓库`/`办公楼`/`饭堂`/`质量控制部`）。⚠️ `energy_workshops.category` **30 行全是 `workshop`**，四值枚举形同未用，所以车间筛选不能靠 `category`（`D-54` 因此按名字白名单）。另有 9 行已软删（含 `303车间`/`QC`——都在规范实体统一时并进了 `303、106车间`/`质量控制部`）。
- 各能源规范实体数（分布核对基准）：电 27 / 水 20 / 汽 14 / 气 1。
- 预警记录（2026-10-16 清理后）：live **205** 条 = 超标日行 **205** 条，逐条 `trigger_value` 等于所在日 `total_value`、所在日 `is_alert=true`、同日同类型无重复；分类型 live：电 38 / 气 20 / 汽 77 / 水 70，全部 `pending`。另有 211 条已软删（其中 188 条是 10-15 批错位记录，由 `realign_energy_alerts_to_daily_data.py` 清掉，见 10.2）。天然气日期范围 2026-02-06 ~ 2026-07-03，9 月下旬至今确实零条 —— 日用气实测 56 ~ 601，全在警戒线 1000 以下，不是漏报。**2026-10-16 20:15 复核（本轮 `ad725422` 提交之后）**：live 仍 **205**、`trigger_value` 与所在日 `total_value` 不一致 **0**、无对应日行的幻影 **0**、同日同类型重复 **0**、所在日其实不达标的 **0**，且 `status <> 'pending'` 的 **0** 条（没有一条被处理过）。
- 日数据（2026-10-16 复核）：未删 **1160** 行 = **290** 个日期 × 4 类，日期跨度 `2025-12-31 ~ 2026-10-16`。其中 **`2025-12-31` 那 4 行是脏数据**：四类 `total_value`/`alert_threshold` 与 `2026-01-01` 逐字节相同，`updated_at == created_at`（10-15 02:19 那批按错误解析写入后从未被再动过）—— 它是 `D-52` 修好后由全量重导入原地自愈时唯一没被覆盖到的残留日，`is_alert=false` 且无关联预警，但仍会被总览/趋势当作一天计入。核对时按 **289 天** 才是真值（2026-01-01 ~ 2026-10-16）。**2026-10-16 20:15 复核未变**：未删 **1160** 行、`max(date)` = `2026-10-16`、`2025-12-31` 那 4 行仍在（**仍等负责人批准删除**），且 `is_deleted = true` 的日行仍是 **0** —— 所以 `D-55` 到现在也没被真实数据暴露过一次。
- 近 30 天（2026-09-15 ~ 2026-10-15）**两个口径都要记**：
  - 全厂汇总口径（剔除合计行，页面与 `GET /monthly/summary`、`GET /data/statistics` 显示的数）：电 **1,574,929** kWh；水 22,618 m³；汽 2,605 t；气 4,977 Nm³。
  - 含合计行口径（按车间明细列表把每一行相加，含 `动力运行` 与 `RTO` 的电）：电 2,365,668 kWh，重复 790,739 kWh = `RTO` 16,834 + `动力运行` 773,905（33.43%）。
  - 水/汽/气两口径相同 —— 目前只有电存在合计行重复。
- `RTO` 实体同时持有 electricity 16,834 kWh（已标 `excluded_energy_types=['electricity']`）与 natural_gas 4,977 Nm³（未剔，全厂唯一气源）。
- 2026-04-01 之前的 28,717 条是全量重跑 34 张月度表回填的**真实历史数据，已确认保留**。
- AI 分析分子的核对基线（2026-10-16，`2026-09` 九个生产车间，实链路 `prepare_ai_analysis_data` vs SQL 聚合逐一相等）：电 `101车间` 31,228 / `102车间` 19,578 / `103车间` 6,169 / `105车间` 7,209 / `201车间` 41,047 / `202车间` 97,469 / `301车间` 93,233 / `302车间` 115,836 / `303、106车间` 95,132 kWh。同月四类**裸值相加**（`D-28` 修前的分子）与电的差即虚高幅度：`202车间` **+5.95%**、`103车间` +5.35%、`301车间` +2.73%、`303、106车间` +2.65%、`102车间` +2.57%、`302车间` +2.45%、`101车间` +2.36%、`201车间` +2.03%、`105车间` 0%（该月只有电）。**2026-10-16 20:15 逐车间复核仍是这九个数**（`102车间` 的 19,578 已经是上面那三条跨月行被软删之后的值，删之前是 31,228）。
- 单耗目标表 `energy_unit_consumption_targets` live **5** 条（此前 11.4 未记，本轮补）：真业务行只有 `101车间` 两条 —— `2026-07` = 5.5、`2026-09` = 6.5 kWh/kg；另 3 条挂在 `D-19` 的假种子上（`_seed_发酵车间` `2026-09` = 8.0 / `2026-10` = 5.0、`_seed_提取车间` `2026-10` = 8.0），而这两个车间本身**已经软删** —— 即 3 条 live 目标指向已不存在的实体，是孤儿行。清理种子数据时必须连带它们，否则目标列表里永远留着不存在的车间。
- `energy_product_conversions` **实测 0 行**（`D-03`；2026-10-16 20:15 复核仍是 0 行）：所有产品的折算系数都按 `1.0` 取，单耗分母 == 手填原始 kg。核对单耗数量级时不要去找"系数表"，它还是空的。
- 车间实体统一的 10 条验收实测见 [energy-workshop-unification.md](./energy-workshop-unification.md) §4。

## 12. 已知缺陷与遗留项登记表

状态含义：**待修**=本模块内可修；**下期**=已确认为下期需求；**非目标**=本期明确不做；**需审批**=需架构负责人或对应负责人处理；**数据侧**=需在飞书源表解决。

| 编号 | 缺陷 | 影响 | 位置 | 状态 |
|---|---|---|---|---|
| D-01 | 预警规则表从不参与判定，判定只认日表警戒线 | 用户以为配了规则就生效；6 个枚举字段与抽屉全表单形同虚设 | `energy_alert_rules` / `bitable_daily_import.py:233-255`（判定只读日表的 `alert_threshold`，`rule_id=None`） | 待修（接线方案需业务确认，见 6.5） |
| D-02 | 前端请求 `GET /energy/production/output`（后端不存在），产量靠手填，另有随机 mock 产量函数；真实产量台账已在 production 模块 `/api/v1/production/product-output` | AI 分析页「从生产模块同步」必 404；单耗分母不可信 | `lib/api/client/energy.ts:202`、`service.py:636` | 下期（跨模块经 production `public_api.py` 取数）。`fetch_mock_production` 与 `D-30` 同属 v1 死代码，全仓无调用方 |
| D-03 | 折算系数表无任何写入入口 | 系数缺失时静默按 1.0，跨产品车间单耗可比性存疑 | `models.py:387`、无 API/页面 | 待修（需 CRUD + 页面） |
| D-04 | `import_year` 年度合计恒为 0 | 按年导入返回统计误导（数据本身正常入库） | `bitable_cross_import.py`（读 `created`/`updated`，实际键 `total_created`/`total_updated`） | 待修 |
| D-05 | `EnergyType` 枚举缺 `natural_gas` | 任何取枚举的代码无法表达气 | `models.py:32-35` | 待修 |
| D-06 | 天然气靠子串识别且**永久改写** `current_energy_type` | 源表把气行插到汽 section 中间，其后所有汽行会被记成天然气 | `bitable_cross_import.py`（映射文档缺陷 5） | 数据侧（需源表加独立标题行）+ 待修 |
| D-07 | `uq_energy_monthly_record` 不含 `date_range_end` | 同日期范围的两条表计互相覆盖 | `models.py:195-200`（`uq_energy_monthly_record` 的三列） | 需审批（改约束要迁移） |
| D-08 | `uq_energy_workshop_code` 不含 `is_deleted`；`name` 与 `code` 共用一个查询命名空间 | 软删除行占着编码，重建同名车间撞唯一约束 | `models.py:62`、`bitable_cross_import.py` `_get_or_create_workshop` | 待修（需迁移，合并脚本已用 `#merged#` 让出） |
| D-09 | ~~两套日口径共存~~ **原判有误**：日均分摊那条链路（`prepare_daily_stats`）是 v1 死代码，无调用方 | 原记「页面数字不能互相对账」不成立 —— 运行时只有 `record_date` 单点归期这一套口径 | `repository.py:281-282/303-304/354-355/390-391` vs `service.py:590-633`（死代码） | **判定有误，不修**（与 `D-30` 同族，随 v1 死代码清理一并处理）。真正剩下的只有 6.1 已定口径本身：跨天记录整体计入起始日，`date_range_end` 在 live 链路里不参与归期 |
| D-10 | `get_monthly_energy_total` 只看 `record_date`（`>= start` 且 `< end`），完全不看 `date_range_end` | 跨月范围的记录整段算进起始那一月，月与月之间既可能重复也可能漏 | `repository.py:959-987` | 待修。**2026-10-16 有一个活样本**（见 11.4）：`102车间` `record_date=2026-09-30`、`date_range_end=2026-10-08` 的电/汽/水三行，11,650 kWh 全部计入 9 月；这三行被软删后，`2026-09-30 ~ 10-08` 这段在 9 月和 10 月的窗口里都不再出现 —— 单耗分子（`D-28` 只算电）与总览月柱都会跟着掉，而页面没有任何地方提示「本月缺 9 天」 |
| D-11 | 异步任务状态是进程内 dict：重启丢、无进度、无 TTL、多副本不可见 | 导入任务"卡住"无法取证；内存无上限增长 | `job_store.py:20-32`（进程内 `self._jobs` dict）、`app/core/tasks.py:20-48` | 需审批（应迁 `app/core/jobs.py`） |
| D-12 | 采集日志与采集值无外键，靠 ±30 秒窗口反推 | 补采（多小时批量 upsert）会漏或串数据 | `repository.py:462-502`（`get_collect_log_detail`，默认 `time_window_seconds=30`） | 待修 |
| D-13 | 车间缓存 key 三处不同源：`['workshops']` / `['energy-workshops']` / `['workshop', id]` | 改完车间另一页读到旧数据 | `ai-analysis/page.tsx:44`、`WorkshopTable.tsx:102`、`WorkshopDrawer.tsx:42` | 已修（四处统一挂 `['energy-workshops']` 前缀：列表带参数对象、月度页下拉为裸前缀、AI 分析页 `'ai-analysis-options'`、抽屉详情 `'detail', id`；车间保存后 `invalidateQueries(['energy-workshops'])` 一次覆盖全部） |
| D-14 | 通知四字段无任何消费方 | 「配置了通知」是假象 | `models.py:283-288` | 非目标（已确认） |
| D-15 | 预警记录无车间维度、`unit=""`、`rule_id=None` | 预警只能按能源类型看，定位不到车间；页面单位空白 | `bitable_daily_import.py:248-258` | 待修 |
| D-16 | 设备与预警的能源类型下拉缺天然气 | 气类配置无法录入 | `DeviceDrawer.tsx:322-328`、`AlertConfigDrawer.tsx:15-19` | 待修 |
| D-17 | 飞书导入按钮请求路径少一段，固定 404 | 月度页「飞书导入」不可用 | `lib/api/server/energy.ts:270` vs `api.py:951` | **已修**（路径改为 `/monthly/import/feishu`；请求体与响应本就是生成类型，无需改。回归护栏见 `test_endpoint_paths.py`） |
| D-18 | 重试策略三处不统一：平台 A 指数退避、飞书月度 `sleep(60)`×3、每日同步无重试 | 与 AGENTS.md 重试约定不符；失败行为不可预期 | `adapters/platform_a.py:126`、`scheduler.py:259-296/323-362` | 待修 |
| D-19 | 假种子脚本污染本地库 | 曾直接导致 D-32（现已修，测试不再依赖空表）；`ruff check scripts/` 的 29 个报错全部来自它 | `scripts/seed/seed_energy_data.py` | 需用户决定（**脚本本身不入库**）。**2026-10-16 20:15 复核残留已经缩小但没有清零**：4 个 `_seed_*` 车间（制剂/动力/发酵/提取）全部已软删、月度行也只剩 3 条软删，**但 `energy_unit_consumption_targets` 里还有 3 条 live 目标挂在这些已软删的车间上**（`_seed_发酵车间` `2026-09`=8.0 / `2026-10`=5.0、`_seed_提取车间` `2026-10`=8.0）—— 孤儿目标行是现在唯一还会进对账/列表的种子残留，清理属数据删除，等负责人批准 |
| D-20 | 导入行级异常只回调用方，不落任何日志表 | 事后无法追溯某行为什么没进来 | `bitable_cross_import.py:499-501`、`bitable_daily_import.py:192-194` | 待修 |
| D-21 | `/energy/workshops` 与 `/energy/settings` 菜单无入口 | 车间与设置只能直连 URL，主数据无法在 UI 维护 | `lib/menu-config.ts:61-72` | 待修 |
| D-22 | 饼图切片可达 58 片 | 可读性差、标签重叠 | `components/energy/DistributionChart.tsx` | 待修（Top-N + 其他）。**2026-10-18 负责人定：不并入本 PR**，排后续 PR 且先于 `DeviceDrawer` 迁移。做之前要先定三个口径——N 取几（当前汽最少 1 片、电最多 58 片）、「其他」切片的 tooltip 要不要列出被合并的车间名、切片数不足 N 时是否完全不合并。分母仍是该能源类型当期合计，故「其他」= 100% − Top-N，占比不会变 |
| D-23 | 三个抽屉用 `useEffect` + `setState` 取数填表 | 违反 React Hooks 规范与 React Compiler 前提 | `DeviceDrawer.tsx:109-128`、`AlertConfigDrawer.tsx:82-112` | **部分已修（3 个迁完 1 个）**。`WorkshopDrawer` 已是声明式：详情走 `useQuery`（`:41-49`，key `['energy-workshops','detail',id]`），`useEffect`（`:52-66`）只把查到的数据回填表单、不取数。剩两处仍在 `useEffect` 里手取：`DeviceDrawer` 的平台列表已用 `useQuery`（`:93-107`），但设备详情走 `loadDeviceData`（`:109-117`）由 `useEffect`（`:119-128`）触发；`AlertConfigDrawer:82-112` 还用 `setTimeout(…, 0)` 包一层再 `getAlertRuleById().then(form.setFieldsValue)`，失败只 `message.error`。余下部分待修（计划 PR6）。**2026-10-18 负责人定：不并入本 PR**，且两处不是一个代价——`DeviceDrawer` 是机械迁移（同文件 `:93-107` 就有 `useQuery` 模板，照 `WorkshopDrawer.tsx:41-49` 的 `enabled: open && !!id` 包住 `getEnergyDeviceById`，`useEffect` 只留 `form.setFieldsValue`，约 15 行）；`AlertConfigDrawer` **缓做**：预警规则本身 `D-01` 未接线，且父组件 `AlertRuleTable.tsx` 里一个 queryKey 都没有，真要迁得新造 `['energy-alert-rules','detail',id]` 并补写后失效，等于给没上线的功能做重构。两处迁完都只能靠 `pnpm typecheck`/`lint` + 负责人人工点击背书（浏览器实测能力仍缺，原因见 `D-48`） |
| D-24 | 孤儿代码 | 死代码误导维护 | `AlertsPageClient.tsx`、`CollectLogsPageClient.tsx`、`DevicesPageClient.tsx`、`actions/energy.ts:151 getWorkshops`、`lib/api/server/energy.ts:203 fetchWorkshops` | 待修（计划 PR4） |
| D-25 | `revalidatePath` 指向不存在的路由 `/energy/alert-rules`、`/energy/alert-records` | 写操作后页面缓存不失效 | `actions/energy.ts:117,123,129,140` | 已修（四处改成真实路由 `/energy/alerts`。注意这页数据全走浏览器侧 React Query，`revalidatePath` 对它本身是空操作，改对只是消除「指向不存在的路由」这一误导，不代表缓存失效链路已通） |
| D-26 | 采集日志详情前端路径与后端不一致，必然 404 | 排障主入口不可用 | `lib/api/client/energy.ts:44` vs `api.py:364` | **已修**（路径改为 `/collect/logs/{logId}/detail`；`apiGet` 已解 `data` 信封，`CollectLogDetail` 为生成类型。回归护栏见 `test_endpoint_paths.py`） |
| D-27 | 目标单耗上限前后端不一致（100 vs 9999.9999） | 提交大值报 422，用户不知原因 | `schemas.py:328`、`:334` vs `TargetModal.tsx:108-118` | 待修 |
| D-28 | 单耗分子把四类能源裸值相加当 kWh | 与 6.4 口径冲突，单耗与偏差值不可信 | `repository.py:959-987` | **已修**（口径负责人已确认：只算电）。`get_monthly_energy_total` 增 `energy_type` 形参（`repository.py:959-987`），`prepare_ai_analysis_data` 传 `EnergyType.ELECTRICITY`（`service.py:837-839`），prompt 措辞由「当月总能耗」改为「当月电耗」（`service.py:926`），无电耗时的 `NotFoundException` 文案同步（`service.py:842`）。护栏 `test_ai_energy_numerator.py` 9 例（含「四类裸值和 2000 / 电 1000」的对照组，证明过滤真的生效而非恰好相等；末 3 例是 `D-56` 的产量校验）。已验证变异：抽掉 `repository` 里的 `energy_type` 过滤 → **4 例转红**；只抽掉调用点的 `energy_type=` 实参 → **3 例转红**。2026-09 九个生产车间的虚高幅度实测 0 ~ **5.95%**（`202车间` 电 97,469 kWh vs 四类裸值和 103,270；`105车间` 该月只有电，所以 0%） |
| D-29 | 偏差分档取绝对值，节能 20% 也判 critical | 与 6.4 分档口径冲突 | `service.py:797-810`（`determine_deviation_status`） | **已修**（口径负责人已确认：分档只算超标）。`determine_deviation_status` 去掉 `abs()`，负偏差一律 `normal`（`service.py:797-810`）；异常偏低（漏报产量等）改由人工在分析里判读，不用分档表达（6.4 的档位表补了 `< 0` 一行）。`test_unit_consumption.py::TestDeviationStatus` 原先把 `-10 → warning`、`-20 → critical` 当成正确行为写进断言，一并反转并补 `test_negative_deviation_is_normal`。已验证变异：把 `abs()` 放回分档判定 → **2 例转红**（`test_negative_deviation_is_normal` 与 `test_ai_energy_numerator.py` 的偏差用例） |
| D-30 | `prepare_daily_stats` 对 `date_range_end IS NULL` 的记录不施加窗口下界 | 原判「AI 分析会把窗口之前的单日记录算进来」**不成立** | `service.py:599-600` | **判定有误，不修**。① 多取的那些行在输出循环里被 `start_date <= current <= end_date` 挡掉（`service.py:623`），页面数字不受影响；② 该函数与 `fetch_mock_production`/`analyze_energy_with_ai`/`analyze_energy_with_vision` 都是 v1 死代码，全仓 grep 无任何调用方（live 链路是 `ai-analysis-v2` → `prepare_ai_analysis_data`）。真实残留瑕疵只有它漏了 `is_deleted` 过滤，属死代码内，随 v1 清理一并处理，不单独立项 |
| D-31 | 两个 Bitable 自动同步开关未进种子表 | 只能在设置页外部配置，UI 看不到 | `scripts/seed/seed_module_settings.py:63-69` | 待修 |
| D-32 | 3 个既有失败用例假设设备配置表为空 | 模块测试不绿，CI 判定被稀释 | `test_repository.py:20`、`:83`、`test_service.py:55` | 已修（按 11.2 的①②：两个 repo 用例改用随机后缀的 `workshop`/`platform_code` 自造数据，service 用例 mock `get_enabled_devices_by_platform`；库里既有的 `D-19` 种子行不再影响判定，energy 套件首次全绿） |
| D-33 | `category` 从未被导入器设置，四值形同虚设 | 分类筛选无业务含义（6.7） | `bitable_cross_import.py`、映射文档缺陷 2 | 待修（依赖 D-38） |
| D-34 | `.env.local` 曾提交进 Git 历史，后被删除 | 现工作树无此文件、`.gitignore:41` 已覆盖，但历史 blob 仍可检出（`A dfcd952d` 2026-06-22 → `M 845cb8e9` 06-27 → `D 18a66339` 07-01 / `D 62037cab` 07-06）。若其中的凭证是真实值，须视为已泄露 | 历史提交里的 `.env.local`（值不在本文出现）。**注**：本文曾误记为「仓库根 `.env` 被提交」——根 `.env` 从未进 Git（`git log -- .env` 为 0，`.gitignore:2` 覆盖），已更正 | 需核实 + 审批（先确认历史 blob 是否含真实凭证，再决定轮换与历史清除）。**2026-10-18 补充：与本 PR 无关**——`git merge-base --is-ancestor dfcd952d origin/main` 为 YES，新增该文件的那次提交**早已在 `origin/main` 祖先链上公开**，`lzhc-zhuang-energy` 的 push 不新增任何暴露面；这条属仓库级历史问题，不该挂在模块 PR 上处理 |
| D-35 | `data/statistics` 的 `group_by` 非 `workshop` 时静默按车间 | 产线/设备维度统计不可用且不报错 | `repository.py:283`（`if group_by == "workshop"`）与 `:304-325`（else 分支注释「暂时按车间分组」，`group_key` 仍是 `EnergyWorkshop.name`） | 待修 |
| D-36 | 前端手写 API 类型（4 个响应模型） | 与 OpenAPI 漂移，违反契约条款 | `lib/api/client/energy.ts:110-196` | 待修（改用生成类型）。`lib/api/server/energy.ts` 的两处同类问题（`crossImportFromBitable`/`syncBitableDailyData` 手写返回类型）已随 `D-48` 修掉——正是它们把 D-48 挡在 `pnpm typecheck` 之外 |
| D-37 | AI 分析页三个写接口从浏览器直接 fetch | 绕过 CSRF/revalidation/错误边界 | `ai-analysis/page.tsx`、`TargetModal.tsx` | 待修（迁 Server Actions） |
| D-38 | `车间映射` sheet 尚未在多维表格创建 | 别名只能改代码，数据侧无法自助维护 | 飞书侧（映射文档缺陷 6） | 数据侧 |
| D-39 | 统计查询对车间 `is_deleted` 的过滤不一致 | 软删除车间的总量会混入部分口径 | `repository.py:255-256`（有）vs `306-337`、`823-861`（无） | 待修（`get_monthly_summary` 漏 `is_deleted` 已随 `D-43` 一并修；`get_overview_summary`/`get_overview_trend` 仍不看车间软删除） |
| D-40 | 配置读取优先级三处不一致（见 8.3） | 设置页改动对两个自动同步无效；违反 `os.getenv` 禁令 | `scheduler.py:144/152/230-233/241-243/321` | 需审批 |
| D-41 | `energy_daily_data` 的 `cost` / `municipal_meter` / `error_value` 无消费方 | 费用与市政总表对账能力未交付 | `models.py:354-356` | 非目标（范围外） |
| D-42 | 采集链路（`energy_data`）与填报链路（`energy_monthly_records`）无对账机制 | 两个数据源各说各话，总览只认填报值 | 6.3、第 4 章链路 5 | 待修（需业务定谁为准） |
| D-43 | 合计行与构成项同时入库，全厂电耗重复计数 | 全厂电虚高 33~35%（近 30 天重复 790,739 kWh）；饼图与汇总卡片与源表对不上 | `models.py` `ROLLUP_WORKSHOPS`、`repository.py` `_not_rollup_record`、迁移 `0069` | 已修（列 + 四处聚合口径剔除 + 导入期一致性告警，见 6.1、6.8.1） |
| D-44 | `get_monthly_summary` 按 `(energy_type, unit)` 分组，却用 `energy_type` 作结果 dict 的键 | 同一能源类型出现多种单位时后一行**静默覆盖**前一行，总量偏小且不报错 | `repository.py`（分组 `group_by(energy_type, unit)` / `summary[row.energy_type] = …`） | 待修（需与业务确认跨单位是否分别返回或强制换算，不宜静默相加） |
| D-45 | 两个前端函数指向后端从未存在的路由：`POST /energy/alerts/check`、`GET /energy/alerts/dates` | 目前**无用户可见影响** —— 只有 `actions/energy.ts:226/232` 的包装引用它们，没有任何页面调用；但一旦有人接上按钮就是必现 404，且会被误认为后端故障 | `lib/api/server/energy.ts:295,301`、`actions/energy.ts:226,232` | 待修（二选一：删掉这两个死包装，或在 `alerts` 路由补上等价端点；需业务确认是否要「按日期手动触发预警」能力） |
| D-46 | 三条导入链路的判重都忽略 `is_deleted`，且命中后的更新分支不复活软删行 | UI 删月度记录 → 改源表 → 重导入：作业回报 `updated: N, created: 0`（看着成功），行仍 `is_deleted = true`，所有页面按默认口径过滤掉 → 数据「导入了但到处看不见」。排障者会判为导入坏了 | `repository.py:806-853`（`batch_upsert_monthly_records`）、`bitable_cross_import.py:458-465`（`import_month` 的判重 select）、`bitable_daily_import.py:155`（`import_table`） | **已修**（三处命中软删行时置回 `is_deleted = false` + INFO 日志；**不能**在判重里加 `is_deleted` 过滤，因两个唯一约束不含该列（键列已用 `pg_constraint` 核过），插入分支必然撞 `UniqueViolation`。护栏 `test_soft_delete_revive.py` 5 例，抽掉三行赋值恰好 3 例转红。口径见 3.5） |
| D-47 | 手工新增月度记录无判重：软删除后再以同 `(车间, 能源类型, 日期)` 新增会撞 `uq_energy_monthly_record` | 直接打 `POST /energy/monthly`（或 `/monthly/batch`）修正数值时得到未捕获的 `IntegrityError`，即 500 而非可读错误。**当前无 UI 入口**（`createMonthlyRecord` 只存在于 `actions/energy.ts` 与 `lib/api/server/energy.ts`，无组件调用），所以不是必现故障 | `service.py:514-519`（只验车间存在，不查同名行）、`repository.py:788` `create_monthly_record` | 待修（与 7.2「修正数值的可用路径」这条说法绑定：要么新增改成 upsert/复活，要么在 UI 上明确修正只能走重导入。需业务确认走哪条） |
| D-48 | 两个导入 UI 把异步 job 句柄当同步结果渲染，且从不轮询 `GET /jobs/{job_id}` | 交叉表导入弹窗固定显示「导入成功 / 新建记录：条 / 更新记录：条」（数字空白），因为 `POST /sync/bitable/cross-import` 只回 `{job_id, status:"running"}`，`result.total_created` 等为 `undefined`；`total_errors` 也是 `undefined` → 状态恒为 success，**任务失败或行级错误在页面上完全不可见**。预警页「导入数据」的 toast 同理显示 `undefined`。配套：`revalidatePath` 在 action 返回时（≈受理后 50ms）就执行，此时后台还没写库，所以页面必然还是旧数据 | `BitableCrossImportModal.tsx:56-57,157-171`（修复前位置）、`alerts/page.tsx:211-216`（修复前位置）、`actions/energy.ts:209-213`（修复前位置）、`api.py:1042`（`/sync/bitable/cross-import`）与 `:1068`（`/sync/bitable/daily-import`） | **已修（契约层 + UI 轮询）**。契约层：`SyncJobApiResponse.data` 从 `dict[str, Any]`（OpenAPI 只发一个裸 `object`，前端因此可以随手手写返回类型、`pnpm typecheck` 也查不出来——这是 D-48 能长期存在的根因）改为具体的 `SyncJobStatus` / `SyncJobResult` / `SyncJobSection` / `SyncJobResultDetail`，`status` 收成 `Literal["running","done","failed"]`，`job_store.py` 从 `dict[str, object]` 重写为 `SyncJob` dataclass。UI 层：新增 `fetchSyncJobClient` + `hooks/useEnergySyncJob.ts`（1.5s 轮询、180s 停轮、404 → `unavailable` 而非失败），交叉表弹窗按 `running`/`done`/`failed`/`unavailable`/`timeout` 五态渲染并在 `done` 时才 `onSuccess()`；预警页 toast 同。`lib/api/server/energy.ts` 两个导入函数的**手写返回类型已换成生成类型**（`SyncJobStatus`），两个提交 action 里必然过早的 `revalidatePath` 已删——这两个 `page.tsx` 都是 `'use client'` 且数据全走浏览器侧 React Query，`revalidatePath` 对它们本就是空操作，真正生效的一直是 `invalidateQueries`。护栏 `test_sync_job_contract.py`。**未经浏览器实测**：本地只有飞书 SSO 登录，`test-login` 端点在 `APP_ENV != test/e2e` 下返回 404，无法自造会话 |
| D-49 | `import_year` 聚合月度结果时读 `created` / `updated`，而 `import_month` 返回的键是 `total_created` / `total_updated` | 「按年导入」的合计计数恒为 0（`total_created`/`total_updated`/`total_errors` 三个都是），操作员以为整年导入了 0 条。单月导入不受影响，因为只有按年链路会混用这两套命名 | `bitable_cross_import.py:581-582`（`import_year`）vs `:507-515`（`import_month` 的结果 dict） | **已修**（改读 `total_created`/`total_updated`）。护栏 `test_sync_job_contract.py::test_import_year_aggregates_month_counts`，已验证把聚合改回 `created` 后该例转红（`assert 0 == 4`）。`SyncJobResult` 刻意保留两套命名并在 docstring 里注明混用风险 |
| D-50 | `check_alerts` 写 `alert_time` 用 **naive** 的「数据日 23:59:59.999999」，列却是 `timestamp with time zone`（asyncpg 按 UTC 解释），前端再按东八区渲染 | 预警列表与处理弹窗的日期**整体晚一天**（10-13 的数据显示成 `2026/10/14 07:59:59`），排障时会去错日期找记录；按日筛选窗口同样错位（筛 10-13 查不到 `10-13 23:59:59+00` 的行） | `bitable_daily_import.py:258`（改存数据日 00:00 UTC）、`AlertRecordTable.tsx:47-52` 与 `alerts/page.tsx:52`（只显示日期）、`alerts/page.tsx:124-130`（筛选窗口按 UTC 日切） | **已修**。存量也已由负责人跑过 `scripts/migration/normalize_energy_alert_time.py`（实测 `alert_time <> date_trunc('day', alert_time)` 与「指向已软删预警的日数据行」都为 0），该脚本已用完，见第 10 章 |
| D-51 | 两个导入器的 `updated` 计数把「匹配到已有行」当成「变更行」，不管值有没有变 | 日导入永远报「新增 0 条，更新 1150 条」（1150 = 日表全部行数），而实际写库只有 106 行；交叉表导入同理。让人误判「导入没生效」或「源表全变了」 | `bitable_daily_import.py:172-185`、`repository.py:816`、`:846`（`batch_upsert_monthly_records` 的 `updated_count`） | 已修（新增 `repository.apply_changed_fields(obj, values)`：逐字段「值不同才赋值」并返回是否真有变化，四条链路（老飞书 `batch_upsert`、交叉表 `import_month`、每日 `import_table`、`bitable_sync` 的车间/月度两段）的 `updated` 改用它计数，键集与 `total_parsed` 都不动，故无契约变化。软删复活计入一次变更（`is_deleted` 进 values）。连带修一处同源错标：`feishu_import` 原把 `updated` 赋给 `records_skipped`（且用 `=` 覆盖了真正的跳行数），现在新增 `records_updated` 字段描述变更行数，`records_skipped` 回归「找不到车间而未写入」——这一处**是契约变化**，openapi 与前端类型已重生成，`FeishuImportModal` 增显「更新记录 N 条」） |
| D-52 | `bitable_daily_import._parse_timestamp` 按 **UTC** 读多维表格「时间」列，而该列按**东八区**录入（实测 5 张表的 ms 恒为 `ms % 86_400_000 == 57_600_000`，即 16:00 UTC = 东八区 00:00） | 整张 `energy_daily_data` 比表格**早一天**（表格 10-15 → 库里 10-14），预警记录的「预警日期」跟着早一天；`D-50` 修掉前端渲染偏差后这条被暴露出来（此前两个错误互相抵消，列表看着对，实际存的是错的日期）。定时任务 `check_alerts(db, now.date())` 用东八区当天去查，永远查不到刚导入的那一行 | `bitable_daily_import.py:62-68`（改 `astimezone(CST)`）、`scheduler.py:355` | **已修（代码 + 存量，但存量不是靠脚本修的）**。日期正确的现在状态是 10-16 一次全量重导入原地自愈的结果，`shift_energy_daily_date_to_cst.py` **未执行、也不得再执行**（取证与订正见 10.2）；自愈遗留 `2025-12-31` 一天 4 行脏数据（与 `2026-01-01` 逐字节相同），删除需负责人批准。**下游的错位预警已清理**：10-15 批把次日用量记到前一天、且从不被 `check_alerts` 改写，本地已由 `scripts/migration/realign_energy_alerts_to_daily_data.py` 软删 188 条 + 重导入重建，现 live 205 条与超标日行一一对齐（实测见 10.2）。同模式的 `bitable_sync.py:170`（老飞书链路 `fromtimestamp()` 取 naive 本地时间，容器 TZ=UTC）本轮**未改**：该链路的 `monthly_table_id` 为空、实际未启用，改它要连带判断存量月度记录是否也要平移 |
| D-53 | 分页列表的 `ORDER BY` 不是全序，并列行的顺序 Postgres 不保证稳定 | 月度记录页翻到第 2 页时同一车间重复出现（一次交叉表导入写入的几十条 `record_date` 完全并列）；加了车间/日期筛选只剩一页，看起来就"正常"，所以长期没被发现。预警列表在 `alert_time` 归一到日之后是同样的形状 | `repository.py:884-888`（`list_monthly_records`）、`:658`（`list_alert_records`）、`:554`（`list_alert_rules`，同事务批量写入的 `created_at` 用 `now()` 完全相同）、`:242`（`list_energy_data`）、`:456`（`list_collect_logs`） | **已修**（五处全部补决胜位：月度用唯一键其余两列，其余用 `id`）。护栏 `test_list_pagination_order.py` 2 例，已验证抽回两处 `order_by` 后对应用例转红 |
| D-54 | AI 能耗分析的车间选择器列出全部 30 个 live 车间，辅助部门、岗位与机组都能选 | 单耗 = 车间电耗 / 折算产量，`动力运行`、`RTO`、`401岗位`、`质量控制部` 这些对不上产品产量的实体，折算产量只能手填甚至填 0，算出来的「单耗」与偏差没有任何业务含义，却能进 AI 分析并写目标值 | `ai-analysis/page.tsx:41-49`（原取 `category=workshop`）、`service.prepare_ai_analysis_data` | **已修（仅读取侧限定，主数据一行不删）**。白名单 `PRODUCTION_WORKSHOPS`（9 个生产车间名，`models.py`）；读侧 `GET /workshops?production_only=true` → `repository.list_workshops(name_in=…)`，写侧 `prepare_ai_analysis_data` 对表外车间 `BadRequestException` → 400。为什么不能删车间行：总览与统计一律过滤 `EnergyWorkshop.is_deleted == false`（`repository.py:300`、`:322`、`:698`、`:710`、`:722`），软删辅助部门会让全厂总量直接掉下来、总览对不上多维表格。为什么按名字而非 `category`：库里 30 行 live 全是 `category='workshop'`，枚举形同未用（实测见 11.4）；名字精确相等才不会让 `103车间` 命中 `103冷水机组`。护栏 `test_ai_analysis_scope.py` 7 例，已验证抽掉 repository 过滤后 3 例转红、抽掉 service 守卫后 2 例转红 |
| D-55 | 预警生成链路的两个查询都不过滤 `EnergyDailyData.is_deleted`：`check_alerts` 与 UI 端「枚举所有超标且未挂记录的日期」 | 日数据行被**软删**后（`is_deleted=true`，但 `is_alert=true`、`alert_record_id` 为空），下一次导入仍会为它生成预警——列表页看不到这行用量，预警却凭空多一条，且撤销它只能回到日数据侧改源表（页面删的是预警记录，不动日行）。目前库里 `is_deleted=true` 的日行为 **0**（2026-10-16 实测），所以还没暴露成真实故障；但 `D-52` 那轮清理软删了 188 条预警并清空反向引用，若当时存在软删日行，重建就会把它们捞回来 | `bitable_daily_import.py:233-239`（`check_alerts`）、`api.py:1086-1090`（UI 触发链路） | 待修（两处各补 `EnergyDailyData.is_deleted == False` 即可挡住新预警；改动面小。**但要先定业务口径**：软删日行是否应连带撤销已生成的预警记录——只挡新增，还是删日行时一并撤判定，需负责人确认） |
| D-56 | `prepare_ai_analysis_data` 的「折算后总产量不能为 0」抛裸 `ValueError`，不是本模块异常 | 全 0 产量的分析请求返回 **500** 而非 400/422，前端拿不到可读信息（页面只能显示通用失败）。触发面是 `D-57` 那个默认值：旧版新增行预填 `0`，负责人只要不删掉它就必然打中这条 | `service.py:873-874` | **已修**（改抛 `BadRequestException("折算后总产量必须大于 0，请填写每个产品的产量")` → 400，复用 `D-54` 已在该文件导入的异常类；`quantity` 键缺省走 `item.get("quantity", 0)`，同样落在这条 400 上）。护栏 `test_ai_energy_numerator.py::TestZeroProductionIsBadRequest` 3 例（service 层 2 例断类型与 `status_code == 400`，HTTP 层 1 例断 `POST /ai-analysis-v2` 真返回 400 且 `chat_json` 未被调用），已验证把该行改回裸 `ValueError` 后 **3 例全转红**（HTTP 那条的红是裸异常一路从 endpoint 冲到测试客户端，正是线上那个 500 的形状）。前端逐行校验（`D-57`）仍保留，是常规路径的第一道闸 |
| D-57 | AI 分析页新增产量行预填 `0`，且产量列不显示单位 | 负责人手测反馈：每次都要先删掉 0 才能输数；`kg` 只写在字段说明里，表格列上看不出单位 | `ai-analysis/page.tsx`（原 `handleAddItem` 预填 `quantity: 0`，`InputNumber` 的 `onChange` 又把「清空」当 0 写回） | **已修**（`ProductionItem.quantity` 改可选、新增行不再带 `quantity`、`onChange` 用 `v ?? undefined` 不再把清空当 0；列名改「产量（kg）」并给 `InputNumber` 加 `addonAfter="kg"`（antd 6.6.4 支持，见 `node_modules/antd/es/input-number/index.d.ts:56`），列宽 100→150）。同时把提交前的逐行校验补全（产品名非空、产量 > 0），这是 `D-56` 的前端防线 |

## 13. 变更记录

按 commit 追加，一行一个工作包。

| 日期 | commit | 内容 | 影响章节 |
|---|---|---|---|
| 2026-10-12 | `748ef6e0` | 修 AI 智能建议必现失败：`construct_ai_prompt` 读 `item['name']` 而生产者给 `product_name`，带产品的分析 100% 抛 `KeyError`；改用全局单例 `llm_client.chat_json` + `expected_keys`，异常收窄到 `LLMError` 并 `logger.exception`；`calculate_unit_consumption` 接受浮点产量，修掉 `int()` 截断导致 <1 归零的 500 | 5.7、R7 |
| 2026-10-13 | `506ed3fd` | 容忍畸形 LLM 输出：网关返回常是 `{建议,具体措施,预期效果}` 对象数组、偶发缺 `confidence_level`；改为只要求至少一段结论文本，其余字段按类型收敛 | 5.7、R7 |
| 2026-10-13 | `fe2b0fa4` | 解开网关 `json_object` 信封：约半数响应被包成 `{"type":"json_object","content":{…}}`，只读顶层字段会把完整结论误判为「AI 不可用」 | 5.7、R7 |
| 2026-10-13 | `825aeb4f` | AI 分析页三处 UI：`&gt;` 被当字符串字面量渲染、产品表格缺稳定 rowKey、antd v6 弃用 `Alert.message` | 5.7 |
| 2026-10-13 | `56f89ce8` | 测试先断言 `chat_json` 已被调用再取 `await_args`（mypy strict 下类型为 `_Call \| None`） | 11.1 |
| 2026-10-15 | `4d936c37` | 三个页面冷加载不取数：把 `useEffect`+`setState` 迁到声明式 `useQuery`，queryKey 用固化 `today` 与格式化日期字符串 | 5.1、5.2、5.3 |
| 2026-10-15 | `d976e3b0` | 合并多维表格里的同义车间名：`WORKSHOP_ALIASES` + `车间映射` 覆盖 + 合并脚本 + 9 条单测 | 4.2、6.8、10.1 |
| 2026-10-15 | `100ff179` | 区域分布饼图按电/水/汽/气分开画：后端回传 `energy_type`，前端卡片内 Segmented | 5.1、6.2 |
| 2026-10-15 | `ea51d979` | RTO 电耗与气耗归到同一车间实体：去掉 `RTO用电` 跳过（每月约 16,834 kWh 曾被整行丢弃）+ 补 `303车间` 别名。**⚠ 方向有误，见下方 `b34d7f25`** | 6.8、R3 |
| 2026-10-15 | `386c23c8` | 补两份文档：月度交叉表字段映射、车间统一变更说明 | 0、4.2、10.1 |
| 2026-10-16 | `b34d7f25` | **更正 `ea51d979` 的方向 + 落地合计行剔除**。`ea51d979` 把 `RTO用电` 与 `RTO(天然气）` 合成一个实体，只解决了「电耗被整行丢弃」，却让 `RTO` 的电与容器 `环保中心(含RTO)` 的电同时计入全厂，重复计数由此重新引入；同理 `动力运行` 本来就是 6 台机组用电之和，一直与机组并计。正确做法是保留单一实体 + 按 `(车间, 能源类型)` 剔除：`energy_workshops.excluded_energy_types varchar[]` + 迁移 `0069`（建列并给 `动力运行`/`RTO` 打 `electricity` 标）；`ROLLUP_WORKSHOPS` 常量作为三种新建车间路径的唯一打标源；`repository.py` 新增 `_not_rollup_record()`，四处全厂口径接入（`get_overview_summary`、`get_energy_statistics`、`get_overview_trend`、`get_monthly_summary`），单车间口径不动；顺带修 `get_monthly_summary` 漏 `is_deleted`；交叉表导入新增 `_check_rollup_consistency`（容差 1%，只告警不改数，随 job 结果返回 `rollup_warnings`）；前端车间抽屉多选 + 列表「合计行」徽标，类型重生成；新增 `test_rollup_exclusion.py` 15 例 | 3.2、5.3、6.1、6.2、6.8.1、10.1、11.1、11.3、11.4、R3、D-39/D-43/D-44 |
| 2026-10-16 | `e86e2f7c` | 修掉两处必然 404 的前端端点路径（`D-17` 飞书导入少 `/monthly` 段、`D-26` 采集日志详情写成 `/energy/collect-logs/{id}`）。只改路径——请求体与响应都是生成类型，`apiGet` 已解 `data` 信封。后端路由由 `@monthly_router.post(...)` + `include_router(prefix="/monthly")` 装配，全文搜路径搜不到，这是当初写错没被发现的原因。同时把 `alerts/check` 与 `alerts/dates` 两个死包装登记为 `D-45`。配套 `test_endpoint_paths.py` 4 例（正确路径可用 + 错误路径确实 404，飞书按 AGENTS.md 必须 mock）；`FeishuImportModal` 的真实载荷即 mock 的入参，顺带锁住请求体契约 | 4、5.2、5.6、7、7.7、R9、R10、11.1、D-17/D-26/D-45 |
| 2026-10-16 | `bdcd21e2` | **修 `D-46`：导入命中软删行必须复活**。起因是排期上的一个真实陷阱——「UI 删掉某月记录 → 改源表 → 重导入」这条修正路径会让作业回报 `updated: N, created: 0`，看起来成功，但行仍 `is_deleted = true`，所有页面按默认口径过滤掉，于是被误判成「导入功能坏了」。三处判重（`batch_upsert_monthly_records` / `import_month` / `import_table`）都不看 `is_deleted`，更新分支也从不置回。**修法只能是复活**：`uq_energy_monthly_record` 与 `uq_energy_daily_data_date_type_category` 都不含 `is_deleted`（已用 `pg_constraint` 对本地库核过键列），在判重里加 `is_deleted = false` 过滤会把同一行让给插入分支，直接撞 `UniqueViolation`；只有带 `is_deleted` 的 `uq_energy_device_config_platform_device` 那种表才容得下过滤式判重。每处复活打 INFO 日志便于排障；新增 3.5 口径条、R1 增一条「count 为 0 但 updated>0」的分叉、7.2/6.6 的修正路径改写；顺带登记 `D-47`（手工新增无判重，软删后重新 POST 撞唯一约束；该端点无 UI 入口）。`test_soft_delete_revive.py` 5 例，已验证抽掉三行赋值恰好 3 例转红，`repository.py` 的 `logger` 为该文件首次引入 | 3.5、6.6、7.2、R1、11.1、11.3、D-46/D-47 |
| 2026-10-16 | `bdcd21e2` | **模块负责人手测「UI 删记录 → 重导入」，`D-46` 修复现场生效，同时查出 `D-48`**。日志侧证据：`POST /sync/bitable/cross-import` 在 **52ms** 内返回 200，11s 后才从飞书取到 83 条、解析 117 条，`bitable_cross_import` 打出 **6 条 `Reviving soft-deleted monthly record`**；库里 `updated_at` 落在该秒的月度记录正好 6 行且全部 `is_deleted = false`，全表软删行数从 9 降到 3（剩下的是 `D-19` 的 `_seed_发酵车间` 假种子，源表无同名车间所以不会被复活）。负责人所述「101车间 2023-10」经核**库内 2023 年记录数为 0**，实际删除并导入的都是 `2026-10`（101车间 电/蒸汽/自来水 三行）。「过一会儿才看到数据」不是缓存：交叉表导入是异步任务，`revalidatePath` 在受理后立刻执行、那时后台还没写库，页面必然还是旧数据。该误导登记为 `D-48`（弹窗把 job 句柄当同步结果渲染 → 计数空白、状态恒为 success、错误不可见；预警页 toast 同）。**并更正本文 5.2/5.5 的两处错误说法**：我曾写「导入后轮询 `GET /jobs/{job_id}`」，实际前端全文只有生成类型里有这个路径，`lib/`、`actions/`、组件均无调用点 —— 轮询从未实现 | 3.5、5.2、5.5、R1、R8、D-46/D-48 |
| 2026-10-16 | `bdcd21e2` | **`D-48` 契约层 + `D-49`（修复方案 Step 1–2）**。`SyncJobApiResponse.data` 原为 `dict[str, Any]`，OpenAPI 只能发一个裸 `object`，于是前端可以在 `lib/api/server/energy.ts` 里手写返回类型而 `pnpm typecheck` 查不出偏差——这既是违反契约条款的入口，也是 D-48 的根因。新增 `SyncJobStatus`（`status` 为 `Literal["running","done","failed"]`）/ `SyncJobResult` / `SyncJobSection` / `SyncJobResultDetail` 四层模型，字段是两个 bitable 导入器与 `bitable_sync` 三条链路的**并集**，`extra="ignore"` 允许契约外的键被丢弃；`job_store.py` 由 `dict[str, object]` 重写为 `SyncJob` dataclass（`Literal` 状态、`created_at` 默认工厂），5 个 `/sync*` 提交端点统一返回 `SyncJobApiResponse(data=SyncJobStatus(...))`、只回受理句柄不含计数，`GET /jobs/{job_id}` 用 `SyncJobResult.model_validate` 把 store 里的原始 dict 卡进契约。顺带修 `D-49`：`import_year` 读 `result.get("created")` 而 `import_month` 给的是 `total_created`，按年导入合计恒为 0。`test_sync_job_contract.py` 11 例（含递归 `$ref` 解析器断言 `data` 确实指向 `SyncJobStatus`，防止退回裸 dict；`spawn_task` patch 成关闭协程，不打飞书）；openapi.json 重导出、生成类型 +113 行，`pnpm typecheck` 通过——但**这次改动它本来就该报错**：`lib/api/server/energy.ts:269,276`（修复前位置） 手写的返回类型把差异挡住了（`D-36` 的现场），那两处在 Step 3 换成生成类型。`D-48` 的 UI 轮询（Step 3/4）未做 | 7.7、R1、R8、11.1、D-48/D-49 |
| 2026-10-16 | `bdcd21e2` | **`D-48` UI 轮询落地（修复方案 Step 3–4）**。新增 `lib/api/client/energy.ts::fetchSyncJobClient` 与 `hooks/useEnergySyncJob.ts`：1.5s 轮询 `GET /jobs/{job_id}`，`status != running` 或 404 或超 180s 即停轮，派生出 `running`/`done`/`failed`/`timeout`/`unavailable` 五态。`unavailable` 单独成态是刻意的——任务状态在**进程内**（`D-11`），重启或换实例会 404，把 404 当「失败」会谎报（数据很可能已写入）。`BitableCrossImportModal` 删掉手写的 `ImportResult` 局部类型，改渲染契约类型：进行中显示 `Result status="info"` 并禁用「完成」，`done` 才渲染计数并首次调用 `onSuccess()`（用 `useRef` 记住已通知的 `job_id`，防止父组件每次渲染换新 `onSuccess` 身份导致反复失效缓存），`failed` 显示后端 `error`，错误明细最多 10 条——这是本文 5.2 早就写过、此前并不存在的能力。预警页 `handleSyncData` 同改造，toast 只在 `done` 后出现，不再念 `undefined`。`lib/api/server/energy.ts` 两个导入函数的手写返回类型换成生成的 `SyncJobStatus`（`D-36` 现场之一，正是它把 D-48 挡在 `pnpm typecheck` 之外），`crossImportFromBitable` 入参一并换成生成的 `BitableCrossImportRequest`；两个提交 action 的 `revalidatePath` 删除（两个页面都是 `'use client'`，本来就不经过服务端渲染缓存）。`pnpm typecheck`/`pnpm lint` 均通过。**浏览器未实测**：本地登录只有飞书 SSO，`/identity/auth/test-login` 在 `APP_ENV != test/e2e` 下 404，无法自造会话，只做 `curl` 确认两个路由 307 未编译失败、dev 日志无报错；实测步骤交模块负责人。5 个态里只有 `done`/`failed` 有真实数据可验，`unavailable`/`timeout` 需人为制造 | 5.2、5.5、7.7、R8、11.3、D-36/D-48 |
| 2026-10-16 | `bdcd21e2` | **预警记录新增删除功能（负责人新提需求）**。后端 `repository.delete_alert_record` / `service.delete_alert_record` / `DELETE /api/v1/energy/alerts/records/{record_id}`（`EnergyDeleteResponse`，未找到与已删均 `NotFoundException` → 404）。**当时的口径是软删除后不清 `energy_daily_data.alert_record_id`**（下一行把它推翻）：`check_alerts` 的判重条件是 `alert_record_id IS NULL`（`bitable_daily_import.py:237`），与 `is_deleted` 正交；清掉反向引用会让下一次日导入把刚删的预警原样再生成一遍，留着则该行永远不再进入生成集合——删的是展示记录，不是重新计算的入口。相应地 3.5 补了这条口径，5.5 写明按钮位置与确认文案。前端 `AlertRecordTable` 操作列加「删除」（宽 120→140，所有状态都可删），alerts 页面用 `modal.confirm` 二次确认 + 成功后 `fetchRecords()`；`lib/api/server/energy.ts::deleteAlertRecord` 与 `actions/energy.ts:146`（`revalidatePath('/energy/alerts')`，路径正确，不像 `D-25` 那几处）。`test_alert_record_delete.py` 5 例：软删后列表查不到、`energy_daily_data` 行与 `is_alert` 标记都不动、**`check_alerts` 不会再生成同一条**（真正的护栏）、未知 id 与重复删均 404。已验证该护栏非空洞：把 `alert_record_id=None` 的 `update` 注入 `delete_alert_record` 后 5 例中 4 例转红。openapi.json 重导出（864→865 路径）+ `pnpm generate:api`；`pnpm typecheck`/`lint` 通过、energy 套件 108 passed / 3 failed（3 例即 `D-32`）。**「预警管理的数据」按预警记录实现**，每日能耗数据仍无列表页与删除入口 | 3.5、5.5、7.4、11.1、11.3、D-25 |
| 2026-10-16 | `bdcd21e2` | **预警记录的删除口径反转（负责人手测后改判）+ 修 `D-50`**。负责人按上一轮实现手测：删掉 10-13（电 65366/65000、水 818/800）与 10-14（水 820/800）三条预警后点「导入数据」，toast 回「新增 0 条，更新 1150 条，无新增预警」，记录没生回来 —— 这正是上一轮「保留 `alert_record_id`」的预期结果。但负责人指出**多维表格的日数据每天会被修正**，源表改对之后重新导入必须按新用量重新判定，永久屏蔽是错的。于是 `repository.delete_alert_record` 改为**同时清掉 `energy_daily_data.alert_record_id`**（`sa.update`，不动 `total_value`/`is_alert`），语义变成「删除 = 撤回这条判定，下次导入重新评」；测试反转：`test_alert_record_delete.py` 5 → 6 例，新增「源表改到线下后不再生成」（证明放开判重 ≠ 无条件生成），变异验证抽掉清引用那一行两例转红；前端删除确认文案跟着改。同时修 `D-50`：`check_alerts` 的 `alert_time` 从 naive 23:59:59.999999 改成**数据日 00:00 UTC**，`AlertRecordTable` 列名「预警时间」→「预警日期」并只显示日期（取 UTC 日部分，旧数据也立刻显示正确）、处理弹窗同步，按日筛选窗口改成 UTC 日切（此前筛 10-13 会漏掉 `10-13 23:59:59+00` 的行）—— **这条日期错位正是负责人误判「删了 10-14/10-15」的原因**。历史数据未动：`scripts/migration/normalize_energy_alert_time.py`（默认 dry-run）负责归一 `alert_time` 并清掉指向已软删预警的 `alert_record_id`，本地那次执行被权限策略拦下、**尚未运行**，需负责人自行执行。新登记 `D-51`（`updated` 把「匹配到已有行」当「变更行」，日导入永远报「更新 1150 条」而实际写库 106 行），本轮未修。energy 套件 109 passed / 3 failed（`D-32`），`ruff`/`mypy`/`pnpm typecheck`/`lint` 干净；本轮无契约变化，未重生成 openapi 与前端类型。**UI 仍未浏览器实测**（原因同 `D-48`） | 3.5、5.5、6.5、7.4、9、11.1、11.3、D-50/D-51 |
| 2026-10-16 | `bdcd21e2` | **修 `D-52`（日数据日期整体比多维表格早一天）与 `D-53`（分页排序非全序，翻页重复显示同一车间）**。负责人手测提出两条：① 预警记录的日期与多维表格不一致，要求「直接复制内容的日期，不要转换时区」；② 月度记录不筛选时同一车间在第 1、2 页各出现一次，加了车间/日期筛选就正常。第二条一眼定位到 `list_monthly_records` 只按 `record_date DESC` 排——一次交叉表写入的几十条 `record_date` 完全并列，Postgres 不保证并列行顺序。第一条先按 `D-50` 的结论否认过一次，但只读探针（`scripts/test/probe_energy_bitable_timezone.py`）实测 5 张日表的「时间」单元格 **`ms % 86_400_000` 恒为 `57_600_000`**（16:00 UTC = 东八区 00:00，即按东八区录入），而 `_parse_timestamp` 按 UTC 取日 → 整张 `energy_daily_data` 比表格早一天（库里 `max(date)=2026-10-14`，表格到 10-15）。`D-50` 修掉前端 +08 渲染后这条被暴露出来：此前 naive 23:59:59 与 +08 渲染两个错误互相抵消，列表显示的日期恰好等于表格日期，**存的却是错的**。修法：`_parse_timestamp` 改 `astimezone(CST)`（`bitable_daily_import.py:62-68`）；`alert_time` 仍存数据日 00:00 UTC、前端仍取 UTC 日，两端合起来正好等于表格那天，前端无需改。存量交 `scripts/migration/shift_energy_daily_date_to_cst.py`（整体 +1 天，默认 dry-run，**只能跑一次**，跑错用 `--days -1` 补回，必须在下次导入前跑否则撞唯一键整体回滚）—— 本轮**未执行**（数据修正需负责人确认）。排序侧五处一起补决胜位（月度用唯一键其余两列，预警/规则/采集日志/设备读数用 `id`），`D-53` 登记为已修。新增 `test_bitable_daily_import.py`（2 例，用真实 ms）与 `test_list_pagination_order.py`（2 例，固定 UUID + 哨兵日期），变异验证：分别抽回月度、预警两处 `order_by` 后对应用例各自转红。`D-50` 的存量确认已由负责人跑过 `normalize_energy_alert_time.py`（实测待归一行 0、指向已删预警的引用 0），该脚本转为「已用完」，第 10 章新增 10.2 收录两个日期脚本。同模式的 `bitable_sync.py:170` **未改**：该链路 `monthly_table_id` 为空、实际未启用，改它要连带判断存量月度记录是否也要平移。energy 套件 113 passed / 3 failed（3 例即 `D-32`），`ruff`/`mypy` 干净；本轮无契约变化，未重生成 openapi 与前端类型。**UI 仍未浏览器实测**（原因同 `D-48`），翻页与日期两条都需负责人复核 | 5.2、5.5、6.5、9（R6/R13）、10.2、11.1、11.3、D-50/D-52/D-53 |
| 2026-10-16 | `ad725422` | **吃掉 §12 里「改动面小」的四条：`D-51` + `D-25` + `D-13` + `D-32`**（交接文档 §6 的候选队列）。① `D-51`：新增 `repository.apply_changed_fields(obj, values)`——逐字段「值不同才赋值」并返回是否真有变化，四条链路（`batch_upsert_monthly_records`、交叉表 `import_month`、每日 `import_table`、`bitable_sync` 的车间/月度两段）的 `updated` 都改用它计数；重复导入同一份源表从此报「更新 0 条」而不是「更新 1150 条」。返回键集与 `total_parsed` 不动，故 `SyncJobResult` 契约不变；软删复活的 `is_deleted` 进 values，所以「同值但被 UI 删过」仍算 1 次变更，不会与 `D-46` 的复活口径打架。连带修一处**同源错标**：`feishu_import` 把 upsert 的 `updated` 赋给 `records_skipped`（还用 `=` 覆盖了前面累计的真跳行数），现新增 `records_updated` 字段专指变更行数、`records_skipped` 回归「找不到车间而未写入」——**这是本轮唯一契约变化**，openapi +1 字段、生成类型 +7 行、`FeishuImportModal` 结果页增显「更新记录 N 条」。② `D-25`：`actions/energy.ts` 四处 `revalidatePath` 改成真实路由 `/energy/alerts`；同时把「`revalidatePath` 对这页本来就是空操作」写进 5.5，避免修完字符串就误以为失效链路通了。③ `D-13`：四个车间 queryKey 统一挂 `['energy-workshops']` 前缀（列表带参数对象、月度下拉裸前缀、AI 分析 `'ai-analysis-options'`、抽屉详情 `'detail', id`），车间保存后一次前缀失效覆盖全部；不新建 keys 模块，仓库里没有共享 queryKey 常量的先例。④ `D-32`：两个 repo 用例改自造带 `uuid` 后缀的 `workshop`/`platform_code`，service 用例 mock `get_enabled_devices_by_platform`——**这里不能用随机平台码**，`trigger_collection` 先查 `ADAPTERS`，未知平台直接走 `failed` 分支；**没有删库里的 `D-19` 种子行**（清理仍待负责人批准）。energy 套件从 13 文件 116 例（113/3）变成 **14 文件 121 例全绿，本模块首次 0 失败**；新增 `test_import_change_counts.py` 5 例，变异验证：`apply_changed_fields` 返回值改成恒 `True` 后 5 例中 4 例转红。**订正 `D-52` 的存量判定**：本条先前据「预警 `alert_time::date` 与日行 `date` 0 处不一致」断定负责人已跑 `shift_energy_daily_date_to_cst.py`，该判据**无效**（`alert_time` 本就是从日行 `date` 生成的，一起错也一起对）。改用 `updated_at` 取证后结论相反：脚本**未执行**，日期正确是 10-16 08:19 一次全量重导入原地自愈的结果（`2026-01-01`/`2026-01-02` 各行 `updated_at` 都是那次，而残留的 `2025-12-31` 四行 `updated_at == created_at` 从未被再写入，四类数值与 `2026-01-01` 逐字节相同）。10.2、`D-52` 与第 9 章排障条目据此重写，新增两条口径：**脚本现在不得再跑**（会把已正确的数据推早一天并撞 `uq_energy_daily_data_date_type_category` 回滚）、**遗留一天脏数据待负责人批准删除**。**本轮未做**：`D-45`（删死包装还是补端点要业务确认）、`D-05`/`D-16`（`EnergyType` 枚举补 `natural_gas` 要跑迁移）、`D-19` 种子数据清理。**UI 仍未经浏览器实测**（原因同 `D-48`：本地只有飞书 SSO，`test-login` 在 `APP_ENV != test/e2e` 下 404）——「更新记录 N 条」新文案、翻页去重、预警日期三条都需负责人手测。静态检查：`ruff check app/modules/energy tests/modules/energy` 干净、`mypy` 7 个改动文件干净（`scripts/` 的 29 个报错全在故意不入库的 `seed_energy_data.py` 内）、`pnpm typecheck`/`lint` 通过 | 3.5、5.3、5.5、5.7、7、10.2、11.1、11.2、11.3、D-13/D-25/D-32/D-51/D-52 |
| 2026-10-16 | `ad725422` | **清理 `D-52` 的下游脏预警：新增 `scripts/migration/realign_energy_alerts_to_daily_data.py` 并由负责人执行**。负责人先问「预警导入是不是在刷新旧数据」，查库发现天然气 live 预警 25 条里 20 条是 10-15 批回填的**错位记录**——每条存的触发值都是**次日**的实际用量（链式取证：02-05 记 1763 = 02-06 实际值、02-13 记 1337 = 02-14 实际值），其中 5 条挂在本身不达标的日子上（幻影），而 10-16 自愈重导入又为每段连续超标的最后一天补出正确记录，于是 02-13/02-14 那种「相邻两天同一个数」在列表里看着像重复。根因是口径本身：`check_alerts` 只在 `alert_record_id IS NULL` 时新建、从不改写已有记录，原地自愈只修日数据，所以**改源表 + 重导入永远修不了旧预警**。全局同类规模：10-15 批 live 191 条里数值对不上当日的是 电 29/30、气 20/20、汽 72/74、水 67/67，所在日实际不达标的 电 11、气 5、汽 21、水 18。处置（负责人批准并执行）：先 `pg_dump` 两张表到 `/tmp/energy_alert_backup_20261016.sql`，再单事务软删 188 条 + 清反向引用，然后点「导入数据」重建。验收四项全绿：live **205** = 超标日行 **205**、数值不一致 **0**、幻影 **0**、同日同类型重复 **0**（分类型电 38 / 气 20 / 汽 77 / 水 70，全 pending）。脚本按仓库惯例落 `scripts/migration/`（默认 dry-run、`--apply` 写库、可重复执行，UAT/生产同样需要跑一次），执行权在负责人——本轮 agent 只读校验与写脚本，写库命令按 §7 约定交负责人执行。文档同步：10.2 增一行、第 9 章 R6 新增「预警触发值与当日用量对不上」排障条目、11.4 补预警基线、`D-52` 状态补下游清理。**另答清两条口径**：重导入会刷新日数据但修不了旧预警（要改只能删了重生成，且删已处理过的预警会丢处理痕迹）；天然气近期零预警是**正确行为**（日用气 56~601 全在警戒线 1000 下），不是漏报。**遗留**：`2025-12-31` 那 4 行自愈残留仍未删（SQL 已给负责人）；天然气警戒线 1000 明显低于 2 月常态用气，重生成后那段照样天天 critical，属源表配置问题不是代码问题 | 9（R6）、10.2、11.4、D-52 |
| 2026-10-16 | `ad725422` | **`D-54`：AI 能耗智能分析限定 9 个生产车间（负责人本轮口径：「仅删除 AI 分析模块！」）**。负责人要求辅助部门与设备不得再出现在 AI 分析板块，但**明确不删主数据**——`repository.py` 的 5 处全厂/总览聚合都过滤 `EnergyWorkshop.is_deleted == false`（`:300`、`:322`、`:698`、`:710`、`:722`），软删这些行会让总览总量直接掉下来、对不上多维表格。于是限定只落在**读取侧 + 分析入口**：`models.PRODUCTION_WORKSHOPS`（9 个车间名，`101/102/103/105/201/202/301/302车间` + `303、106车间`；`303车间` 与 `QC` 早在实体统一时就软删并进规范名，不拆行）；`repository.list_workshops(name_in=…)` 只做通用名字过滤、不含业务名，白名单在 service 层解析；`service.list_workshops(production_only=…)`；`/workshops` 新增 `production_only` query 参数；`prepare_ai_analysis_data` 对表外车间 `BadRequestException` → 400（守卫在取数与 `llm_client.chat_json` 之前，不为辅助部门烧一次模型调用，也不会先撞「该月无能耗数据」的 404）。前端只改 AI 页：`fetchWorkshopsClient({ production_only: true })`、`WorkshopQueryParams` 补该字段，车间管理页与月度页一字未动。**为什么按名字而不是 `category`**：库里 30 行 live 的 `category` 全是 `workshop`，四值枚举形同未用（实测见 11.4），拿它筛选会把 21 个非生产实体一起放进来；名字精确相等也顺带解决了 `103车间` 与 `103冷水机组` 的前缀混淆。**连带修 14 例**：`test_unit_consumption.py` 的 `_patched_energy_source` 把 `get_workshop_by_id` mock 成 `装配车间A`，被新守卫提前挡下——mock 车间名必须在白名单内才走得到被测的计算路径，改成 `101车间`（prompt 构造那 3 例自带 dict 字面量，不受影响）。新增 `test_ai_analysis_scope.py` 7 例；变异验证两轮：抽掉 repository 的 `name_in` 过滤 → 3 例转红，抽掉 service 守卫 → 2 例转红。契约：openapi 重导出 +19 行（`production_only`，另把上一轮未提交的 `records_updated` 一并带出）、`pnpm generate:api` +9 行，`pnpm typecheck`/`lint` 通过；energy 套件 15 文件 **128 例全绿**，后端全量 **615 passed**，`ruff`/`format`/`mypy` 干净。两处盲区记进 11.3：登记表测试挡不住「库里新增第 10 个生产车间却漏出白名单」，前端选择器只 9 项也无自动化测试。**UI 仍未经浏览器实测**（原因同 `D-48`）——需负责人手测：AI 分析页车间下拉只有 9 项、车间管理页仍能看到全部 30 项、用旧链接或脚本打非生产车间应得到 400。本轮顺带登记一条**未修**的新缺陷 `D-55`（`check_alerts` 与 UI 触发链路都不过滤软删日行，实测当前软删日行为 0 故未暴露；修法要先定「软删日行是否连带撤销已生成预警」的业务口径） | 5.7、11.1、11.3、11.4、12（D-54/D-55） |
| 2026-10-16 | `ad725422` | **`D-28` + `D-29`（AI 分析数字的正确性）**。负责人手测 `D-54` 通过后接着问「AI 分析页导出的车间能源数据对不对」，答案是**此前不对**：分子把电/水/汽/气的裸值（kWh / m³ / t / Nm³）直接相加当 kWh 用，2026-09 九个生产车间的虚高 **0 ~ 5.95%**（`202车间` 97,469 → 103,270，`105车间` 该月只有电所以 0%）；偏差分档又取 `abs()`，节能 20% 照样判 critical。修法两处：`get_monthly_energy_total` 增 `energy_type` 形参（`repository.py:959-990`），`prepare_ai_analysis_data` 传 `EnergyType.ELECTRICITY`（`service.py:837-839`），连带把 prompt 的「当月总能耗」改成「当月电耗」（`:926`）、空数据文案改成「无电耗数据」（`:842`）；`determine_deviation_status` 去掉 `abs()`，负偏差一律 `normal`（`:797-810`），6.4 档位表补 `< 0` 一行。**核对**：用实链路 `prepare_ai_analysis_data` 逐车间跑 `2026-09`，九个 `total_energy_kwh` 与 SQL 聚合逐字节相等（数已进 11.4 基线）。**新护栏** `test_ai_energy_numerator.py` 6 例，种齐「电 1000 / 水 500 / 汽 200 / 气 300 → 裸值和 2000」并带对照组；`TestDeviationStatus` 原先把负偏差判 warning/critical 当成正确行为写进断言，一并反转 + 补 `test_negative_deviation_is_normal`（该文件 32 → 33 例）。变异验证三轮：抽掉 repository 过滤 → 4 例转红；只抽调用点实参 → 3 例；把 `abs()` 放回 → 2 例。**同时更正两处本文自己的错误判定**：`D-30` 与 `D-09` 都建立在「v1 日口径链路还活着」的假设上，实测 `prepare_daily_stats`（`service.py:590-633`）与 `fetch_mock_production`/`analyze_energy_with_ai`/`analyze_energy_with_vision` **全仓零调用方**，日均分摊根本不参与任何页面计算，所以「窗口下界失效会把窗口外的行算进来」和「两套日口径共存、页面数字不能互相对账」都不成立（`D-30` 的多取行在输出循环里被 `service.py:623` 挡掉；真实残留只是死代码漏了 `is_deleted` 过滤）。两条状态改为「判定有误，不修」，随 v1 清理一并处理。顺带把 5.7/6.4/第 9 章里因本轮改动漂移的行号引用全部核一遍改正（`service.py:826-827`/`:842`/`:865`、`schemas.py:328`、`fetch_mock_production:636`）。energy 套件 16 文件 **135 例全绿**、后端全量 **622 passed**，`ruff`/`format`/`mypy` 干净；本轮无契约变化（`energy_type` 是 repository 内部形参，不进 API），未重生成 openapi 与前端类型。**另答一条**：`energy_product_conversions` 实测 **0 行**（`D-03`），所以现在所有产品的折算系数都按 `1.0`，分母 == 手填原始 kg —— 页面单耗与「总览的电」能对上，但与产品台账的可比性取决于这张表何时补数据 | 5.7、6.4、9（R7/R12）、11.1、11.4、12（D-02/D-09/D-27/D-28/D-29/D-30） |
| 2026-10-16 | `ad725422` | **前端产量录入两处手感问题（负责人手测提出）+ 登记 `D-56`**。「手动添加产品默认产量是 0，每次要先删 0 再输数，且产量右侧没有单位」。改 `ai-analysis/page.tsx`：`ProductionItem.quantity` 改可选、`handleAddItem` 不再预填 `quantity`（`:69`，新行输入框为空并显示 placeholder「产量」）、`onChange` 用 `v ?? undefined` 不再把「清空」当 0、列名改「产量（kg）」并给 `InputNumber` 挂 `addonAfter="kg"`（`:217-231`，`addonAfter` 已核实在 antd 6.6.4 的 `input-number/index.d.ts:56`），列宽 100 → 150。同时补提交前的逐行校验（产品名非空、产量 > 0，`:114-126`）——因为后端拿 0 产量会抛裸 `ValueError`（`service.py:874`）→ 走 `main.py:395` 的兜底 handler → **500「服务内部错误」**，这条登记为 `D-56`（后端应改 `BadRequestException`；绕过前端直打接口仍能触发）——**同轮已修，见下一条**。`pnpm typecheck`/`lint` 通过，无契约变化。**UI 仍未经浏览器实测**（原因同 `D-48`），需负责人复核：点「添加产品」新行产量应为空、单位在输入框右侧可见、留空或填 0 点分析应被 toast 拦住且不发请求 | 5.7、12（D-56/D-57）、13 |
| 2026-10-16 | `ad725422` | **`D-56` 后端补刀：0 产量不再 500**。上一条登记的那条裸 `ValueError` 一并修掉：`prepare_ai_analysis_data` 的产量校验改抛 `BadRequestException("折算后总产量必须大于 0，请填写每个产品的产量")`（`service.py:873-874`），走 `main.py:295` 的 `AppException` handler → **400**，不再落 `main.py:395` 的兜底 500。选 `BadRequestException` 而不是 `ValidationException`：同文件 `D-54` 的白名单守卫已经在用它，两者都是 400，不必为一条文案引入第二种异常类型。`quantity` 键整个缺省也走 `item.get("quantity", 0)` → 同一条 400（旧版是 0.0 参与求和后撞裸 `ValueError`）。护栏 `test_ai_energy_numerator.py::TestZeroProductionIsBadRequest` **3 例**（service 层 2 例断异常类型 + `status_code`，HTTP 层 1 例用 `auth_client` 真打 `POST /ai-analysis-v2` 断 400、文案含「产量」、`chat_json` 未被调用），落在该文件里是为了复用上面已有的种子助手（`_workshop`/`_record`/`_record_only_electric`），不再另开文件重复 30 行 fixture。变异验证：把那行改回裸 `ValueError` → **3 例全转红**（HTTP 那条是裸异常直接从 endpoint 冲到测试客户端，就是线上 500 的形状）。前端逐行校验（`D-57`）保留不动，仍是常规路径的第一道闸。本轮**无契约变化**（只是 500 → 400，请求/响应体不变），未重生成 openapi 与前端类型。energy 套件 16 文件 **138 例全绿**，后端全量 **625 passed**（41.6s），`ruff`/`format`（36 files already formatted）/`mypy`（18 files）干净。**UI 仍未经浏览器实测**（原因同 `D-48`） | 5.7、11.1、12（D-56）、13 |
| 2026-10-17 | `261ca5a8` | **手测收口 + 基线复核（纯文档，无代码改动）**。负责人回报「已测试完成」，交接文档 §3 的 9 条 UI 条目全部点完、未报新问题，于是 5.7 验收 ⑩ 从「需负责人手测」改成「已手测通过」，11.3 补一句：**手测只补上「人工点击」那一层，自动化盲区一条没少**。随后用只读探针把 11.4 的基线在 `ad725422` 之后重新量了一遍，三处结论变了：① 月度 live 由 **33,339 → 33,336**（分类型电 16,487 / 汽 5,945 / 水 10,331 / 气 573），差额是 `102车间` `record_date=2026-09-30`、`date_range_end=2026-10-08` 的电 11,650 kWh / 汽 6 t / 水 228 m³ 三行于 10-16 **17:22（本地）** 被软删 —— **操作主体未经确认**（agent 本轮只读，时间落在手测窗口内），若是误删，重跑交叉表导入会按 `D-46` 的复活分支捞回来；② 由此 2026-09 `102车间` 的电由 31,228 变成 **19,578**，另外八个车间的分子逐字节复现不变，所以分子的核对基线仍然可用，但必须写明它是删除后的值；③ 新记一条此前 11.4 漏掉的表：`energy_unit_consumption_targets` live **5** 条，真业务行只有 `101车间` 的 `2026-07`=5.5 与 `2026-09`=6.5，其余 3 条挂在 `D-19` 的 `_seed_*` 假车间上，**而 `_seed_发酵车间`/`_seed_提取车间` 本身已软删 —— 这 3 条 live 目标成了孤儿行**（`D-19` 的残留现在只剩这一处）。复核同时确认：预警 live 205 = 超标日行 205、不一致/幻影/重复/未达标/已处理 **全 0**，日数据 1160 行 + `2025-12-31` 那 4 行残留仍在（**仍等批准删除**）、软删日行仍 **0**（`D-55` 至今没被真实数据暴露过）、`energy_product_conversions` 仍 **0** 行、live 车间仍 **30** 条。`D-10` 借这次机会补上活样本并修正位置引用（`repository.py:935-953` → `:959-987`）。之后按负责人「重点观察并更新 PRD 最新进度」的口径做了一次**全文引用校准**：用脚本把全文 145 个不同的 `file:line` 引用逐条对到当前代码（`bdcd21e2`/`ad725422` 之后行号整体下移），改掉 30 余处失效引用，涉及 §12 的 21 个 D 条目（连同前面 `D-10` 共 22 条）和 3.4、3.5、5.5、6.1、6.3、6.4、10、11.2 的正文；其中 `D-35` 的位置从 `repository.py:260-262` 挪到真正的 else 分支（`:283`、`:304-325`），`D-03`/`D-07`/`D-14`/`D-41` 四条模型引用分别从 `:350`/`:158-163`/`:246-253`/`:317-319` 对到 `:387`/`:195-200`/`:283-288`/`:354-356`。同时纠正两处**内容**过期：5.5 车间页的缓存 key 还写着 `D-13` 修之前的 `['workshop', id]`（实为 `['energy-workshops','detail',id]`，`WorkshopDrawer.tsx:42`），`D-23` 的「三个抽屉都用 `useEffect` 取数」现在只剩 2 个未迁（`WorkshopDrawer` 已改 `useQuery`）。另用 `--collect-only` 复核 11.1 的 **16 文件 / 138 例**与逐文件计数全部相符，`pytest tests/modules/energy` **138 passed**。交接文档按负责人口径「已完成的任务就没有修改价值」不再逐条维护，本文此后是唯一进度载体 | 0、3.4、3.5、5.5、5.7、6.1、6.3、6.4、9、10、11.1、11.2、11.3、11.4、12（D-01/03/07/10/11/12/13/14/17/20/23/28/29/32/35/41/46/47/51/53/54/55）、13 |
| 2026-10-18 | `8e7fd506` | **PR 前 code review 核查收尾：外部审查 9 条结论逐条定案 + 一次脚本清理**。审查方以本地陈旧的 `main`（`003ede72`，10-08）为基线算出 208 文件，而 `origin/main` 早已合并 #88（quality 模块 + `app/core/job_models.py`/`job_repository.py` + 迁移 0067/0068）、#110、#114，**本 PR 真实范围只有 52 文件 / 21 提交且全部是 energy**（`git diff --name-only origin/main...HEAD`）。据此它 4 条「硬性违规」里 3 条不成立：`response_model=dict` 那条点名的 `reagent_reminder_api.py`/`instrument_api.py`/`static_data/api.py` 命中为 **0**，真有 13 处的是 `reagent_api.py`/`ipqc_api.py`/`sampling_api.py`/`stability_api.py`/`iqc_api.py`，且**全部在 `origin/main` 既有**；f-string 日志不是规范禁令（AGENTS.md 只要求「带上下文」，safety 11 处、equipment 6 处属通行写法，且审查方把 2 处数成 5 处）；`service.py:474` 的 `from app.modules.energy.models import PRODUCTION_WORKSHOPS` 是**同模块内部** import，禁令针对「import 其他模块」。SQL 那条只算技术性成立：被插值的 `{table}`/`{column}`/`{on_clause}` 全是本文件模块级常量，运行时值（车间 id/名称/编码）一律走 `:src`/`:tgt`/`:name`/`:old` 绑定，但 `backend/pyproject.toml:71` 的 ruff `select = ["E","F","I","N","W","UP"]` **未启用 S 规则集**，4 处 `# noqa: S608` 是死抑制，本轮删掉。「scope creep：本 PR 新增后台任务基础设施」同样不成立——`app/core/jobs.py` 是 `15c7ddc5` 起就在 main 的既有文件，能源的导入任务状态在**进程内存**（`energy/job_store.py:20-47`，`self._jobs` 字典，重启即丢），DB 那套任务表只服务 quality/static_data。审查方没查而我核出的一条：**CI 的 typecheck 口径是 `scripts/ci/ci.sh:204` 的 `mypy app tests`，`scripts/` 根本不在其中**，所以本 PR 新增脚本里的 **7 处 strict 报错一直没人挡**（对照基线：main 上既有的 `scripts/migration/backfill_all.py` 同跑法 10 处报错，属仓库通行状态、不是本 PR 的回归）。已补 `merge_energy_workshop_aliases.py` 四个函数的 `db: AsyncSession` 与返回注解（`fetchall()` 结果显式转列表以匹配声明的 `list[Any]`），`realign_energy_alerts_to_daily_data.py:113` 的 `rowcount` 用 `# type: ignore[attr-defined]`（与 `safety/repository.py` 里 20+ 处同款，负责人否掉了 `cast`），五个新增脚本现 strict 全绿。spec 侧两条判定为**准确但不属本 PR 承诺**：`D-22`（饼图 Top-N + 其他，§13 `100ff179` 那条只承诺按电/水/汽/气分画）、`D-23`（剩 `DeviceDrawer.tsx:109-128` 混用、`AlertConfigDrawer.tsx:82-112` 仍是 `setTimeout` + `.then`），负责人决定两项都留后续 PR，顺序 D-22 → DeviceDrawer（照 `WorkshopDrawer.tsx:41-49` 的 `enabled` 模板，约 15 行）→ AlertConfigDrawer（等 `D-01` 接线后再做；`AlertRuleTable.tsx` 一个 queryKey 都没有，迁移要连带新造 key 并接写后失效，给未上线功能做重构不值）。`D-21`/`D-24` 同为已登记待修。**另更正 `D-34` 与本次 PR 的关系**：`git merge-base --is-ancestor dfcd952d origin/main` = YES，那个 `.env.local` blob **早就在 origin/main 上公开**，本 PR 的 push 不新增暴露面，属仓库级历史问题。凭证扫描重跑一遍 52 文件全量 diff：`app_token` 命中均为变量名、政策原文、测试虚拟值 `app_token="test-token"`（8 处 fixture）与一条「断言假 token 不出现在 AI 摘要里」的脱敏护栏，无真实凭证、无飞书链接、无 table_id 取值。验证：energy 套件 **138 passed**、`ruff check app/modules/energy scripts tests/modules/energy` 干净、`mypy app/modules/energy tests/modules/energy` 36 文件 0 issues、5 个新增脚本 0 issues；迁移编号无重复、`0069` 单模块只 `add_column`。**前端两个手测症状（总览饼图需刷新才显示、月度记录切走再切回不显示）仍未在浏览器里结案**：代码侧已确认 `EnergyOverview.tsx:43-58` 与 `MonthlyRecordTable.tsx:100-135` 都是**无 `enabled` 门控的声明式 `useQuery`**（`4d936c37` 的结果，冷加载不取数这条成因已不存在），且本地 `energy_daily_data` 最新只到 `2026-10-16`、当天 0 行，所以默认「今日」全 0 与空态属正常、而月度 live 有 33,336 条（最新 `2026-10-09`）不能用「没数据」解释；月度侧只剩一条假设待验——`Providers.tsx:11-19` 的 `staleTime: 5min` 是否会把错误态缓存住。补注解后的脚本 dry-run 需负责人自行执行（agent 侧执行迁移脚本被权限策略拦下，未换路径绕过） | 11.3、12（D-22/D-23/D-34）、13 |
| 2026-10-16 | 本文更正 | **`D-34` 原判定有误**：本文曾记为「仓库根 `.env` 提交了真实 `app_token`」，实际根 `.env` 从未进 Git（`git log -- .env` 为 0 个提交，`.gitignore:2` 覆盖）。真实的历史暴露面是 `.env.local`：`A dfcd952d` → `M 845cb8e9` → `D 18a66339`/`D 62037cab`，工作树已无、`.gitignore:41` 已覆盖，但历史 blob 仍可检出。是否含真实凭证**未经核实**，故状态从「需审批」降为「需核实 + 审批」 | 8.4、D-34、13 待办 |
| 2026-10-16 | 本文 v1.0 | 首版模块 PRD：8 项业务口径经能源模块负责人确认（单耗只算电、预警以警戒线为准、产量本期手填、通知非目标、偏差只算超标、权限只写现状、`category` 写为目标口径、0 视为未填报） | 全文 |

**待办**（不属于文档缺陷，属工程排期；2026-10-16 复核后更新，负责人为唯一执行方，agent 不代跑写库操作）

1. **`2025-12-31` 的 4 行日数据残留**仍未删（`D-52` 自愈时唯一没被覆盖的那天，四类数值与 `2026-01-01` 逐字节相同、`is_alert=false`、无关联预警，但仍被总览/趋势当一天计入）。软删 SQL 已交负责人，**等批准执行**；删除后 11.4 的日基线应变成 1156 行 / 289 天。
2. **`102车间` 三条跨月月度行**（`record_date=2026-09-30`、`date_range_end=2026-10-08`，电 11,650 kWh / 汽 6 t / 水 228 m³）于 10-16 17:22 被软删，**操作主体待负责人确认**。若是误删，重跑交叉表导入即可按 `D-46` 的复活分支捞回；若是有意删，得同时接受 `09-30 ~ 10-08` 这段用量在两个月里都不计（`D-10`）。
3. **`D-55` 的业务口径**：软删日行是否应连带撤销已生成的预警。定下来之前不动代码（目前库里软删日行仍为 0，所以没暴露过）。
4. **UAT / 生产**：车间实体统一、`realign_energy_alerts_to_daily_data.py`（预警错位清理）都要在 UAT/生产各跑一次；本地已由负责人执行。
5. **`D-19` 假种子数据清理**待批 —— 4 个 `_seed_*` 车间与其月度行都已软删，**只剩 3 条 live 单耗目标还挂在已软删的 `_seed_发酵车间`/`_seed_提取车间` 上**（孤儿行，见 11.4）。
6. **`D-34`** 需先核实历史 `.env.local` blob 是否含真实凭证，再定责轮换/清除。

