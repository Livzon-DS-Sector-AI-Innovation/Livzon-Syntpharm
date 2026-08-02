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

#### Resolved findings (fixed in branch ruanjiaheng, commit 55bda93)

- [x] `backend/app/modules/safety/api/ai_workflow.py` + `backend/app/modules/safety/api/scheduled_tasks.py` — Routers registered in `safety/api/__init__.py`. **RESOLVED** — severity: blocking

- [x] `backend/app/modules/safety/api/ai_workflow.py:23` — `ConfigService` created in `safety/service/config.py`. **RESOLVED** — severity: blocking

- [x] `backend/app/modules/safety/service/scheduled_task.py:44,56,84,99` — `compute_next_run` implemented in `safety/scheduler.py`. **RESOLVED** — severity: blocking

- [x] `backend/app/modules/energy/scheduler.py:223,228` + `backend/app/main.py` — `ENERGY_BITABLE_*` added to `core/config.py`, background workers registered. **RESOLVED** — severity: blocking

- [x] `backend/app/modules/equipment/models/work_order.py:46` + migration 0049 — Migration 0050 `fix_work_order_order_type_check` created. **RESOLVED** — severity: blocking

- [x] `frontend/src/components/equipment/inspection/index.ts:1` — `'use client'` directive restored. **RESOLVED** — severity: blocking

- [x] `backend/app/modules/energy/scheduler.py:32,42,138,147` — `ENERGY_AUTO_COLLECT_ENABLED` reverted to `get_module_setting_bool`. **RESOLVED** — severity: high

- [x] `backend/app/modules/safety/api/scheduled_tasks.py:29,224` — `current_user` parameter added. **RESOLVED** — severity: high

- [x] `frontend/src/actions/energy.ts:319` — Operator precedence fixed: `(process.env.API_BASE_URL || '') + '/api/v1/...'`. **RESOLVED** — severity: high

- [x] `backend/alembic/versions/0047_add_energy_daily_data_table.py:3` — Docstring corrected. **RESOLVED** — severity: medium

- [x] `backend/alembic/versions/0048_make_rule_id_nullable_in_energy_alert.py:3` — Docstring corrected. **RESOLVED** — severity: medium

- [x] `backend/app/modules/energy/bitable_daily_import.py:142,181` — Logging fixed to use `extra={}` pattern. **RESOLVED** — severity: medium

- [x] `frontend/src/types/energy.ts:228-231` — `ProcessRecordInput` now aliases `AlertRecordProcessRequest` from schema. **RESOLVED** — severity: medium

- [x] `frontend/src/app/(dashboard)/energy/devices/page.tsx:7-8` — Imports changed to barrel `@/components/energy`. **RESOLVED** — severity: medium

- [x] `backend/app/modules/equipment/models/personnel.py:18,23` — Duplicate `unique=True` removed from `code` column. **RESOLVED** — severity: low

#### Accepted exceptions

- `backend/alembic/versions/0049_add_equipment_model_changes.py:30,40,71-73` — DROP COLUMN approved by architecture lead. — severity: medium — **ACCEPTED**
- `backend/app/modules/safety/service/safety.py.bak.indent-fix` — .bak file already removed from repo. — severity: blocking — **RESOLVED**

#### Category summaries (all resolved)

| Category | Blocking | High | Medium | Low | Status |
|---|---|---|---|---|---|
| 1. Repository layout | 1 | 0 | 0 | 0 | RESOLVED |
| 2. Secrets | 1 | 0 | 0 | 0 | RESOLVED |
| 3. Module boundaries | 0 | 0 | 0 | 0 | Clean |
| 4. API & auth | 2 | 1 | 0 | 0 | RESOLVED |
| 5. Models & migrations | 1 | 0 | 2 | 1 | RESOLVED (1 accepted) |
| 6. Config & logging | 1 | 1 | 1 | 0 | RESOLVED |
| 7. External services | 1 | 0 | 0 | 0 | RESOLVED |
| 9. Frontend boundaries | 1 | 0 | 1 | 0 | RESOLVED |
| 10. Frontend API & types | 0 | 1 | 1 | 0 | RESOLVED |

### PR #17: Ruanjiaheng (head: ruanjiaheng, base: main, date: 2026-08-02)

Files changed: 163 across all 14 categories (core: browser service, safety scheduled tasks/models, equipment/energy API+scheduler refactors, frontend API layer reorganization, E2E enhancements)

#### New findings (not in baseline)

- [x] `backend/app/modules/energy/api.py` — API & auth / Q6-Q7 — All energy CRUD endpoints changed `current_user` from required `CurrentUser` to `current_user: CurrentUser = None` without adding `_require_user(current_user)` or any auth gate. Previously these endpoints required authentication; now all POST/PUT/DELETE and GET operations are publicly accessible with no login check. Every other module in this PR (equipment, safety, quality) properly uses `_require_user(current_user)` after making the parameter optional. — severity: blocking — **RESOLVED** (added `_require_user` helper + calls to all 35 endpoints)

- [x] `backend/app/platform/identity/api.py` — API & auth / Q6 — `GET /me` changed `current_user: CurrentUser` (required) to `current_user: CurrentUser = None` (optional). Function body already handles `current_user=None` at line 176 with explicit 401 check. — severity: high — **RESOLVED** (false positive — body correctly handles None)

- [x] `backend/app/modules/safety/models.py` — Models & migrations / cross-module FK — `ScheduledTask.created_by` declares `ForeignKey("identity.users.id")`, a cross-module FK (safety → identity). Cross-module FKs require architecture lead approval per AGENTS.md rules. — severity: high — **ACCEPTED** (approved by architecture lead, 2026-08-02)

- [x] `frontend/src/actions/safety/helpers.ts` — Frontend API / malformed error — `getApiBaseUrl()` contains malformed error message. Fixed: `'环境变量 API_BASE_URL 未配置，无法连接后端服务'`. — severity: high — **RESOLVED**

- [x] `backend/app/modules/energy/scheduler.py` — Config & logging / Q3 — `bitable_monthly_sync_loop()` now uses `get_module_setting_bool("energy", "ENERGY_BITABLE_AUTO_SYNC_ENABLED")` (runtime config), consistent with `energy_collection_loop()`. — severity: medium — **RESOLVED**

- [x] `backend/app/modules/registration/regulatory_tracker/tasks/sync_tasks.py` — External services / unhandled exceptions — Removed `raise` from two `except Exception:` blocks in `daily_sync_job` and `daily_ai_analysis_job`. — severity: blocking — **RESOLVED**

- [x] `backend/app/modules/equipment/scheduler.py` — External services / unhandled exceptions — Removed `raise` from two `except Exception:` blocks in `maintenance_plan_loop` and `timeout_scan_loop`. — severity: blocking — **RESOLVED**

- [x] `frontend/src/app/(dashboard)/registration/authorization-letter/page.tsx` — Frontend boundaries / Q9 — Added `<h1>授权书</h1>` heading. — severity: medium — **RESOLVED**

- [x] `frontend/src/actions/administration.ts` — Frontend API / Q2 — `batchImportVehicles` migrated from inline `fetch` to `batchImportVehiclesApi()` in `@/lib/api/server/administration`. — severity: low — **RESOLVED**

- [x] `frontend/e2e/auth/callback-errors.spec.ts` — E2E / test consistency — Added heading assertion to "empty token" test. — severity: low — **RESOLVED**

- [x] `docker-compose.ci.yml` / `scripts/ci.sh` — Docker / cleanup — Old `.next-e2e` cleanup removed from `cleanup_e2e()`. Restored `rm -rf "$REPO_ROOT/frontend/.next-e2e"` in cleanup trap and startup. — severity: low — **RESOLVED** (scripts/ci.sh:99,109)

#### Uncertain findings

- [ ] `frontend/e2e/auth/callback-errors.spec.ts` — E2E / error handling — `beforeAll` warmup loop silently exits if all 5 retries fail. Subsequent tests will all fail with connection errors, but the root cause won't be clearly attributed to warmup failure. — severity: low

#### Category summaries

| Category | Blocking | High | Medium | Low | Status |
|---|---|---|---|---|---|
| 1. Repository layout | 0 | 0 | 0 | 0 | Clean |
| 2. Secrets | 0 | 0 | 0 | 0 | Clean |
| 3. Module boundaries | 0 | 0 | 0 | 0 | Clean |
| 4. API & auth | 0 | 0 | 0 | 0 | RESOLVED |
| 5. Models & migrations | 0 | 0 | 0 | 0 | Clean (1 accepted) |
| 6. Config & logging | 0 | 0 | 0 | 0 | RESOLVED |
| 7. External services | 0 | 0 | 0 | 0 | RESOLVED |
| 8. Backend tests | 0 | 0 | 0 | 0 | Clean |
| 9. Frontend boundaries | 0 | 0 | 0 | 0 | RESOLVED |
| 10. Frontend API & types | 0 | 0 | 0 | 0 | RESOLVED |
| 11. Proxy & routing | 0 | 0 | 0 | 0 | Clean |
| 12. OpenAPI | 0 | 0 | 0 | 0 | Clean |
| 13. Docker | 0 | 0 | 0 | 0 | Clean (1 resolved) |
| 14. E2E | 0 | 0 | 0 | 0 | Clean (1 resolved, 1 uncertain) |
| **Total** | **0** | **0** | **0** | **0** | **All resolved** |


