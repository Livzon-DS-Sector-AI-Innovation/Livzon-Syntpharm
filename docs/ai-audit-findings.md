# AI Audit Findings

## Baseline (commit: to be filled, date: 2025-07-25)

---

### Category 1: Repository layout

| Files inspected | ~30 (all directories via listing) |
| Files not inspected | 0 |
| Rules evaluated | 9 (Q1-Q9 covering all listed rules) |
| Rules not evaluated | 1 (training template dir presence — confirmed, not audited in depth) |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
- `backend/scripts/run_edbo.py` — 仓库组织/脚本 — Standalone EDBO+ runner script kept at `scripts/` root intentionally. Not a violation.

---

### Category 2: Secrets and hardcoded values

| Files inspected | ~200 (grep scans across backend/app, frontend/src, nginx, Docker) |
| Files not inspected | 0 |
| Rules evaluated | 9 (all Q1-Q9) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
- [x] `backend/app/core/config.py:265-266` — 仓库通用规则/禁止硬编码绝对路径 — Hardcoded Windows paths removed. `SOFFICE_FALLBACK_PATHS` now empty; `SOFFICE_PATH` env var is the sole configuration source. — severity: medium — **RESOLVED**

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 3: Backend module boundaries

| Files inspected | ~300 Python files across 12 modules |
| Files not inspected | 0 |
| Rules evaluated | 8 (Q1-Q8 covering cross-module imports, circular deps, new modules, global layer, env vars, event naming) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 1 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
- [ ] `backend/app/modules/quality/` — 模块所有权/public_api — The quality module has no `public_api.py` file. No other module currently imports from quality, so this is not causing violations. But if another module needs quality's functionality in the future, there is no public entry point. This is a structural observation, not an active violation. — severity: low

#### Accepted exceptions
_None yet._

---

### Category 4: API and authentication

| Files inspected | ~50 API files + router.py |
| Files not inspected | 0 |
| Rules evaluated | 7 (all Q1-Q7) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 1 |
| Status | complete |

#### Confirmed
- [x] `backend/app/modules/research/repository.py` — API 规范/必须: 业务异常使用 app/core/exceptions.py — Repository layer was raising raw `HTTPException(status_code=404)`. Fixed: repository now returns `None` when entity not found; service layer checks and raises `NotFoundException` from `app.core.exceptions`. — severity: blocking — **RESOLVED**

#### Uncertain
- [ ] `backend/app/modules/safety/api/files.py:127,134` — API 规范/必须 — Uses raw `HTTPException(status_code=404)` in API layer. AGENTS.md requires "业务异常" to use `app.core.exceptions`. A file-not-found 404 in a file-serving endpoint may be considered an HTTP-level response, not a business exception. The project provides `NotFoundException(resource, id)` for business entities; whether file retrieval qualifies is debatable. — severity: low

#### Accepted exceptions
_None yet._

---

### Category 5: Models and migrations

| Files inspected | 40 migration files + ~40 model files |
| Files not inspected | 0 |
| Rules evaluated | 11 (all Q1-Q11) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 6: Configuration and logging

| Files inspected | ~300 module Python files |
| Files not inspected | 0 |
| Rules evaluated | 9 (all Q1-Q9) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 7: External services and background tasks

| Files inspected | ~300 module Python files + core/llm/ + core/tasks.py |
| Files not inspected | 0 |
| Rules evaluated | 9 (all Q1-Q9) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 8: Backend tests

| Files inspected | 33 test files |
| Files not inspected | 0 |
| Rules evaluated | 5 (all Q1-Q5) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 9: Frontend component boundaries

| Files inspected | ~50 page files + ~15 barrel files |
| Files not inspected | 0 |
| Rules evaluated | 8 (all Q1-Q8) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
- [x] `frontend/src/app/(dashboard)/settings/page.tsx` — Server Component vs Client Component — Was directly importing `<Result>` from antd. Fixed: extracted to `NoAccessResult` Client Component. — severity: medium — **RESOLVED**
- [x] `frontend/src/app/(dashboard)/hr/training/ledger/page.tsx` — Server Component vs Client Component — Was directly importing `<Spin>` from antd. Fixed: replaced with `<LoadingSpinner>` Client Component. — severity: medium — **RESOLVED**
- [x] `frontend/src/app/(dashboard)/hr/training/annual-plan/page.tsx` — Server Component vs Client Component — Was directly importing `<Spin>` from antd. Fixed: replaced with `<LoadingSpinner>` Client Component. — severity: medium — **RESOLVED**

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 10: Frontend API and generated types

| Files inspected | ~42 action files + ~15 API client files |
| Files not inspected | 0 |
| Rules evaluated | 7 (Q1-Q7) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 11: Proxy and routing

| Files inspected | proxy.ts (28 lines) + lib/api/ |
| Files not inspected | 0 |
| Rules evaluated | 6 (all Q1-Q6) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 12: Cross-project OpenAPI

| Checks verified | 1 (CI job exists and runs `scripts/ci.sh openapi`) |
| Checks failing | 0 |
| Status | complete |

CI configuration in place. OpenAPI drift check runs on every push/PR via `.github/workflows/ci.yml:57-74`.

---

### Category 13: Docker and deployment

| Files inspected | 5 (2 Dockerfiles, 3 compose files) |
| Files not inspected | 0 |
| Rules evaluated | 5 (all Q1-Q5) |
| Rules not evaluated | 0 |
| Confirmed findings | 0 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
_None._

#### Accepted exceptions
_None yet._

---

### Category 14: E2E

| Checks verified | 1 (CI job exists and runs `scripts/ci.sh e2e`) |
| Checks failing | 0 |
| Status | complete |

CI configuration in place. E2E tests run on push to main via `.github/workflows/ci.yml:183-203`.

---

## Audit Summary

| Category | Status | Confirmed | Uncertain |
|---|---|---|---|
| 1. Repository layout | complete | 0 | 0 |
| 2. Secrets and hardcoded values | complete | 0 | 0 |
| 3. Backend module boundaries | complete | 0 | 1 |
| 4. API and authentication | complete | 0 | 1 |
| 5. Models and migrations | complete | 0 | 0 |
| 6. Configuration and logging | complete | 0 | 0 |
| 7. External services and background tasks | complete | 0 | 0 |
| 8. Backend tests | complete | 0 | 0 |
| 9. Frontend component boundaries | complete | 0 | 0 |
| 10. Frontend API and generated types | complete | 0 | 0 |
| 11. Proxy and routing | complete | 0 | 0 |
| 12. Cross-project OpenAPI | complete | 0 | 0 |
| 13. Docker and deployment | complete | 0 | 0 |
| 14. E2E | complete | 0 | 0 |
| **Total** | **14/14 complete** | **0** | **2** |

---

## PR Reviews

_No PRs reviewed yet._

### Template for PR entries

```markdown
### PR #N: <title> (base: <sha>, head: <sha>, date: <date>)

Files changed:
- `path/file1.ts`
- `path/file2.py`

Categories affected: ...

#### New findings (not in baseline)
- [ ] `file:line` — <rule> — <evidence> — severity: <...>

#### Worsened findings (existed in baseline, now worse)
- [ ] `file:line` — <rule> — <baseline evidence> → <new evidence>
```

### PR #10: Ruanjiaheng (base: main, head: ruanjiaheng, date: 2026-07-27)

Files changed: 93 files (see `git diff --stat main...ruanjiaheng`)

Categories affected: all 14

#### New findings (not in baseline)

- [x] `frontend/src/components/settings/NoAccessResult.tsx` — 前端/模块边界 — `NoAccessResult` is imported via `@/components/settings/NoAccessResult` (direct path) instead of through the `settings/index.ts` barrel. The barrel currently exports `LLMConfigClient` and `ModuleSettingsClient` but not `NoAccessResult`. Add the export to `index.ts` and update all imports to use `@/components/settings`. — severity: low — **RESOLVED** (barrel updated, import fixed)

#### Worsened findings (none)

#### Previously resolved, still resolved

- Category 2: `SOFFICE_FALLBACK_PATHS` hardcoded Windows paths — removed ✓
- Category 4: Repository `HTTPException` → service `NotFoundException` — fixed ✓  
- Category 9: `settings/page.tsx` antd Result → NoAccessResult — fixed ✓
- Category 9: `training/ledger/page.tsx` antd Spin → LoadingSpinner — fixed ✓
- Category 9: `training/annual-plan/page.tsx` antd Spin → LoadingSpinner — fixed ✓

#### Category summaries

| Category | New violations | Status |
|---|---|---|
| 1. Repository layout | 0 | ✓ |
| 2. Secrets | 0 | ✓ |
| 3. Module boundaries | 0 | ✓ |
| 4. API & auth | 0 | ✓ |
| 5. Models & migrations | 0 | ✓ |
| 6. Configuration & logging | 0 | ✓ |
| 7. External services & tasks | 0 | ✓ |
| 8. Backend tests | 0 | ✓ |
| 9. Frontend boundaries | 0 | ✓ |
| 10. Frontend API & types | 0 | ✓ |
| 11. Proxy & routing | 0 | ✓ |
| 12. OpenAPI | 0 | ✓ |
| 13. Docker | 0 | ✓ |
| 14. E2E | 0 | ✓ |

### PR #10: Ruanjiaheng (base: main, head: ruanjiaheng, date: 2026-07-27)

Files changed: 93 files across all categories

#### New findings (not in baseline)

- [x] `frontend/src/components/settings/NoAccessResult.tsx` — 前端/模块边界 — Imported via `@/components/settings/NoAccessResult` (direct path) instead of through `settings/index.ts` barrel. — severity: low — **RESOLVED** (added to barrel, import updated to `@/components/settings`)

#### Category summaries

| Category | New violations | Note |
|---|---|---|
| 1. Repository layout | 0 | |
| 2. Secrets | 0 | CI-only credentials, in scope |
| 3. Module boundaries | 0 | |
| 4. API & auth | 0 | E2E auth hardening |
| 5. Models & migrations | 0 | Migration CI passes |
| 6. Config & logging | 0 | |
| 7. External services | 0 | |
| 8. Backend tests | 0 | |
| 9. Frontend boundaries | 1 | NoAccessResult barrel missing |
| 10. Frontend API & types | 0 | |
| 11. Proxy & routing | 0 | |
| 12. OpenAPI | 0 | CI passes |
| 13. Docker | 0 | |
| 14. E2E | 0 | CI updated |

### PR #11: Ruanjiaheng — E2E rework (head: ruanjiaheng, date: 2026-07-27)

Files changed: 98 files across all 14 categories

#### New findings

_None._

#### Category summaries

| Category | New violations | Note |
|---|---|---|
| 1. Repository layout | 0 | |
| 2. Secrets | 0 | CI-only 127.0.0.1 references excluded |
| 3. Module boundaries | 0 | |
| 4. API & auth | 0 | |
| 5. Models & migrations | 0 | 0046 migration CI-validated |
| 6. Config & logging | 0 | |
| 7. External services | 0 | |
| 8. Backend tests | 0 | |
| 9. Frontend boundaries | 0 | NoAccessResult barrel export resolved in PR #10 |
| 10. Frontend API & types | 0 | |
| 11. Proxy & routing | 0 | proxy.ts untouched |
| 12. OpenAPI | 0 | CI passes |
| 13. Docker | 0 | |
| 14. E2E | 0 | CI passes |

#### Previously resolved from PR #10, still resolved

- Category 9: NoAccessResult barrel — ✓ fixed

### PR #13: lzhc-zhuang — Energy daily data, Equipment module refactor, Safety workflows (head: lzhc-zhuang, date: 2026-07-29)

Files changed: 277 (core: energy scheduler, equipment API refactor, safety scheduled tasks/ai workflows, migrations 0047-0049, frontend energy/equipment/safety pages, nginx timeout)

Categories affected: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

#### Blocking findings

- [ ] `backend/app/modules/safety/api/ai_workflow.py` + `backend/app/modules/safety/api/scheduled_tasks.py`
  **Rule: 后端 / 目录结构** — `app/modules/` 下每个模块通过 `api/` 子包独立维护 API，模块的 `api/__init__.py` 负责聚合所有子路由。
  **Evidence:** `ai_workflow_router` and `scheduled_tasks_router` are defined in their respective files but NOT included via `router.include_router()` in `safety/api/__init__.py`. All 21 new endpoints are unreachable at runtime.
  **Severity:** blocking

- [ ] `backend/app/modules/safety/api/ai_workflow.py:23`
  **Rule: 后端 / 模块所有权 / 禁止** — "直接 import 其他模块的 repository.py、service.py 或 models.py（只能通过 public_api.py）"。此处为同模块内部导入，但导入的类不存在。
  **Evidence:** `from app.modules.safety.service import ConfigService` imports a class that does not exist anywhere in the `safety/` module. `service/config.py` only contains `_get_ai_config()` and `create_ai_service()` functions. Causes `ImportError` at module load.
  **Severity:** blocking

- [ ] `backend/app/modules/safety/service/scheduled_task.py:44,56,84,99`
  **Rule: 后端 / 模块结构** — 模块通过 `service/`、`repository/`、`models/` 组织业务逻辑，导入的符号必须在对应模块内定义。
  **Evidence:** `from app.modules.safety.scheduler import compute_next_run` imports from `scheduler.py`, which is a 33-line stub containing only `scheduled_task_loop()`. `compute_next_run` and `execute_single_task` are not defined. Causes `ImportError` at runtime.
  **Severity:** blocking

- [ ] `backend/app/modules/energy/scheduler.py:223,228` + `backend/app/main.py`
  **Rule: 配置管理规范 / 新增** — "Other API keys/credentials → core/config.py Settings class"。部署配置字段必须在 `Settings` 类中定义。
  **Evidence:** `settings.ENERGY_BITABLE_AUTO_SYNC_ENABLED` and `settings.ENERGY_BITABLE_SYNC_HOUR` accessed but NOT defined in `core/config.py` Settings class. Pydantic `extra="ignore"` means these attributes don't exist → `AttributeError` at runtime.
  **Additional:** `bitable_monthly_sync_loop` and `bitable_daily_sync_loop` also never registered via `register_background_worker()` in `main.py`, making them dead code even if the config issue were fixed.
  **Severity:** blocking

- [ ] `backend/app/modules/equipment/models/work_order.py:46` + `backend/alembic/versions/0049_add_equipment_model_changes.py`
  **Rule: Model-Migration 绑定** — "任何 SQLAlchemy Model 的新增、删除、字段修改、索引修改、**约束修改**，都必须在同一个 PR/commit 中包含对应 Alembic migration"。
  **Evidence:** Model `ck_work_orders_order_type` CheckConstraint was updated from 5 values to 6 (added `'巡检'`), but migration 0049 only alters the column comment — NOT the constraint text. The database still enforces the old 5-value constraint. Inserts with `order_type='巡检'` will fail with check constraint violation.
  **Severity:** blocking

- [ ] `frontend/src/components/equipment/inspection/index.ts:1`
  **Rule: 前端 / Barrel 文件规则** — "当 Server Component 从 components/<模块>/index.ts 导入 Client 组件时，如果导出的组件使用了 Zustand store、React Context 或其他 Context-based 状态管理，barrel 文件**必须**加 'use client'。"
  **Evidence:** `'use client'` directive removed from barrel that exports Client Components (`InspectionPage`, `InspectionTasksTab`, `InspectionRoutesTab`, etc.) using antd components, hooks, and Zustand stores. Will cause Next.js build error: `TypeError: createContext is not a function`.
  **Severity:** blocking

- [ ] `backend/app/modules/safety/service/safety.py.bak.indent-fix`
  **Rule: 仓库组织 / 文档** — "禁止将 .docx、.xlsx 或 PDF 文件放在 backend/ 根目录"。备份文件、自动生成文件等同理应排除在版本控制之外。
  **Rule: 仓库通用规则** — "禁止硬编码绝对文件路径（使用配置、环境变量或相对路径）"。
  **Evidence:** 2177-line `.bak` backup file committed to git. Contains hardcoded `C:/Windows/Fonts/simsun.ttc` paths (lines 13470-13472). Backup/temp files belong in `.gitignore`, not version control. The Windows paths also violate the no-hardcoded-paths rule.
  **Severity:** blocking

#### High findings

- [ ] `backend/app/modules/energy/scheduler.py:32,42,138,147`
  **Rule: 配置管理规范 / 两层** — 配置分 "部署配置"（`.env` + `core/config.py`）和 "运行时配置"（`core.module_settings` + Web UI）。"模型名称 / 功能开关 / 运营参数 → scripts/seed/seed_module_settings.py + Web UI"。
  **Rule: 配置管理规范 / 禁止** — "在 core/config.py 中存放模型名称等频繁变更的配置"。
  **Evidence:** `ENERGY_AUTO_COLLECT_ENABLED` moved from `get_module_setting_bool("energy", ...)` (runtime config, DB-managed, Web UI editable) to `get_settings().ENERGY_AUTO_COLLECT_ENABLED` (deployment config, needs restart to change). Feature flags must stay in runtime config layer.
  **Severity:** high

- [ ] `backend/app/modules/safety/api/scheduled_tasks.py:29,224`
  **Rule: 认证与权限** — "新增业务接口时必须显式选择 require_user / optional_user / public。未声明的业务接口按 require_user 处理"。
  **Evidence:** `get_data_source_options()` (line 29) and `get_feishu_ws_status()` (line 224) have no `current_user` parameter at all — not even `CurrentUser | None`. Per the rule, undeclared endpoints default to `require_user`, yet neither enforces authentication. Must explicitly declare auth requirement.
  **Severity:** high

- [ ] `frontend/src/actions/energy.ts:319`
  **Rule: 前端 / 路由转发** — "服务器端代码使用 API_BASE_URL 环境变量"。
  **Evidence:** `process.env.API_BASE_URL + '/api/v1/energy/sync/monthly' || '/api/v1/energy/sync/monthly'` — JavaScript evaluates `+` before `||`, producing `"undefined/api/v1/..."` when `API_BASE_URL` is unset. Correct form: `(process.env.API_BASE_URL || '') + '/api/v1/energy/sync/monthly'`.
  **Severity:** high

#### Medium findings

- [ ] `backend/alembic/versions/0047_add_energy_daily_data_table.py:3`
  **Rule: 迁移规范 / 命名** — "迁移文件必须使用顺序编号格式 NNNN_descriptive_name.py"。Revision ID 也应与文件名一致。
  **Evidence:** Docstring `Revision ID` says `0048_...` but actual `revision` variable is `0047_...`; `Revises` in docstring references auto-generated hash `49684887bf7e` instead of the actual down-revision `0046_qms_deviation_settings`. Docstring was not updated after renaming.
  **Severity:** medium

- [ ] `backend/alembic/versions/0048_make_rule_id_nullable_in_energy_alert.py:3`
  **Rule: 迁移规范 / 命名** — 同上。
  **Evidence:** Same docstring mismatch: `Revision ID` says `0049_...` but actual `revision` is `0048_...`; `Revises` shows wrong `0046_qms_deviation_settings` (should be `0047_add_energy_daily_data_table`).
  **Severity:** medium

- [ ] `backend/alembic/versions/0049_add_equipment_model_changes.py:30,40,71-73`
  **Rule: Orphan Table** — "数据库中存在但当前代码没有 model 的表，不得自动删除。必须查询 row count、检查代码引用、确认业务负责人是否需要保留、完成备份后，明确批准才允许创建 DROP migration"。
  **Rule: Model-Migration 绑定 / 禁止** — "执行包含无关 DROP TABLE / DROP COLUMN 的自动生成 migration"。
  **Evidence:** Drops 4 columns (`equipment_categories.department_id`, `locations.department_id`, `maintenance_plans.executor_id`, `maintenance_plans.category_id`) without visible approval documentation or row-count checks.
  **Severity:** medium

- [ ] `backend/app/modules/energy/bitable_daily_import.py:142,181`
  **Rule: 日志规范** — "始终包含上下文：logger.info('batch created', extra={'batch_id': id, 'module': 'production'})"。"禁止记录 API key、token、密码等敏感信息"。
  **Evidence:** `logger.info(f"Found {len(records)} records...")` uses f-string instead of lazy `%s` (no performance benefit but missing `extra={}` for structured context); `logger.exception(f"Error processing record: {record}")` logs the entire record dict, which may contain sensitive workshop/business data. Should log only identifiers with `extra={}`.
  **Severity:** medium

- [ ] `frontend/src/types/energy.ts:228-231`
  **Rule: 前端 / API 类型来源** — "所有 API 相关的类型（请求参数、响应数据）必须从 @/types/generated/schema 导入。禁止手写 API 类型。"
  **Evidence:** `ProcessRecordInput` was previously a `components['schemas']['AlertRecordProcessRequest']` alias. The PR replaced it with a hand-written interface. The generated `AlertRecordProcessRequest` type exists in `@/types/generated/schema` with identical fields (status, process_note).
  **Severity:** medium

- [ ] `frontend/src/app/(dashboard)/energy/devices/page.tsx:7-8`
  **Rule: 前端 / 模块边界** — "禁止跨模块直接 import 组件内部文件。如果需要用其他模块的东西，只能从该模块的 index.ts 导入。"
  **Evidence:** `import { DeviceTable } from '@/components/energy/DeviceTable'` and `import { DeviceDrawer } from '@/components/energy/DeviceDrawer'` bypass the barrel `@/components/energy`. Both components are exported from `components/energy/index.ts`.
  **Severity:** medium

#### Low findings

- [ ] `backend/app/modules/equipment/models/personnel.py:18,23`
  **Rule: ORM 规则 / 必须** — "字段命名使用英文 snake_case，显式声明唯一约束、索引"。
  **Evidence:** `EquipmentRole.code` has both `unique=True` on `mapped_column` AND `UniqueConstraint("code", name="uq_equipment_role_code")` in `__table_args__`. Alembic will generate two redundant unique constraints on the same column (one auto-named, one explicitly named). Only one is needed.
  **Severity:** low

#### Category summaries

| Category | Blocking | High | Medium | Low | Note |
|---|---|---|---|---|---|
| 1. Repository layout | 1 | 0 | 0 | 0 | .bak file |
| 2. Secrets | 1 | 0 | 0 | 0 | C:/Windows paths in .bak |
| 3. Module boundaries | 0 | 0 | 0 | 0 | No cross-module direct imports |
| 4. API & auth | 2 | 1 | 0 | 0 | Routers not registered + ConfigService missing |
| 5. Models & migrations | 1 | 0 | 3 | 1 | CheckConstraint mismatch + docstring + DROP COLUMN |
| 6. Config & logging | 1 | 1 | 1 | 0 | ENERGY_BITABLE_* missing + config layer + logging |
| 7. External services | 1 | 0 | 0 | 0 | compute_next_run from stub |
| 8. Backend tests | 0 | 0 | 0 | 0 | Tests updated for refactored service signatures |
| 9. Frontend boundaries | 1 | 0 | 1 | 0 | 'use client' removed + barrel bypass |
| 10. Frontend API & types | 0 | 1 | 1 | 0 | API_BASE_URL bug + hand-written type |
| 11. Proxy & routing | 0 | 0 | 0 | 0 | proxy.ts unchanged |
| 12. OpenAPI | 0 | 0 | 0 | 0 | schema.ts regenerated, CI passes |
| 13. Docker | 0 | 0 | 0 | 0 | nginx timeout changes, reasonable |
| 14. E2E | 0 | 0 | 0 | 0 | CI config not in this PR |

#### Previously resolved from PR #12, still resolved

- Category 4: `daily_import_from_bitable` auth — ✓ fixed
- Category 10: 12 API types + ~18 equipment types — ✓ fixed

#### Previously resolved from PR #12, regressed

_None._

