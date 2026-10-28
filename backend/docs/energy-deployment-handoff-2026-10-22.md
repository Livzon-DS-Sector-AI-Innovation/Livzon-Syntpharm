# 能源模块正式部署交接（2026-10-22）

> 读者：部署负责人
> 分支：`lzhc-zhuang-energy`
> 规格与缺陷登记：[energy-module-prd.md](./energy-module-prd.md)

## 0. 结论

代码侧已完成收口：energy 套件 147 例通过，ruff / mypy / 前端 `typecheck` / `lint` 干净，OpenAPI 契约与前端生成类型一致。

部署分两部分，**缺一不可**：

1. 发布代码并执行 Alembic 迁移；
2. 上线后执行一次车间别名合并（`merge_energy_workshop_aliases.py --apply`），再重新导入数据。

只发布代码、不跑第 2 步，存量的 `QC` / `废水站` / `303车间` 等分裂实体仍会出现在总览和月度筛选里。

## 1. 本次修复覆盖的三个现场问题

| 问题 | 根因 | 修复 | 是否需要数据步骤 |
|---|---|---|---|
| 总览中同一部门在水/电/汽下名称不一致 | 旧导入器按源表字面建车间，未做别名归一 | 三条导入链路统一走 `energy/workshop_names.py` 的别名表；总览按车间实体名分组 | **需要**：合并脚本 + 重导入 |
| 月度筛选同一部门出现多个名字 | 同上，记录挂在不同的 `workshop_id` 上 | 同上；筛选列表只返回未软删车间 | **需要**：合并脚本 |
| AI 分析「添加产品」点击无响应 | 旧代码用 `crypto.randomUUID()`，该 API 只在 HTTPS / localhost 可用，服务器 HTTP 下点击即抛异常 | 改为页面内自增 ID，不依赖安全上下文 | 不需要 |

同批还修复了：总览「今日」按东八区取窗口、软删车间不计入总览/月度统计、月度列表返回 `workshop_name`、五个列表接口的分页信封、采集响应类型、目标单耗上限、采集循环重复启动与关闭后空转、车间删除守卫（有月度记录时拒绝删除）。

## 2. 部署前必须处理（阻断项）

### 2.1 代码与镜像

- 以本次推送的 HEAD 构建，**不要复用旧镜像**：后端镜像内置了 `alembic/`、`scripts/` 与业务代码。
- 前端也要重建，AI 分析页与分页契约的修复在前端产物里。

### 2.2 Alembic 版本行先对齐

新镜像里已没有旧的 `0069_energy_add_workshop_excluded_energy_types.py`。如果目标库 `alembic_version` 仍指向该旧 revision，`migrate` 会报 `Can't locate revision`；`backend` 依赖 migrate 成功启动，会一起起不来。

先查：

```sql
SELECT version_num FROM alembic_version;
```

按结果处理：

| 当前版本行 | 操作 |
|---|---|
| `0072_add_equipment_quantity` | 直接 `alembic upgrade head`（只跑 0073） |
| `0069_energy_add_workshop_excluded_energy_types` 且 equipment 迁移效果已存在 | `alembic stamp 0073_energy_add_workshop_excluded_energy_types` |
| `0069_energy_add_workshop_excluded_energy_types` 且 equipment 迁移效果缺失 | `stamp 0068_add_background_jobs` → `upgrade 0072_add_equipment_quantity` → `stamp 0073_energy_add_workshop_excluded_energy_types` |
| `0068_add_background_jobs` 或更早 | 直接 `alembic upgrade head` |

判断 equipment 效果是否已存在：

```sql
SELECT to_regclass('equipment.sync_logs') IS NOT NULL,
       EXISTS(SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'equipment' AND table_name = 'equipments'
                AND column_name = 'quantity'),
       EXISTS(SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'equipment' AND table_name = 'import_audit_logs'
                AND column_name = 'override_type');
```

三项全为 `true` 才能直接 stamp 0073。不要在列已存在时再执行 `upgrade 0073`，`0073` 的 `ADD COLUMN` 不是幂等的。

按你们环境的 compose 文件执行，例如：

```bash
docker compose run --rm migrate /app/.venv/bin/alembic stamp 0073_energy_add_workshop_excluded_energy_types
docker compose up -d
```

### 2.3 环境变量

必须存在且有效：

- `FEISHU__ENERGY__APP_TOKEN`：月度多维表格 base
- `FEISHU__ENERGY__ALERT_APP_TOKEN`：日数据 base
- `FEISHU__ENERGY__WORKSHOP_TABLE_ID`、`FEISHU__ENERGY__MONTHLY_TABLE_ID`：月度同步/「导入数据」使用；为空会导致该链路失败

### 2.4 保持单 uvicorn worker

导入任务状态存在进程内存储（`D-11`）。不要给后端加 `--workers`，也不要多副本，否则轮询 `/api/v1/energy/jobs/{job_id}` 可能 404。当前 Dockerfile 是单 worker，保持现状即可。

### 2.5 迁移内容确认

- `0073_energy_add_workshop_excluded_energy_types`：给 `energy.energy_workshops` 增加 `excluded_energy_types`，并把 `动力运行` / `RTO` 标记为不计入全厂电耗汇总（它们与构成项重复上报）。
- 若目标库版本较旧，`alembic upgrade` 会连带执行 equipment 的 `0069`–`0072`，这是预期行为，先迁移后重启。

## 3. 部署后数据步骤（按顺序，由模块负责人执行）

### 3.1 合并存量车间别名

先 dry-run 核对动作，再写库并保留审计 JSON：

```bash
python scripts/migration/merge_energy_workshop_aliases.py
python scripts/migration/merge_energy_workshop_aliases.py --apply --audit-path /tmp/energy-workshop-merge.json
```

脚本会：

- 把别名实体名下的月度记录改挂到规范车间；
- 软删除别名实体并让出唯一编码（`<原code>#merged#<uuid前8>`）；
- 同步 `energy_device_configs.workshop` 字符串；
- 给 `RTO` 补 `excluded_energy_types` 标记（避免迁移先于实体创建时漏标）；
- 迁移前后按能源类型校验 `count(*)` 与 `sum(value)` 不变，不一致会失败。

### 3.2 重新导入

合并完成后触发一次按年/按月导入，让源表里尚未入库的数据按规范车间名落库（历史上被跳过的 `RTO用电` 等也依赖这一步补齐）。

### 3.3 预警对账（存量有旧预警时）

若此前用错误日期口径导入过日数据，旧预警的 `trigger_value` 可能与当日实际用量不一致。先 dry-run，再 `--apply`：

```bash
python scripts/migration/realign_energy_alerts_to_daily_data.py
python scripts/migration/realign_energy_alerts_to_daily_data.py --apply
```

跑完后再导入一次日数据，按修正后的用量重建预警。

### 3.4 禁止执行的脚本

- `scripts/migration/shift_energy_daily_date_to_cst.py`：**不得再执行**。日期已由修好代码后的全量重导入原地自愈，再平移会把数据整体推早一天并撞唯一键。
- `scripts/seed/seed_energy_data.py`：本地造数脚本，**未纳入本次提交，任何环境都不要执行**。

## 4. 验收清单

### 4.1 接口

1. `GET /api/v1/energy/workshops`：不再出现 `QC`、`炊事班`、`生活办公`、`废水站`、`环保中心(含RTO)`、`303车间`、`RTO(天然气)`。
2. `GET /api/v1/energy/workshops?production_only=true`：返回 9 个生产车间；AI 分析页车间下拉应有 9 项。
3. 五个列表接口翻页不再重复，`meta.total/page/page_size` 正常。

### 4.2 页面

1. 能源总览：切换电/水/汽/气，同一部门显示同一个名称；全厂合计不含 `动力运行` / `RTO` 的电耗。
2. 月度记录：车间筛选栏同一部门只剩一个选项；列表带 `workshop_name`。
3. AI 分析：点「添加产品」能新增一行，产量输入框为空；「从生产模块同步」点击后是提示，不是报错；选车间 + 月份 + 填产量后可正常分析。
4. 采集日志：手动采集返回结果有类型化状态；详情抽屉能打开。

### 4.3 运维

1. `alembic current` 显示 `0073_energy_add_workshop_excluded_energy_types (head)`。
2. 后端日志无 `Can't locate revision`、无导入批量异常。
3. 后端保持单 worker。

## 5. 回滚

- 代码：回退到上一镜像/commit 重新部署。
- 数据合并：以 `--audit-path` 的 JSON 为依据反向改挂记录并恢复别名实体；注意软删除时 `code` 已被改写为 `<原code>#merged#<uuid前8>`，恢复时需一并还原。
- `0073` 的 `downgrade` 会删除 `excluded_energy_types` 列，属数据丢失，非必要不要回退迁移。

## 6. 已知但不阻断本次部署

`D-01` 预警规则未接入判定、`D-05` `EnergyType` 枚举缺 `natural_gas`、`D-06` 天然气靠子串识别、`D-07` / `D-08` 唯一约束改造需迁移审批、`D-10` 跨月记录归属、`D-11` 进程内任务存储、`D-12` 采集详情时间窗、`D-03` 折算系数无维护入口、`D-44` 跨单位合计、`D-55` 软删日行与预警联动、`D-37` 浏览器直写。均为已登记的业务/架构决策项，不影响上述三个现场问题的修复。
