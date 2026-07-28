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

### PR #12: lzhc-zhuang — Energy, Safety, Equipment sync (head: lzhc-zhuang, date: 2026-07-28)

Files changed: 281 across categories 1–14 (backend: energy, equipment, quality, safety; frontend: energy, equipment, safety, administration, registration)

#### New findings

- [x] `backend/app/modules/energy/api.py:624` — §4 API & Auth / 认证与权限 — `daily_import_from_bitable()` has no `current_user: CurrentUser` parameter. Per AGENTS.md: "未声明的业务接口按 require_user 处理". — severity: blocking — **RESOLVED** (added `current_user: CurrentUser` parameter)
- [x] `frontend/src/actions/energy.ts` (8 types), `frontend/src/actions/equipment.ts` (4 types) — §10 — 12 API types now use `components["schemas"]["..."]` from generated schema. Local type files now re-export via same pattern. **RESOLVED** for types in OpenAPI.
- [ ] ~18 equipment types still handwritten — need backend Pydantic schemas added to OpenAPI spec before they can be imported from generated schema. Deferred. — severity: medium

#### Category summaries

| Category | New violations | Note |
|---|---|---|
| 1. Repository layout | 0 | |
| 2. Secrets | 0 | LLM_ENCRYPTION_KEY in .env.example is disputed rule, not a violation |
| 3. Module boundaries | 0 | No cross-module direct imports |
| 4. API & auth | 1 | daily_import_from_bitable missing auth (blocking) |
| 5. Models & migrations | 0 | Both migrations use NNNN format |
| 6. Config & logging | 0 | os.environ in converter.py is allowed subprocess exception |
| 7. External services | 0 | asyncio.create_task only in infrastructure |
| 8. Backend tests | 0 | |
| 9. Frontend boundaries | 0 | force-dynamic conflicts resolved |
| 10. Frontend API & types | 1 | Handwritten types in energy/equipment actions |
| 11. Proxy & routing | 0 | proxy.ts unchanged |
| 12. OpenAPI | 0 | CI passes |
| 13. Docker | 0 | nginx timeout + Feishu timeout changes |
| 14. E2E | 0 | CI passes |

