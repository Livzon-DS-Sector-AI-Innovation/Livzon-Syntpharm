# AI Audit Findings

## Baseline (commit: to be filled, date: 2025-07-25)

---

### Category 1: Repository layout

| Files inspected | ~30 (all directories via listing) |
| Files not inspected | 0 |
| Rules evaluated | 9 (Q1-Q9 covering all listed rules) |
| Rules not evaluated | 1 (training template dir presence — confirmed, not audited in depth) |
| Confirmed findings | 0 |
| Uncertain findings | 1 |
| Status | complete |

#### Confirmed
_None._

#### Uncertain
- [ ] `backend/scripts/run_edbo.py` — 仓库组织/脚本 — Standalone script in `scripts/` root, not in a purpose-specific subdirectory (ci/seed/migration/sync/import/test/regulatory_poc). May belong in `scripts/test/` or could be intentionally kept at root as an EDBO+ runner. — severity: low

#### Accepted exceptions
_None yet._

---

### Category 2: Secrets and hardcoded values

| Files inspected | ~200 (grep scans across backend/app, frontend/src, nginx, Docker) |
| Files not inspected | 0 |
| Rules evaluated | 9 (all Q1-Q9) |
| Rules not evaluated | 0 |
| Confirmed findings | 1 |
| Uncertain findings | 1 |
| Status | complete |

#### Confirmed
- [ ] `.env.example:111` — 后端/LLM_ENCRYPTION_KEY — `LLM_ENCRYPTION_KEY=change-me-in-production` is present in `.env.example`. AGENTS.md prohibits: "LLM_ENCRYPTION_KEY 必须存放在部署环境变量中，不进入 .env.example". — severity: blocking

#### Uncertain
- [ ] `backend/app/core/config.py:265-266` — 仓库通用规则/禁止硬编码绝对路径 — Hardcoded Windows paths `C:\Program Files\LibreOffice\program\soffice.exe`. These are in `core/config.py` (the configuration layer), so they're in the correct file. However, they are hardcoded string literals rather than sourced from environment variables. — severity: low

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
| Confirmed findings | 1 |
| Uncertain findings | 1 |
| Status | complete |

#### Confirmed
- [ ] `backend/app/modules/research/repository.py:636,701,713,725,741` — API 规范/必须: 业务异常使用 app/core/exceptions.py — Repository layer raises raw `HTTPException(status_code=404)` instead of domain exceptions. Repositories must not depend on HTTP. Return `None` or raise domain-level exceptions; let API/service layer convert to HTTP responses. Also a module boundary violation (repository depends on `fastapi.HTTPException`). — severity: blocking

#### Uncertain
- [ ] `backend/app/modules/safety/api/files.py:127,134` — API 规范/必须 — Uses raw `HTTPException(status_code=404)` in API layer. The project provides `NotFoundException(resource, id)` in `app.core.exceptions`. This is in an API file (acceptable layer), but should use project exception classes for consistency. — severity: low

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
| Confirmed findings | 3 |
| Uncertain findings | 0 |
| Status | complete |

#### Confirmed
- [ ] `frontend/src/app/(dashboard)/settings/page.tsx` — Server Component vs Client Component — Directly imports `<Result>` from antd and uses it in JSX without `'use client'`. Server Components cannot render antd components. — severity: medium
- [ ] `frontend/src/app/(dashboard)/hr/training/ledger/page.tsx` — Server Component vs Client Component — Directly imports from antd without `'use client'`. — severity: medium
- [ ] `frontend/src/app/(dashboard)/hr/training/annual-plan/page.tsx` — Server Component vs Client Component — Directly imports from antd without `'use client'`. — severity: medium

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
| 1. Repository layout | complete | 0 | 1 |
| 2. Secrets and hardcoded values | complete | 1 | 1 |
| 3. Backend module boundaries | complete | 0 | 1 |
| 4. API and authentication | complete | 1 | 1 |
| 5. Models and migrations | complete | 0 | 0 |
| 6. Configuration and logging | complete | 0 | 0 |
| 7. External services and background tasks | complete | 0 | 0 |
| 8. Backend tests | complete | 0 | 0 |
| 9. Frontend component boundaries | complete | 3 | 0 |
| 10. Frontend API and generated types | complete | 0 | 0 |
| 11. Proxy and routing | complete | 0 | 0 |
| 12. Cross-project OpenAPI | complete | 0 | 0 |
| 13. Docker and deployment | complete | 0 | 0 |
| 14. E2E | complete | 0 | 0 |
| **Total** | **14/14 complete** | **5** | **4** |

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
