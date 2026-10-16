# 能源车间实体统一与总览分布拆分 · 变更说明

> 状态：已落地并本地实测通过，已随 `386c23c8` 提交，待 UAT/生产手动验证
> 模块级规格见 [energy-module-prd.md](./energy-module-prd.md)（本文只覆盖这一个工作包）
> 分支：`lzhc-zhuang-energy`
> 相关：[energy-bitable-field-mapping.md](./energy-bitable-field-mapping.md)（字段契约与叫法对照表）
> 关联提交：`4d936c37 fix(energy): 三个页面冷加载不取数`、`d976e3b0 fix(energy): 合并多维表格里的同义车间名`

## 1. 背景

能源模块三个页面（`/energy`、`/energy/monthly`、`/energy/workshops`）的数据来自飞书多维表格的月度交叉表。同一部门在 电/水/汽 三个 section 里写法不同，交叉表导入器按字面建了多个车间实体，导致：

- **月度记录车间筛选选「质量控制部」只有电量**，要再选「QC」才看到水量 —— 筛选按 `workshop_id` 精确过滤，两个实体的记录天然互斥。
- `环保中心` 分裂成 `环保中心(含RTO)`（电）、`废水站`（水）、`环保中心`（汽）三个实体。
- `RTO` 只剩气耗：导入器把 `RTO用电` 整行**跳过**，每月约 16,834 kWh（全厂电 0.7%）从未入库。
- `/energy` 区域分布把电（kWh）、水（m³）、汽（t）、气（Nm³）画进同一张饼图，跨单位百分比无意义。

## 2. 目标与非目标

**目标**

1. 同一部门在库里只有一个车间实体，筛选栏不再出现两个名称。
2. 修复必须在**导入器 + 数据迁移**两侧同时成立：只改数据，下次导入会被打回原形。
3. 区域分布按能源类型拆分，且拆分口径与源表车间数可核对。
4. 字段契约、叫法对照、已知缺陷沉淀成文档。

**非目标**

- 不给 `energy_workshops` 加列（避免 Alembic migration），`含RTO` 这类限定只记在映射文档里。
- 不合并 `动力车间` 与 `动力运行`（两个独立组织，已裁定）。
- 不改饼图为「Top-N + 其他」（遗留项）。
- 不动 `bitable_daily_import.py` 与 `bitable_sync.py` 的取数口径（后者只补 `is_deleted` 过滤与 name/code 拆字典）。

## 3. 方案

### 3.1 导入器 — `app/modules/energy/bitable_cross_import.py`

| 改动 | 说明 |
|---|---|
| `WORKSHOP_ALIASES` 常量 | 登记 9 条「归一化后叫法 → 规范名」，覆盖 6 个规范实体（含 `RTO用电`/`RTO(天然气）` → `RTO`、`303车间` → `303、106车间`） |
| `_resolve_workshop_name` | 归一化之后套别名表 |
| `_get_or_create_workshop` | `name` 与 `code` 两次查询都补 `is_deleted == False`；同名多行取 `id` 最小的一条而不是抛错 |
| `_normalize_workshop_name` | 删掉按 `、` 取首段的截断，`303、106车间` 原样保留；纯数字补「车间」的逻辑保留 |
| `_load_workshop_alias_map` | 支持 base 内的 `车间映射` 表覆盖常量，缺表时 `logger.warning` 回退常量 |
| 删除 `RTO用电` 跳过 | 该行原本是电力 section 的普通数据行 |

### 3.2 一次性数据迁移 — `scripts/migration/merge_energy_workshop_aliases.py`

- 默认 dry-run，`--apply` 才写库；`--audit-path` 输出动作清单 JSON 供反向恢复参考。
- 每个别名走两条分支：规范实体已存在 → 改挂记录 + 软删除别名实体；不存在 → 原地改名。
- **顺序有意义**：多条规则指向同一规范实体时，先跑的负责「改名」建出实体，后面的才能「合并」。
- 前置守卫：逐对断言 `(energy_type, record_date)` 无重叠，重叠则该对跳过并报错；软删除时一并让出 `code`（唯一约束不含 `is_deleted`）。
- 不变量：迁移前后按 `energy_type` 的 `count(*)` 与 `sum(value)` 必须完全一致，不一致直接返回失败。
- 幂等：第二次运行 0 动作。
- 不做物理删除，不改 Alembic 迁移。

### 3.3 总览分布按能源类型拆分

- 后端 `repository.get_energy_statistics`：两个 select 分支都带上 `energy_type`，`group_by` 追加该列。
- `schemas.EnergyOverviewDistributionPoint` 新增 `energy_type` 字段；`openapi.json` 与前端生成类型同步重出。
- 前端 `DistributionChart`：卡片内 `Segmented`（电/水/汽/气），只渲染当前类型；标题显示「电 · 合计 2,365,668 kWh」；无可切类型时不显示分段控件；该类型无数据时显示空态。选中项在可用集合变化时回落到第一个可用类型。

## 4. 验收标准与实测结果

| # | 验收项 | 结果 |
|---|---|---|
| 1 | `pytest tests/modules/energy/test_bitable_workshop_alias.py` | 9 passed |
| 2 | `pytest tests/modules/energy/` | 68 passed / 3 failed（**均为既有失败**：用例假设 `energy_device_configs` 为空，本地库有 5 行假种子） |
| 3 | `ruff check` + `mypy` 变更文件 | 全部通过 |
| 4 | 迁移不变量（按 energy_type 的 count/sum 前后一致） | 通过（electricity 16,488 / natural_gas 573 / steam 5,946 / water 10,332 未变） |
| 5 | 迁移幂等（第二次运行 0 动作） | 通过 |
| 6 | 未删除车间数 | **30**，列表内不再出现 `QC`/`炊事班`/`生活办公`/`废水站`/`环保中心(含RTO)`/`303车间`/`RTO(天然气）` |
| 7 | 重新导入后不新建别名车间 | 通过（34 张月度表全量重跑，车间数仍 30） |
| 8 | `/energy` 近 30 天分布 | 电 27 片 / 水 19 / 汽 12 / 气 1，与源表规范实体数（27/20/14/1）差异全部可由「窗口内零值」解释 |
| 9 | `RTO` 实体 | 同时持有 electricity 16,834 kWh 与 natural_gas 4,977 Nm³，饼图出现 `RTO: 0.7%` 标签 |
| 10 | 前端分段切换 | 四个分段标题合计与 API 完全一致 |

## 5. 执行记录（仅本地）

1. `merge_energy_workshop_aliases.py --apply` × 3 轮（5 对 → 补 `废水站` → 补 `RTO(天然气）`），审计 JSON 落在 `/tmp/`。
2. 为补齐 `RTO` 历史电耗，**全量重跑 34 张月度表**（2024-01 ~ 2026-10）。月度记录由 1,635 条增至 33,339 条，其中 2026-04-01 之前 28,717 条为本次回填的真实历史数据 —— **已确认保留**。
3. 回填暴露真 bug：2024-07 及之前的表把 303 写成 `303车间`，导入后重新分裂出实体。补别名 + 再跑合并（389 条改挂）。
4. `docker restart erp-backend` 使导入器改动生效。

**UAT / 生产**：由用户执行同一脚本 `python scripts/migration/merge_energy_workshop_aliases.py --apply`，再触发按年/按月导入。

## 6. 影响面与回滚

- 受影响表：`energy.energy_workshops`（改名/软删除）、`energy.energy_monthly_records`（改挂 `workshop_id`）、`energy_device_configs.workshop`（字符串跟随改名）。
- `energy_alert_rules` / `energy_alert_records` / `energy_daily_data` 无 workshop 列，不受影响。
- 前端零结构改动：车间筛选栏数据源就是已过滤软删除的 `GET /api/v1/energy/workshops`。
- 回滚：别名实体是**软删除**，按审计 JSON 里的 `workshop_id`/`target_workshop_id`/`moved` 可反向改挂并置 `is_deleted = false`；`code` 已被改写成 `<原code>#merged#<uuid前8>`，恢复时需一并还原。改名分支（`RTO(天然气）` → `RTO`）直接改回即可。

## 7. 遗留项

| 项 | 位置 | 说明 |
|---|---|---|
| `import_year` 年度合计恒为 0 | `bitable_cross_import.py` | 读 `created`/`updated`，而 `import_month` 返回 `total_created`/`total_updated` |
| 天然气子串识别永久改写 `current_energy_type` | 同上 | 当前表布局恰好无害，源表调整行序会误判 |
| `category` 从不被导入器设置 | 同上 | 建议归类见映射文档 |
| 唯一约束不含 `date_range_end` | `models.py` | 同日期范围表计互相覆盖 |
| `车间映射` 表未创建 | 多维表格 | 目前只有代码常量生效 |
| 饼图 58 片可读性 | `DistributionChart.tsx` | 建议 Top-N + 「其他」 |
| 孤儿代码清理 | `*PageClient.tsx`、`lib/api/server/energy.ts`、`actions/energy.ts` | 计划中的 PR4 |
| 抽屉组件取数 | `DeviceDrawer.tsx`、`AlertConfigDrawer.tsx` | 仍是 `useEffect` + setState，计划中的 PR6 |
| AI 分析页缓存 key | `ai-analysis/page.tsx` | 仍用 `['workshops']`，与列表页 `['energy','workshops',...]` 不同源 |
| 既有 3 个失败用例 | `tests/modules/energy/test_repository.py`、`test_service.py` | 假设设备配置表为空，需改为自建 fixture 数据 |
