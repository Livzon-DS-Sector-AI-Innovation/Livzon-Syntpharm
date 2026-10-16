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
- **跨天记录的读口径不唯一**：第 6 章 6.1 的汇总/分布/趋势按 `record_date` 单点归期，跨天记录整体算进起始日；第 6 章 6.4 单耗链路走 `service.prepare_daily_stats`（`service.py:582-627`），把 `value / days` **平均分摊到区间内每一天**。两套口径共存，页面数字不能互相对账。列为 `D-09`。
- `get_monthly_energy_total`（`repository.py:935-953`）用 `record_date >= start AND record_date < end` 且**完全不看 `date_range_end`**：跨月范围的记录会被漏计或错月。列为 `D-10`。

### 3.5 软删除口径

- 删除业务数据一律置 `is_deleted = true`，不做物理删除。
- 「未删除」是所有统计与列表的默认前提，但必须**逐条查询显式声明**：`get_energy_statistics` 同时过滤记录与车间的 `is_deleted`（`repository.py:255-256`），`get_overview_summary`/`get_overview_trend` 只过滤记录未过滤车间，`get_monthly_summary`/`get_monthly_energy_total` 只过滤记录。
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
| 路由与入口 | `/energy/alerts`，标题「预警管理」，两个 Tab「预警记录 / 预警规则」（`alerts/page.tsx:283,351`） |
| 依赖接口 | 读 `GET /alerts/records`、`GET /alerts/rules`（client 分页版）；写 `processAlertRecord`（`PUT /alerts/records/{id}/process`）、`deleteAlertRecord`（`DELETE /alerts/records/{id}`，**新增**）、`deleteAlertRule`、`createAlertRule`（Server Action）；导入按钮 `syncBitableDailyDataAction`（`POST /sync/bitable/daily-import`，同为异步任务）。**已接轮询**：提交只存 `job_id`，`useEnergySyncJob` 轮到 `done` 才弹「新增 N 条，更新 M 条，自动生成 K 条预警记录」并 `refetchRecords()`；`failed`/`unavailable`/`timeout` 各有独立文案（`D-48` 已修）。此前它把 job 句柄当同步结果，toast 必然写成「新增 undefined 条」 |
| 取数与缓存 key | 规则 `['alert-rules', {rulesPage, rulesPageSize}]`（`:101`）；记录 `['alert-records', {recordsPage, recordsPageSize, filterDate, filterEnergyType}]`（`:121`），`filterDate` 转成**该数据日的 UTC 日窗口**（`00:00`–`23:59:59.999`）进 params（`:124-129`），与 `alert_time` 的存储口径一致（`D-50`）；分页默认 10 |
| 交互与口径 | 记录 Tab：导入数据、DatePicker、能源类型筛选、刷新；处理弹窗字段 `status`（默认 processed，必填）+ `process_note`；操作列两个按钮 —— pending 才有「处理」，任何状态都有「删除」（danger link，`modal.confirm` 二次确认，`AlertRecordTable.tsx:108-124`）。**删除口径 = 软删除 + 清反向引用**：置 `energy_alert_records.is_deleted = true`，同时把 `energy_daily_data.alert_record_id` 置回 `NULL`，但不动日数据行本身（`total_value`/`is_alert` 原样）。于是「删除 → 重导入」按新的用量重新判定：**仍超线就再生成一条，源表改到线下就不再生成**。改这条口径的理由是多维表格日数据每天被修正，永久屏蔽会让修正后的超标再也报不出来；代价是删掉的误报下次导入会回来 —— 不想它回来只能改源表或把状态处理掉。「预警日期」列只显示日期（`YYYY-MM-DD`，取 `alert_time` 的 UTC 日），因为预警按天判定、时刻无业务含义（`D-50`）；这个日期**必须等于多维表格「时间」列显示的那一天** —— 表格单元格按东八区录入，解析时必须换算到东八区再取日，按 UTC 取会整体早一天（`D-52` 已修）。规则 Tab 抽屉字段：规则名、能源类型、监控指标（instant/daily_total/monthly_total）、阈值类型（greater_than/less_than/equal）、阈值（min 0 必填）、单位（必填）、级别（info/warning/critical/emergency）、通知方式多选、通知用户、通知频率、生效时段（`AlertConfigDrawer.tsx:195-244`）。⚠️ **规则不参与判定**：判定只认日表警戒线（第 6 章 6.5） |
| 边界与空态 | 无记录时提示「暂无预警记录…请点击导入数据」（`AlertRecordTable.tsx:127-137`）；导入 toast 含新增/更新/预警数，且只在轮询到 `done` 后才出现（`alerts/page.tsx:257-258`） |
| 验收用例 | ① 点「导入数据」→ 当天 `total_value > 警戒线` 的行生成记录且等级按 1.1/1.2 倍分档；② 把某条 pending 记录处理为已处理 → 状态、处理人、处理时间、备注都落库；③ 同一天的同一 `(date, energy_type, category)` 重复导入 → 不重复生成预警（靠 `alert_record_id IS NULL` 守卫）；④ 新建规则 → 列表出现，但**不会产生任何预警或通知**；⑤ 删除一条预警记录 → 列表不再出现、库里 `is_deleted = true`、日数据行的 `total_value`/`is_alert` 纹丝不动但 `alert_record_id` 被清空；⑥ 删完立刻再点「导入数据」，源表仍超线 → **重新生成一条新预警记录**（不是复用被删那条）；把源表改到线下再重导 → 不再生成（⑤⑥ 由 `test_alert_record_delete.py` 全链路覆盖）；⑦ 对已删除的 id 再删一次 → 404，不是 200；⑧ 列表与处理弹窗的「预警日期」等于多维表格「时间」列显示的那一天，不出现 07:59:59 这种跨日时刻（`D-50`、`D-52`）；⑨ 同一天多条预警时翻页不重复（`D-53`） |
| 已知缺陷 | `D-01` 规则未接线；`D-14` 通知字段无消费方；`D-15` 记录无车间维度、`unit=""`；`actions/energy.ts:117,123,129,140` 的 `revalidatePath('/energy/alert-rules')`、`'/energy/alert-records'` 指向**不存在的路由**（真实为 `/energy/alerts`），缓存失效落空（`D-25`）；新增的 `deleteAlertRecord` 用的是正确路径 `/energy/alerts`（`:146`），但这页数据全走浏览器侧 React Query，`revalidatePath` 本身对它就是空操作；`AlertConfigDrawer.tsx:82-112` `useEffect`+`setTimeout` 取数（`D-23`）；能源类型选项缺 natural_gas（`AlertConfigDrawer.tsx:15-19`）；`AlertsPageClient.tsx` 孤儿（`D-24`） |

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
| 依赖接口 | 读 `GET /workshops`、`GET /targets/{workshop_id}/{target_month}`、`GET /production/output`（**后端不存在**；真实产量台账在 production 模块的 `GET /api/v1/production/product-output`，下期跨模块对接需走该模块 `public_api.py`）；写 `POST /ai-analysis-v2`、`POST /targets`、`PUT /targets/{target_id}`。**这三个写接口全部从浏览器直接 fetch**（`lib/api/client/energy.ts:119-151`），违反 AGENTS.md「写操作必须走 Server Actions」 |
| 取数与缓存 key | 车间 `['workshops']`（`:42`）；目标 `['target', workshopId, analysisMonth]`（`:53`，两个参数都非空才 `enabled`）；设定目标成功后失效同 key 并复算（`:128-135`）。其余是 `useState` 本地态 |
| 交互与口径 | 车间 Select + MonthPicker（`YYYY-MM`）；**产品产量列表手填**：表格内 `product_name` 文本 + `quantity` 数字（min 0）逐行编辑，单位固定 `kg` 不可改（`:68,197,206`），可增删行；「从生产模块同步」按钮调 `fetchProductionOutput`（路径不存在，`D-02`）。校验：月份匹配 `/^\d{4}-\d{2}$/`（`:102`）、产品明细非空（`:107`），车间+月份+产量三项齐才允许点分析（`:228`）。目标弹窗 `TargetModal`：目标月份继承所选月份，目标单耗 `InputNumber` min 0.0001 / max 9999.9999 / precision 4 / step 0.1，后缀 `kWh/kg`（`TargetModal.tsx:108-118`），`handleOk` 校验 workshopId、数值、>0（`:46`）；已有目标走 update，否则 create（`:55-67`）。⚠️ 后端 schema 的上限是 `le=100`（`schemas.py:322`），前端允许到 9999.9999 → 超限提交会被后端 422 拒（`D-27`） |
| 边界与空态 | 未设目标 → 显示「未设定」+「➕设定目标」（`:253-261`），`deviation_status='unknown'` → 文案「未知（未设定目标）」（`:306`）；该车间当月无能耗记录 → 后端抛 `NotFoundException('能耗数据', ...)`（`service.py:816-817`），页面显示错误；LLM 输出畸形/不可用 → 降级为固定文案，不整链失败 |
| 验收用例 | ① 选车间+月份且该月有电耗 → 自动查出目标并显示单耗与偏差；② 填两条产品产量点分析 → 返回 `actual_unit_consumption`（4 位小数）、`target_unit_consumption`（无目标显示 `—`）、`deviation_rate`（带正负与颜色）、`ai_suggestion.summary/detailed_analysis/recommendations[]/confidence_level`；③ 设定目标成功后卡片立即复算且偏差状态改变；④ 断言折算系数缺失的产品按 `factor=1.0` 参与分母（`service.py:840`）；⑤ 把 `energy_product_conversions` 里某产品系数配成 2 → 折算产量翻倍、单耗减半 |
| 已知缺陷 | 第 6 章 6.4 的三项口径偏差：分子含非电能源（`D-28`）、偏差取绝对值（`D-29`）、日均分摊窗口下界失效（`D-30`）；写接口绕过 Server Action（`D-37`）；`AIAnalysisResult`/`AISuggestion`/`UnitConsumptionTarget`/`ProductionOutputItem` 全是手写 API 类型（`lib/api/client/energy.ts:110-196`，`D-36`）；车间缓存 key 与列表页不同源（`D-13`）；`TargetModal.tsx:38-43` 在 render 期 setState |

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

**与现状实现的差异**（不改口径，代码待修）：分子未按能源类型过滤（`D-28`，`repository.py:935-953`）；分档对绝对值判定，节省 20% 也判 critical（`D-29`，`service.py:782-793`）；日均分摊窗口的下界条件对 `date_range_end IS NULL` 的记录不生效（`D-30`，`service.py:585`）。

### 6.5 预警判定（G3）

**口径（已确认：以日表「警戒线」为唯一判定基准）**

- 触发条件：`total_value > alert_threshold`，落库时同步置 `energy_daily_data.is_alert`。
- 等级分档（`bitable_daily_import.py:241-245`）：
  | 倍数 | 等级 |
  |---|---|
  | > 警戒线 × 1.2 | `critical` |
  | > 警戒线 × 1.1 | `warning` |
  | 仅 > 警戒线 | `info` |
- 幂等守卫：只为 `is_alert = true` **且 `alert_record_id IS NULL`** 的日数据生成记录，生成后回填 `alert_record_id`，因此同日重复导入不产生重复预警。这个反向引用同时是「这条预警已被确认过」的标记：删除预警记录会把它清空，于是下一次导入按新用量重新判定（`D-50` 那一版曾刻意保留，已改）。
- `energy_alert_rules` 的 `monitor_metric` / `threshold_type` / `threshold_value` / 生效时段 / 通知配置**全部不参与判定**（`D-01`）；本期不做通知送达（`D-14`）。
- 阈值来源：数值由飞书日表逐行给定，**不在本模块配置**。谁维护、按什么规则调线，属源表侧流程，本文不定义。
- **日期口径**：`energy_daily_data.date` 必须等于多维表格「时间」列显示的那一天。飞书日期单元格是 ms 时间戳，实测 5 张表恒为 `ms % 86_400_000 == 57_600_000`（16:00 UTC = 东八区 00:00），即按**东八区**录入 —— `_parse_timestamp` 必须 `astimezone(CST)` 再取日（`bitable_daily_import.py:61-67`）。按 UTC 取日会让整张日数据表早一天，连带 `check_alerts` 生成的预警日期、以及定时任务 `check_alerts(db, now.date())` 要查的那一天一起错开（`D-52`）。交叉表导入不受影响：它的日期来自**列头文本**（`bitable_cross_import.py:168`），不经过时间戳。

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

本地执行环境要点（会踩的坑）：后端跑在容器 `erp-backend`（工作目录 `/app`），宿主机没有 `python`/`uv`，一切 Python 命令走容器；`backend/app` 与 `backend/scripts` 是**只读 bind mount**（改宿主机文件容器内立即可见，但 `docker cp` 进去会被拒）；`backend/tests` **不是**挂载，跑单个测试文件要先 `docker cp` 进容器；改了 `app/` 代码后常驻进程需要 `docker restart erp-backend`。查库用 `docker exec -i erp-postgres psql -U postgres -d dazah`（库名是 `dazah`，不是 `livzon`；`-i` 必须带，否则 heredoc 的 SQL 不会送进去，命令静默无输出）。写脚本用 `from app.core.database import async_session_factory`，`docker cp` 到 `/tmp/` 后 `docker exec -w /app -e PYTHONPATH=/app erp-backend uv run python /tmp/xxx.py`。

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
- **预警日期与表格差一天**：日数据的日期必须等于表格「时间」列显示的那一天（6.5 日期口径，`D-52`）。校验 `SELECT max(date) FROM energy.energy_daily_data WHERE is_deleted = false;` 与表格里最后一天对比，少一天就是存量未修 → 跑 `scripts/migration/shift_energy_daily_date_to_cst.py`（见 10.2，**只能执行一次**）。

### R13 列表翻页时同一行重复出现

- 先定位：分页 `ORDER BY` 必须是全序（`D-53`）。并列行多时才会显现，所以**加了筛选就"好了"**——只剩一页而已。
- 校验：不筛选连翻两页，看同一主键是否出现两次；或 `SELECT record_date, count(*) FROM energy.energy_monthly_records WHERE is_deleted = false GROUP BY 1 ORDER BY 2 DESC LIMIT 5;` 单日几十条并列即触发条件。
- 修复：给该查询补决胜位（唯一键其余列或 `id`），不要改前端；五处已修，新增分页查询时照抄。

### R7 AI 分析必现失败

- 先定位三层：① 该车间该月有无电耗记录（`service.py:816` 会抛「能耗数据」未找到）；② LLM 调用是否成功（网关信封、畸形输出）；③ 前后端字段契约（`product_name` 键名，`748ef6e0` 的根因）。
- 校验：`SELECT count(*), sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND energy_type = 'electricity' AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false;`；后端日志找 `LLMOutputError` / `LLMProviderError`；跑 `uv run pytest tests/modules/energy/test_unit_consumption.py -q`（11 个降级路径用例）。
- 修复：按日志判因 —— 网关信封问题看 `fe2b0fa4` 的解包逻辑；结论缺失看 `506ed3fd` 的容忍分支；不要通过放宽 `expected_keys` 来"修"业务字段缺失。

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

- 先定位：单耗分子含四类能源裸值相加（`D-28`）+ 分母用折算产量，而总览按类型分开显示，两者**本就不可互推**（6.1 vs 6.4）。422 一般是目标单耗超过后端 `le=100`（`D-27`）。
- 校验：`SELECT energy_type, sum(value) FROM energy.energy_monthly_records WHERE workshop_id = :wid AND record_date >= :month_start AND record_date < :month_end AND is_deleted = false GROUP BY 1;` 手算电单耗对比页面值。
- 修复：修 `D-28` 后两者可对齐；`TargetModal` 的 max 应降到 100 与后端一致。

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
| `scripts/migration/shift_energy_daily_date_to_cst.py` | `D-52`：把 `energy_daily_data.date` 与 `energy_alert_records.alert_time` 整体 +1 天，补回按东八区解析的那一天 | ⚠ **待负责人执行**。默认 dry-run，`--apply` 才写库；**只能执行一次**（整表平移没有可复用判据），跑错方向用 `--days -1 --apply` 补回；必须在下一次「导入数据」**之前**跑，否则平移会撞 `uq_energy_daily_data_date_type_category` 并整体回滚（失败是安全的，不会留半套数据） |

### 10.3 禁用脚本

`backend/scripts/seed/seed_energy_data.py`（当前未跟踪，**故意不入库**）会 `commit` 写入 4 个车间 + 5 条设备配置 + `random` 生成的 7 天小时级假数（`:72-126`）。它污染本地库并直接导致 `D-32` 三个用例失败。**任何环境都不要执行**。

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

`backend/tests/modules/energy/` 共 13 个文件 116 例（113 passed / 3 failed，3 例即 `D-32`）：

| 文件 | 例数 | 覆盖面 |
|---|---|---|
| `test_bitable_daily_import.py` | 2 | `D-52` 日期口径：用表格里真实抓到的 ms（`1791907200000`，16:00 UTC = 东八区 00:00）断言 `_parse_timestamp` 与 `_parse_record` 得到的是**表格显示的那一天**，不是 UTC 那一天 |
| `test_list_pagination_order.py` | 2 | `D-53` 分页全序：`record_date` 完全并列的月度行、`alert_time` 完全并列的预警行，必须按补出的决胜位排序。固定 UUID + 哨兵日期让期望顺序与插入顺序错开且与存量数据隔离。已验证：分别抽回两处 `order_by` 后对应用例转红 |

| `test_alert_record_delete.py` | 6 | 预警记录软删除端点：200 + `is_deleted` 置位 + 从 `list_alert_records` 消失、未知 id 与重复删除都 404、删预警不动能耗数据行（`total_value`/`is_alert` 原样）但**清空 `alert_record_id`**、**仍超线时 `check_alerts` 会生成一条新记录**（并断言其 `alert_time` 是数据日 00:00 UTC，即 `D-50` 的护栏）、源表改到线下后不再生成。已验证：抽掉清反向引用那一行，`..._clears_back_reference` 与 `..._regenerated_while_still_over_threshold` 两例转红 |
| `test_sync_job_contract.py` | 11 | `D-48` 契约层 + `D-49`：OpenAPI 里 `SyncJobApiResponse.data` 必须解析到 `SyncJobStatus`（防止退回裸 `dict[str, Any]`，这是 D-48 能存在的根因）、5 个提交端点只回受理句柄不含计数、job 状态 running/done/failed 三态、契约外的键被丢弃、未知 job 404、按年导入的月度计数聚合。`spawn_task` 被 patch 成关闭协程，不真打飞书 |
| `test_soft_delete_revive.py` | 5 | `D-46` 回归护栏：三条导入链路（老飞书 `batch_upsert_monthly_records`、交叉表 `import_month`、每日 `import_table`）命中软删行后必须复活且被 `list_monthly_records` 读到；含「无同名行时仍走插入分支」对照组，和「复活不重复生成预警记录」的 `alert_record_id` 判重。飞书客户端 monkeypatch。已验证：抽掉三处 `is_deleted = False` 后恰好 3 例转红 |
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

无用例：预警规则 CRUD、预警记录的**处理**（`PUT .../process`）与列表筛选参数（含 `D-50` 修掉的按日筛选窗口，只测了生成侧）；月度记录判重中「同名行存在且未删除」的正常更新分支与 `date_range_end` 写入（软删复活分支已由 `D-46` 覆盖）、采集日志列表与详情（±30 秒窗口逻辑）、单耗目标持久化、`bitable_sync.py` 主流程、`bitable_daily_import.py` 的 Decimal 与可选字段转换（时间戳那一半已由 `test_bitable_daily_import.py` 补上）——只有 `import_table` 的判重与复活分支被测。`bitable_cross_import.py` 的交叉表解析只在别名/合计行用例里间接触达，`import_month` 只测车间打标、合计行校验和软删复活。`adapters/platform_a.py` 的重试与分页无用例。`get_overview_summary`/`get_energy_statistics`/`get_overview_trend` 与 `get_monthly_summary` **只有合计行剔除这一条被测**（`test_rollup_exclusion.py`），其余过滤组合仍无用例；车间 CRUD 只测 `excluded_energy_types` 的读写往返。`repository.py` 的 45 个顶层函数里只有 16 个被用例按名触达（`get_enabled_devices_by_platform` 多为 patch 替身，不算真实覆盖）。三方平台适配器**未被 mock**，测试里若真实调用会打外部网络。前端侧：`useEnergySyncJob` 的五态轮询没有任何自动化测试——本模块只有 Playwright e2e（`frontend/e2e/`），而它需要 `APP_ENV=test/e2e` + `E2E_AUTH_SECRET` 才拿得到会话，本地开发环境起不来，所以 `D-48` 的 UI 修复目前只有契约测试 + `typecheck`/`lint` + 人工点击背书。`D-53` 的五处排序修复里只有月度与预警两处有断言，`list_energy_data`/`list_collect_logs`/`list_alert_rules` 三处补的决胜位无用例（这三张表的并列条件目前还没在真实数据里出现，属预防性一致）。

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
| D-01 | 预警规则表从不参与判定，判定只认日表警戒线 | 用户以为配了规则就生效；6 个枚举字段与抽屉全表单形同虚设 | `energy_alert_rules` / `bitable_daily_import.py:228` | 待修（接线方案需业务确认，见 6.5） |
| D-02 | 前端请求 `GET /energy/production/output`（后端不存在），产量靠手填，另有随机 mock 产量函数；真实产量台账已在 production 模块 `/api/v1/production/product-output` | AI 分析页「从生产模块同步」必 404；单耗分母不可信 | `lib/api/client/energy.ts:202`、`service.py:621` | 下期（跨模块经 production `public_api.py` 取数） |
| D-03 | 折算系数表无任何写入入口 | 系数缺失时静默按 1.0，跨产品车间单耗可比性存疑 | `models.py:350`、无 API/页面 | 待修（需 CRUD + 页面） |
| D-04 | `import_year` 年度合计恒为 0 | 按年导入返回统计误导（数据本身正常入库） | `bitable_cross_import.py`（读 `created`/`updated`，实际键 `total_created`/`total_updated`） | 待修 |
| D-05 | `EnergyType` 枚举缺 `natural_gas` | 任何取枚举的代码无法表达气 | `models.py:32-35` | 待修 |
| D-06 | 天然气靠子串识别且**永久改写** `current_energy_type` | 源表把气行插到汽 section 中间，其后所有汽行会被记成天然气 | `bitable_cross_import.py`（映射文档缺陷 5） | 数据侧（需源表加独立标题行）+ 待修 |
| D-07 | `uq_energy_monthly_record` 不含 `date_range_end` | 同日期范围的两条表计互相覆盖 | `models.py:158-163` | 需审批（改约束要迁移） |
| D-08 | `uq_energy_workshop_code` 不含 `is_deleted`；`name` 与 `code` 共用一个查询命名空间 | 软删除行占着编码，重建同名车间撞唯一约束 | `models.py:62`、`bitable_cross_import.py` `_get_or_create_workshop` | 待修（需迁移，合并脚本已用 `#merged#` 让出） |
| D-09 | 两套日口径共存：汇总按 `record_date` 单点归期，单耗链路按日均分 | 页面数字不能互相对账 | `repository.py:281-282/303-304/354-355/390-391` vs `service.py:582-627` | 待修（6.1 已定口径：按单点归期） |
| D-10 | `get_monthly_energy_total` 不看 `date_range_end` 且用 `record_date < end` | 跨月范围记录漏计/错月 | `repository.py:935-953` | 待修 |
| D-11 | 异步任务状态是进程内 dict：重启丢、无进度、无 TTL、多副本不可见 | 导入任务"卡住"无法取证；内存无上限增长 | `job_store.py:7-28`、`app/core/tasks.py:20-48` | 需审批（应迁 `app/core/jobs.py`） |
| D-12 | 采集日志与采集值无外键，靠 ±30 秒窗口反推 | 补采（多小时批量 upsert）会漏或串数据 | `repository.py:411-452` | 待修 |
| D-13 | 车间缓存 key 三处不同源：`['workshops']` / `['energy-workshops']` / `['workshop', id]` | 改完车间另一页读到旧数据 | `ai-analysis/page.tsx:42`、`WorkshopTable.tsx:94`、`WorkshopDrawer.tsx:33` | 待修 |
| D-14 | 通知四字段无任何消费方 | 「配置了通知」是假象 | `models.py:246-253` | 非目标（已确认） |
| D-15 | 预警记录无车间维度、`unit=""`、`rule_id=None` | 预警只能按能源类型看，定位不到车间；页面单位空白 | `bitable_daily_import.py:248-258` | 待修 |
| D-16 | 设备与预警的能源类型下拉缺天然气 | 气类配置无法录入 | `DeviceDrawer.tsx:322-328`、`AlertConfigDrawer.tsx:15-19` | 待修 |
| D-17 | 飞书导入按钮请求路径少一段，固定 404 | 月度页「飞书导入」不可用 | `lib/api/server/energy.ts:270` vs `api.py:949` | **已修**（路径改为 `/monthly/import/feishu`；请求体与响应本就是生成类型，无需改。回归护栏见 `test_endpoint_paths.py`） |
| D-18 | 重试策略三处不统一：平台 A 指数退避、飞书月度 `sleep(60)`×3、每日同步无重试 | 与 AGENTS.md 重试约定不符；失败行为不可预期 | `adapters/platform_a.py:126`、`scheduler.py:259-296/323-362` | 待修 |
| D-19 | 假种子脚本污染本地库 | 直接导致 D-32；本地对账数字失真 | `scripts/seed/seed_energy_data.py` | 需用户决定（不入库；本地是否清理待批） |
| D-20 | 导入行级异常只回调用方，不落任何日志表 | 事后无法追溯某行为什么没进来 | `bitable_cross_import.py:460,471`、`bitable_daily_import.py:179,186` | 待修 |
| D-21 | `/energy/workshops` 与 `/energy/settings` 菜单无入口 | 车间与设置只能直连 URL，主数据无法在 UI 维护 | `lib/menu-config.ts:61-72` | 待修 |
| D-22 | 饼图切片可达 58 片 | 可读性差、标签重叠 | `components/energy/DistributionChart.tsx` | 待修（Top-N + 其他） |
| D-23 | 三个抽屉用 `useEffect` + `setState` 取数填表 | 违反 React Hooks 规范与 React Compiler 前提 | `WorkshopDrawer.tsx:43-56`、`DeviceDrawer.tsx:119-128`、`AlertConfigDrawer.tsx:82-112` | 待修（计划 PR6） |
| D-24 | 孤儿代码 | 死代码误导维护 | `AlertsPageClient.tsx`、`CollectLogsPageClient.tsx`、`DevicesPageClient.tsx`、`actions/energy.ts:151 getWorkshops`、`lib/api/server/energy.ts:203 fetchWorkshops` | 待修（计划 PR4） |
| D-25 | `revalidatePath` 指向不存在的路由 `/energy/alert-rules`、`/energy/alert-records` | 写操作后页面缓存不失效 | `actions/energy.ts:117,123,129,140` | 待修 |
| D-26 | 采集日志详情前端路径与后端不一致，必然 404 | 排障主入口不可用 | `lib/api/client/energy.ts:44` vs `api.py:364` | **已修**（路径改为 `/collect/logs/{logId}/detail`；`apiGet` 已解 `data` 信封，`CollectLogDetail` 为生成类型。回归护栏见 `test_endpoint_paths.py`） |
| D-27 | 目标单耗上限前后端不一致（100 vs 9999.9999） | 提交大值报 422，用户不知原因 | `schemas.py:322` vs `TargetModal.tsx:108-118` | 待修 |
| D-28 | 单耗分子把四类能源裸值相加当 kWh | 与 6.4 口径冲突，单耗与偏差值不可信 | `repository.py:935-953` | 待修（口径已确认：只算电） |
| D-29 | 偏差分档取绝对值，节能 20% 也判 critical | 与 6.4 分档口径冲突 | `service.py:782-793` | 待修（口径已确认：只算超标） |
| D-30 | `prepare_daily_stats` 对 `date_range_end IS NULL` 的记录不施加窗口下界 | AI 分析会把窗口之前的单日记录算进来 | `service.py:585` | 待修 |
| D-31 | 两个 Bitable 自动同步开关未进种子表 | 只能在设置页外部配置，UI 看不到 | `scripts/seed/seed_module_settings.py:63-69` | 待修 |
| D-32 | 3 个既有失败用例假设设备配置表为空 | 模块测试不绿，CI 判定被稀释 | `test_repository.py:30,92`、`test_service.py:58` | 待修（11.2 修法） |
| D-33 | `category` 从未被导入器设置，四值形同虚设 | 分类筛选无业务含义（6.7） | `bitable_cross_import.py`、映射文档缺陷 2 | 待修（依赖 D-38） |
| D-34 | `.env.local` 曾提交进 Git 历史，后被删除 | 现工作树无此文件、`.gitignore:41` 已覆盖，但历史 blob 仍可检出（`A dfcd952d` 2026-06-22 → `M 845cb8e9` 06-27 → `D 18a66339` 07-01 / `D 62037cab` 07-06）。若其中的凭证是真实值，须视为已泄露 | 历史提交里的 `.env.local`（值不在本文出现）。**注**：本文曾误记为「仓库根 `.env` 被提交」——根 `.env` 从未进 Git（`git log -- .env` 为 0，`.gitignore:2` 覆盖），已更正 | 需核实 + 审批（先确认历史 blob 是否含真实凭证，再决定轮换与历史清除） |
| D-35 | `data/statistics` 的 `group_by` 非 `workshop` 时静默按车间 | 产线/设备维度统计不可用且不报错 | `repository.py:260-262` | 待修 |
| D-36 | 前端手写 API 类型（4 个响应模型） | 与 OpenAPI 漂移，违反契约条款 | `lib/api/client/energy.ts:110-196` | 待修（改用生成类型）。`lib/api/server/energy.ts` 的两处同类问题（`crossImportFromBitable`/`syncBitableDailyData` 手写返回类型）已随 `D-48` 修掉——正是它们把 D-48 挡在 `pnpm typecheck` 之外 |
| D-37 | AI 分析页三个写接口从浏览器直接 fetch | 绕过 CSRF/revalidation/错误边界 | `ai-analysis/page.tsx`、`TargetModal.tsx` | 待修（迁 Server Actions） |
| D-38 | `车间映射` sheet 尚未在多维表格创建 | 别名只能改代码，数据侧无法自助维护 | 飞书侧（映射文档缺陷 6） | 数据侧 |
| D-39 | 统计查询对车间 `is_deleted` 的过滤不一致 | 软删除车间的总量会混入部分口径 | `repository.py:255-256`（有）vs `306-337`、`823-861`（无） | 待修（`get_monthly_summary` 漏 `is_deleted` 已随 `D-43` 一并修；`get_overview_summary`/`get_overview_trend` 仍不看车间软删除） |
| D-40 | 配置读取优先级三处不一致（见 8.3） | 设置页改动对两个自动同步无效；违反 `os.getenv` 禁令 | `scheduler.py:144/152/230-233/241-243/321` | 需审批 |
| D-41 | `energy_daily_data` 的 `cost` / `municipal_meter` / `error_value` 无消费方 | 费用与市政总表对账能力未交付 | `models.py:317-319` | 非目标（范围外） |
| D-42 | 采集链路（`energy_data`）与填报链路（`energy_monthly_records`）无对账机制 | 两个数据源各说各话，总览只认填报值 | 6.3、第 4 章链路 5 | 待修（需业务定谁为准） |
| D-43 | 合计行与构成项同时入库，全厂电耗重复计数 | 全厂电虚高 33~35%（近 30 天重复 790,739 kWh）；饼图与汇总卡片与源表对不上 | `models.py` `ROLLUP_WORKSHOPS`、`repository.py` `_not_rollup_record`、迁移 `0069` | 已修（列 + 四处聚合口径剔除 + 导入期一致性告警，见 6.1、6.8.1） |
| D-44 | `get_monthly_summary` 按 `(energy_type, unit)` 分组，却用 `energy_type` 作结果 dict 的键 | 同一能源类型出现多种单位时后一行**静默覆盖**前一行，总量偏小且不报错 | `repository.py`（分组 `group_by(energy_type, unit)` / `summary[row.energy_type] = …`） | 待修（需与业务确认跨单位是否分别返回或强制换算，不宜静默相加） |
| D-45 | 两个前端函数指向后端从未存在的路由：`POST /energy/alerts/check`、`GET /energy/alerts/dates` | 目前**无用户可见影响** —— 只有 `actions/energy.ts:226/232` 的包装引用它们，没有任何页面调用；但一旦有人接上按钮就是必现 404，且会被误认为后端故障 | `lib/api/server/energy.ts:295,301`、`actions/energy.ts:226,232` | 待修（二选一：删掉这两个死包装，或在 `alerts` 路由补上等价端点；需业务确认是否要「按日期手动触发预警」能力） |
| D-46 | 三条导入链路的判重都忽略 `is_deleted`，且命中后的更新分支不复活软删行 | UI 删月度记录 → 改源表 → 重导入：作业回报 `updated: N, created: 0`（看着成功），行仍 `is_deleted = true`，所有页面按默认口径过滤掉 → 数据「导入了但到处看不见」。排障者会判为导入坏了 | `repository.py:787`（`batch_upsert_monthly_records`）、`bitable_cross_import.py:466`（`import_month`）、`bitable_daily_import.py:155`（`import_table`） | **已修**（三处命中软删行时置回 `is_deleted = false` + INFO 日志；**不能**在判重里加 `is_deleted` 过滤，因两个唯一约束不含该列（键列已用 `pg_constraint` 核过），插入分支必然撞 `UniqueViolation`。护栏 `test_soft_delete_revive.py` 5 例，抽掉三行赋值恰好 3 例转红。口径见 3.5） |
| D-47 | 手工新增月度记录无判重：软删除后再以同 `(车间, 能源类型, 日期)` 新增会撞 `uq_energy_monthly_record` | 直接打 `POST /energy/monthly`（或 `/monthly/batch`）修正数值时得到未捕获的 `IntegrityError`，即 500 而非可读错误。**当前无 UI 入口**（`createMonthlyRecord` 只存在于 `actions/energy.ts` 与 `lib/api/server/energy.ts`，无组件调用），所以不是必现故障 | `service.py:499-504`（只验车间存在，不查同名行）、`repository.py:748` `create_monthly_record` | 待修（与 7.2「修正数值的可用路径」这条说法绑定：要么新增改成 upsert/复活，要么在 UI 上明确修正只能走重导入。需业务确认走哪条） |
| D-48 | 两个导入 UI 把异步 job 句柄当同步结果渲染，且从不轮询 `GET /jobs/{job_id}` | 交叉表导入弹窗固定显示「导入成功 / 新建记录：条 / 更新记录：条」（数字空白），因为 `POST /sync/bitable/cross-import` 只回 `{job_id, status:"running"}`，`result.total_created` 等为 `undefined`；`total_errors` 也是 `undefined` → 状态恒为 success，**任务失败或行级错误在页面上完全不可见**。预警页「导入数据」的 toast 同理显示 `undefined`。配套：`revalidatePath` 在 action 返回时（≈受理后 50ms）就执行，此时后台还没写库，所以页面必然还是旧数据 | `BitableCrossImportModal.tsx:56-57,157-171`（修复前位置）、`alerts/page.tsx:211-216`（修复前位置）、`actions/energy.ts:209-213`（修复前位置）、`api.py:1042`（`/sync/bitable/cross-import`）与 `:1068`（`/sync/bitable/daily-import`） | **已修（契约层 + UI 轮询）**。契约层：`SyncJobApiResponse.data` 从 `dict[str, Any]`（OpenAPI 只发一个裸 `object`，前端因此可以随手手写返回类型、`pnpm typecheck` 也查不出来——这是 D-48 能长期存在的根因）改为具体的 `SyncJobStatus` / `SyncJobResult` / `SyncJobSection` / `SyncJobResultDetail`，`status` 收成 `Literal["running","done","failed"]`，`job_store.py` 从 `dict[str, object]` 重写为 `SyncJob` dataclass。UI 层：新增 `fetchSyncJobClient` + `hooks/useEnergySyncJob.ts`（1.5s 轮询、180s 停轮、404 → `unavailable` 而非失败），交叉表弹窗按 `running`/`done`/`failed`/`unavailable`/`timeout` 五态渲染并在 `done` 时才 `onSuccess()`；预警页 toast 同。`lib/api/server/energy.ts` 两个导入函数的**手写返回类型已换成生成类型**（`SyncJobStatus`），两个提交 action 里必然过早的 `revalidatePath` 已删——这两个 `page.tsx` 都是 `'use client'` 且数据全走浏览器侧 React Query，`revalidatePath` 对它们本就是空操作，真正生效的一直是 `invalidateQueries`。护栏 `test_sync_job_contract.py`。**未经浏览器实测**：本地只有飞书 SSO 登录，`test-login` 端点在 `APP_ENV != test/e2e` 下返回 404，无法自造会话 |
| D-49 | `import_year` 聚合月度结果时读 `created` / `updated`，而 `import_month` 返回的键是 `total_created` / `total_updated` | 「按年导入」的合计计数恒为 0（`total_created`/`total_updated`/`total_errors` 三个都是），操作员以为整年导入了 0 条。单月导入不受影响，因为只有按年链路会混用这两套命名 | `bitable_cross_import.py:581-582`（`import_year`）vs `:500-508`（`import_month` 的结果 dict） | **已修**（改读 `total_created`/`total_updated`）。护栏 `test_sync_job_contract.py::test_import_year_aggregates_month_counts`，已验证把聚合改回 `created` 后该例转红（`assert 0 == 4`）。`SyncJobResult` 刻意保留两套命名并在 docstring 里注明混用风险 |
| D-50 | `check_alerts` 写 `alert_time` 用 **naive** 的「数据日 23:59:59.999999」，列却是 `timestamp with time zone`（asyncpg 按 UTC 解释），前端再按东八区渲染 | 预警列表与处理弹窗的日期**整体晚一天**（10-13 的数据显示成 `2026/10/14 07:59:59`），排障时会去错日期找记录；按日筛选窗口同样错位（筛 10-13 查不到 `10-13 23:59:59+00` 的行） | `bitable_daily_import.py:258`（改存数据日 00:00 UTC）、`AlertRecordTable.tsx:47-52` 与 `alerts/page.tsx:52`（只显示日期）、`alerts/page.tsx:124-130`（筛选窗口按 UTC 日切） | **已修**。存量也已由负责人跑过 `scripts/migration/normalize_energy_alert_time.py`（实测 `alert_time <> date_trunc('day', alert_time)` 与「指向已软删预警的日数据行」都为 0），该脚本已用完，见第 10 章 |
| D-51 | 两个导入器的 `updated` 计数把「匹配到已有行」当成「变更行」，不管值有没有变 | 日导入永远报「新增 0 条，更新 1150 条」（1150 = 日表全部行数），而实际写库只有 106 行；交叉表导入同理。让人误判「导入没生效」或「源表全变了」 | `bitable_daily_import.py:179`、`repository.py:822`（`batch_upsert_monthly_records` 的 `updated_count`） | 待修（建议分开 `matched` / `changed` 两个计数，或改报「源表 N 行 / 变更 M 行」；SQLAlchemy 只在属性值真变化时才发 UPDATE，所以 `updated_at` 是可靠的变更依据） |
| D-52 | `bitable_daily_import._parse_timestamp` 按 **UTC** 读多维表格「时间」列，而该列按**东八区**录入（实测 5 张表的 ms 恒为 `ms % 86_400_000 == 57_600_000`，即 16:00 UTC = 东八区 00:00） | 整张 `energy_daily_data` 比表格**早一天**（表格 10-15 → 库里 10-14），预警记录的「预警日期」跟着早一天；`D-50` 修掉前端渲染偏差后这条被暴露出来（此前两个错误互相抵消，列表看着对，实际存的是错的日期）。定时任务 `check_alerts(db, now.date())` 用东八区当天去查，永远查不到刚导入的那一行 | `bitable_daily_import.py:61-67`（改 `astimezone(CST)`）、`scheduler.py:355` | **已修（代码）**。⚠ **存量数据未修正**：跑 `scripts/migration/shift_energy_daily_date_to_cst.py`（默认 dry-run，`--apply` 才写库，**只能执行一次**，跑错用 `--days -1 --apply` 补回），必须在下一次导入之前跑。同模式的 `bitable_sync.py:170`（老飞书链路 `fromtimestamp()` 取 naive 本地时间，容器 TZ=UTC）本轮**未改**：该链路的 `monthly_table_id` 为空、实际未启用，改它要连带判断存量月度记录是否也要平移 |
| D-53 | 分页列表的 `ORDER BY` 不是全序，并列行的顺序 Postgres 不保证稳定 | 月度记录页翻到第 2 页时同一车间重复出现（一次交叉表导入写入的几十条 `record_date` 完全并列）；加了车间/日期筛选只剩一页，看起来就"正常"，所以长期没被发现。预警列表在 `alert_time` 归一到日之后是同样的形状 | `repository.py:859-864`（`list_monthly_records`）、`:641-642`（`list_alert_records`）、`:538`（`list_alert_rules`，同事务批量写入的 `created_at` 用 `now()` 完全相同）、`:226`（`list_energy_data`）、`:440`（`list_collect_logs`） | **已修**（五处全部补决胜位：月度用唯一键其余两列，其余用 `id`）。护栏 `test_list_pagination_order.py` 2 例，已验证抽回两处 `order_by` 后对应用例转红 |

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
| 2026-10-16 | 待提交（回填 hash） | **修 `D-46`：导入命中软删行必须复活**。起因是排期上的一个真实陷阱——「UI 删掉某月记录 → 改源表 → 重导入」这条修正路径会让作业回报 `updated: N, created: 0`，看起来成功，但行仍 `is_deleted = true`，所有页面按默认口径过滤掉，于是被误判成「导入功能坏了」。三处判重（`batch_upsert_monthly_records` / `import_month` / `import_table`）都不看 `is_deleted`，更新分支也从不置回。**修法只能是复活**：`uq_energy_monthly_record` 与 `uq_energy_daily_data_date_type_category` 都不含 `is_deleted`（已用 `pg_constraint` 对本地库核过键列），在判重里加 `is_deleted = false` 过滤会把同一行让给插入分支，直接撞 `UniqueViolation`；只有带 `is_deleted` 的 `uq_energy_device_config_platform_device` 那种表才容得下过滤式判重。每处复活打 INFO 日志便于排障；新增 3.5 口径条、R1 增一条「count 为 0 但 updated>0」的分叉、7.2/6.6 的修正路径改写；顺带登记 `D-47`（手工新增无判重，软删后重新 POST 撞唯一约束；该端点无 UI 入口）。`test_soft_delete_revive.py` 5 例，已验证抽掉三行赋值恰好 3 例转红，`repository.py` 的 `logger` 为该文件首次引入 | 3.5、6.6、7.2、R1、11.1、11.3、D-46/D-47 |
| 2026-10-16 | 待提交（回填 hash） | **模块负责人手测「UI 删记录 → 重导入」，`D-46` 修复现场生效，同时查出 `D-48`**。日志侧证据：`POST /sync/bitable/cross-import` 在 **52ms** 内返回 200，11s 后才从飞书取到 83 条、解析 117 条，`bitable_cross_import` 打出 **6 条 `Reviving soft-deleted monthly record`**；库里 `updated_at` 落在该秒的月度记录正好 6 行且全部 `is_deleted = false`，全表软删行数从 9 降到 3（剩下的是 `D-19` 的 `_seed_发酵车间` 假种子，源表无同名车间所以不会被复活）。负责人所述「101车间 2023-10」经核**库内 2023 年记录数为 0**，实际删除并导入的都是 `2026-10`（101车间 电/蒸汽/自来水 三行）。「过一会儿才看到数据」不是缓存：交叉表导入是异步任务，`revalidatePath` 在受理后立刻执行、那时后台还没写库，页面必然还是旧数据。该误导登记为 `D-48`（弹窗把 job 句柄当同步结果渲染 → 计数空白、状态恒为 success、错误不可见；预警页 toast 同）。**并更正本文 5.2/5.5 的两处错误说法**：我曾写「导入后轮询 `GET /jobs/{job_id}`」，实际前端全文只有生成类型里有这个路径，`lib/`、`actions/`、组件均无调用点 —— 轮询从未实现 | 3.5、5.2、5.5、R1、R8、D-46/D-48 |
| 2026-10-16 | 待提交（回填 hash） | **`D-48` 契约层 + `D-49`（修复方案 Step 1–2）**。`SyncJobApiResponse.data` 原为 `dict[str, Any]`，OpenAPI 只能发一个裸 `object`，于是前端可以在 `lib/api/server/energy.ts` 里手写返回类型而 `pnpm typecheck` 查不出偏差——这既是违反契约条款的入口，也是 D-48 的根因。新增 `SyncJobStatus`（`status` 为 `Literal["running","done","failed"]`）/ `SyncJobResult` / `SyncJobSection` / `SyncJobResultDetail` 四层模型，字段是两个 bitable 导入器与 `bitable_sync` 三条链路的**并集**，`extra="ignore"` 允许契约外的键被丢弃；`job_store.py` 由 `dict[str, object]` 重写为 `SyncJob` dataclass（`Literal` 状态、`created_at` 默认工厂），5 个 `/sync*` 提交端点统一返回 `SyncJobApiResponse(data=SyncJobStatus(...))`、只回受理句柄不含计数，`GET /jobs/{job_id}` 用 `SyncJobResult.model_validate` 把 store 里的原始 dict 卡进契约。顺带修 `D-49`：`import_year` 读 `result.get("created")` 而 `import_month` 给的是 `total_created`，按年导入合计恒为 0。`test_sync_job_contract.py` 11 例（含递归 `$ref` 解析器断言 `data` 确实指向 `SyncJobStatus`，防止退回裸 dict；`spawn_task` patch 成关闭协程，不打飞书）；openapi.json 重导出、生成类型 +113 行，`pnpm typecheck` 通过——但**这次改动它本来就该报错**：`lib/api/server/energy.ts:269,276`（修复前位置） 手写的返回类型把差异挡住了（`D-36` 的现场），那两处在 Step 3 换成生成类型。`D-48` 的 UI 轮询（Step 3/4）未做 | 7.7、R1、R8、11.1、D-48/D-49 |
| 2026-10-16 | 待提交（回填 hash） | **`D-48` UI 轮询落地（修复方案 Step 3–4）**。新增 `lib/api/client/energy.ts::fetchSyncJobClient` 与 `hooks/useEnergySyncJob.ts`：1.5s 轮询 `GET /jobs/{job_id}`，`status != running` 或 404 或超 180s 即停轮，派生出 `running`/`done`/`failed`/`timeout`/`unavailable` 五态。`unavailable` 单独成态是刻意的——任务状态在**进程内**（`D-11`），重启或换实例会 404，把 404 当「失败」会谎报（数据很可能已写入）。`BitableCrossImportModal` 删掉手写的 `ImportResult` 局部类型，改渲染契约类型：进行中显示 `Result status="info"` 并禁用「完成」，`done` 才渲染计数并首次调用 `onSuccess()`（用 `useRef` 记住已通知的 `job_id`，防止父组件每次渲染换新 `onSuccess` 身份导致反复失效缓存），`failed` 显示后端 `error`，错误明细最多 10 条——这是本文 5.2 早就写过、此前并不存在的能力。预警页 `handleSyncData` 同改造，toast 只在 `done` 后出现，不再念 `undefined`。`lib/api/server/energy.ts` 两个导入函数的手写返回类型换成生成的 `SyncJobStatus`（`D-36` 现场之一，正是它把 D-48 挡在 `pnpm typecheck` 之外），`crossImportFromBitable` 入参一并换成生成的 `BitableCrossImportRequest`；两个提交 action 的 `revalidatePath` 删除（两个页面都是 `'use client'`，本来就不经过服务端渲染缓存）。`pnpm typecheck`/`pnpm lint` 均通过。**浏览器未实测**：本地登录只有飞书 SSO，`/identity/auth/test-login` 在 `APP_ENV != test/e2e` 下 404，无法自造会话，只做 `curl` 确认两个路由 307 未编译失败、dev 日志无报错；实测步骤交模块负责人。5 个态里只有 `done`/`failed` 有真实数据可验，`unavailable`/`timeout` 需人为制造 | 5.2、5.5、7.7、R8、11.3、D-36/D-48 |
| 2026-10-16 | 待提交（回填 hash） | **预警记录新增删除功能（负责人新提需求）**。后端 `repository.delete_alert_record` / `service.delete_alert_record` / `DELETE /api/v1/energy/alerts/records/{record_id}`（`EnergyDeleteResponse`，未找到与已删均 `NotFoundException` → 404）。**当时的口径是软删除后不清 `energy_daily_data.alert_record_id`**（下一行把它推翻）：`check_alerts` 的判重条件是 `alert_record_id IS NULL`（`bitable_daily_import.py:226`），与 `is_deleted` 正交；清掉反向引用会让下一次日导入把刚删的预警原样再生成一遍，留着则该行永远不再进入生成集合——删的是展示记录，不是重新计算的入口。相应地 3.5 补了这条口径，5.5 写明按钮位置与确认文案。前端 `AlertRecordTable` 操作列加「删除」（宽 120→140，所有状态都可删），alerts 页面用 `modal.confirm` 二次确认 + 成功后 `fetchRecords()`；`lib/api/server/energy.ts::deleteAlertRecord` 与 `actions/energy.ts:146`（`revalidatePath('/energy/alerts')`，路径正确，不像 `D-25` 那几处）。`test_alert_record_delete.py` 5 例：软删后列表查不到、`energy_daily_data` 行与 `is_alert` 标记都不动、**`check_alerts` 不会再生成同一条**（真正的护栏）、未知 id 与重复删均 404。已验证该护栏非空洞：把 `alert_record_id=None` 的 `update` 注入 `delete_alert_record` 后 5 例中 4 例转红。openapi.json 重导出（864→865 路径）+ `pnpm generate:api`；`pnpm typecheck`/`lint` 通过、energy 套件 108 passed / 3 failed（3 例即 `D-32`）。**「预警管理的数据」按预警记录实现**，每日能耗数据仍无列表页与删除入口 | 3.5、5.5、7.4、11.1、11.3、D-25 |
| 2026-10-16 | 待提交（回填 hash） | **预警记录的删除口径反转（负责人手测后改判）+ 修 `D-50`**。负责人按上一轮实现手测：删掉 10-13（电 65366/65000、水 818/800）与 10-14（水 820/800）三条预警后点「导入数据」，toast 回「新增 0 条，更新 1150 条，无新增预警」，记录没生回来 —— 这正是上一轮「保留 `alert_record_id`」的预期结果。但负责人指出**多维表格的日数据每天会被修正**，源表改对之后重新导入必须按新用量重新判定，永久屏蔽是错的。于是 `repository.delete_alert_record` 改为**同时清掉 `energy_daily_data.alert_record_id`**（`sa.update`，不动 `total_value`/`is_alert`），语义变成「删除 = 撤回这条判定，下次导入重新评」；测试反转：`test_alert_record_delete.py` 5 → 6 例，新增「源表改到线下后不再生成」（证明放开判重 ≠ 无条件生成），变异验证抽掉清引用那一行两例转红；前端删除确认文案跟着改。同时修 `D-50`：`check_alerts` 的 `alert_time` 从 naive 23:59:59.999999 改成**数据日 00:00 UTC**，`AlertRecordTable` 列名「预警时间」→「预警日期」并只显示日期（取 UTC 日部分，旧数据也立刻显示正确）、处理弹窗同步，按日筛选窗口改成 UTC 日切（此前筛 10-13 会漏掉 `10-13 23:59:59+00` 的行）—— **这条日期错位正是负责人误判「删了 10-14/10-15」的原因**。历史数据未动：`scripts/migration/normalize_energy_alert_time.py`（默认 dry-run）负责归一 `alert_time` 并清掉指向已软删预警的 `alert_record_id`，本地那次执行被权限策略拦下、**尚未运行**，需负责人自行执行。新登记 `D-51`（`updated` 把「匹配到已有行」当「变更行」，日导入永远报「更新 1150 条」而实际写库 106 行），本轮未修。energy 套件 109 passed / 3 failed（`D-32`），`ruff`/`mypy`/`pnpm typecheck`/`lint` 干净；本轮无契约变化，未重生成 openapi 与前端类型。**UI 仍未浏览器实测**（原因同 `D-48`） | 3.5、5.5、6.5、7.4、9、11.1、11.3、D-50/D-51 |
| 2026-10-16 | 待提交（回填 hash） | **修 `D-52`（日数据日期整体比多维表格早一天）与 `D-53`（分页排序非全序，翻页重复显示同一车间）**。负责人手测提出两条：① 预警记录的日期与多维表格不一致，要求「直接复制内容的日期，不要转换时区」；② 月度记录不筛选时同一车间在第 1、2 页各出现一次，加了车间/日期筛选就正常。第二条一眼定位到 `list_monthly_records` 只按 `record_date DESC` 排——一次交叉表写入的几十条 `record_date` 完全并列，Postgres 不保证并列行顺序。第一条先按 `D-50` 的结论否认过一次，但只读探针（`scripts/test/probe_energy_bitable_timezone.py`）实测 5 张日表的「时间」单元格 **`ms % 86_400_000` 恒为 `57_600_000`**（16:00 UTC = 东八区 00:00，即按东八区录入），而 `_parse_timestamp` 按 UTC 取日 → 整张 `energy_daily_data` 比表格早一天（库里 `max(date)=2026-10-14`，表格到 10-15）。`D-50` 修掉前端 +08 渲染后这条被暴露出来：此前 naive 23:59:59 与 +08 渲染两个错误互相抵消，列表显示的日期恰好等于表格日期，**存的却是错的**。修法：`_parse_timestamp` 改 `astimezone(CST)`（`bitable_daily_import.py:61-67`）；`alert_time` 仍存数据日 00:00 UTC、前端仍取 UTC 日，两端合起来正好等于表格那天，前端无需改。存量交 `scripts/migration/shift_energy_daily_date_to_cst.py`（整体 +1 天，默认 dry-run，**只能跑一次**，跑错用 `--days -1` 补回，必须在下次导入前跑否则撞唯一键整体回滚）—— 本轮**未执行**（数据修正需负责人确认）。排序侧五处一起补决胜位（月度用唯一键其余两列，预警/规则/采集日志/设备读数用 `id`），`D-53` 登记为已修。新增 `test_bitable_daily_import.py`（2 例，用真实 ms）与 `test_list_pagination_order.py`（2 例，固定 UUID + 哨兵日期），变异验证：分别抽回月度、预警两处 `order_by` 后对应用例各自转红。`D-50` 的存量确认已由负责人跑过 `normalize_energy_alert_time.py`（实测待归一行 0、指向已删预警的引用 0），该脚本转为「已用完」，第 10 章新增 10.2 收录两个日期脚本。同模式的 `bitable_sync.py:170` **未改**：该链路 `monthly_table_id` 为空、实际未启用，改它要连带判断存量月度记录是否也要平移。energy 套件 113 passed / 3 failed（3 例即 `D-32`），`ruff`/`mypy` 干净；本轮无契约变化，未重生成 openapi 与前端类型。**UI 仍未浏览器实测**（原因同 `D-48`），翻页与日期两条都需负责人复核 | 5.2、5.5、6.5、9（R6/R13）、10.2、11.1、11.3、D-50/D-52/D-53 |
| 2026-10-16 | 本文更正 | **`D-34` 原判定有误**：本文曾记为「仓库根 `.env` 提交了真实 `app_token`」，实际根 `.env` 从未进 Git（`git log -- .env` 为 0 个提交，`.gitignore:2` 覆盖）。真实的历史暴露面是 `.env.local`：`A dfcd952d` → `M 845cb8e9` → `D 18a66339`/`D 62037cab`，工作树已无、`.gitignore:41` 已覆盖，但历史 blob 仍可检出。是否含真实凭证**未经核实**，故状态从「需审批」降为「需核实 + 审批」 | 8.4、D-34、13 待办 |
| 2026-10-16 | 本文 v1.0 | 首版模块 PRD：8 项业务口径经能源模块负责人确认（单耗只算电、预警以警戒线为准、产量本期手填、通知非目标、偏差只算超标、权限只写现状、`category` 写为目标口径、0 视为未填报） | 全文 |

**待办**（不属于文档缺陷，属工程排期）：车间实体统一的 UAT/生产执行由模块负责人完成；`D-34` 需先核实历史 `.env.local` blob 是否含真实凭证，再定责轮换/清除。

