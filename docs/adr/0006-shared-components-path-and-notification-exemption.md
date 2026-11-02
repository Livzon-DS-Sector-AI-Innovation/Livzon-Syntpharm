# ADR-006: Fix the shared-components path and scope the fire-and-forget exemption

## Status

Accepted — approved by the project owner on 2026-10-31, together with the instruction to
resolve every open audit finding in the current PR.

## Context

Two governance documents described the frontend shared-component directory as
`frontend/src/components/shared/`:

- `AGENTS.md` (the standard every AI assistant must follow)
- `docs/ai-audit-plan.md` (the 15-category audit plan, which is also protected)

That directory does not exist. The repository has `frontend/src/components/common/`, which
holds `BoundaryResult`, `DataUnavailable` and the other cross-module components. Three
consequences follow:

1. A developer following `AGENTS.md` writes `@/components/shared/...` imports that cannot
   resolve.
2. The "protected files" list (`src/components/shared/` 下所有文件) protects a path that
   nothing lives in, so the real shared components are unprotected.
3. Audit category 1 asks whether `frontend/src/` follows the documented structure. Code and
   document disagreed, so the category cannot pass while the document stays wrong.

Separately, audit category 7 flagged `app.core.tasks.spawn_task(...)` call sites as
"`asyncio.create_task` for business logic". Most of them — 15 in `safety` — send Feishu
messages inside loops. They write no business tables, carry no state, and losing one message
only delays a notice. Turning each of them into a queued job would add one `core.background_jobs`
row per recipient for a delivery that is already best-effort. What was missing was not code,
it was a written boundary for that case.

## Decision

**1. `components/common/` is the canonical path.** `AGENTS.md`, `docs/ai-audit-plan.md`
(directory sketch, protected-file list, and the category-1 question) now name it. `AGENTS.md`
keeps one line recording that `components/shared/` is a historical name that no longer exists,
so older references can be recognised instead of copied.

**2. Fire-and-forget stays legal, but only for pure notification.** `AGENTS.md` 异步任务 gains a
narrow exemption. It applies only when all three hold:

- no business table is written and no business state changes; failure degrades to "message not
  delivered";
- `app/core/tasks.py:spawn_task()` is used (exceptions reach the log), never a bare
  `asyncio.create_task()`;
- anything that needs retry, delivery status, or is bound to business state uses
  `app/core/jobs.py:submit_job_safe()` instead.

The one call site that owns business state — `equipment/api/claim.py`, which notifies a claimer
after a work order has been taken — was moved to `submit_job_safe()` rather than exempted.

## Consequences

- Imports in new frontend code resolve, and the protected-file list now covers files that exist.
- `components/common/` is now under the same "architecture approval required" rule that
  `components/shared/` was meant to have. Adding a component there is no longer a free action.
- The 15 `safety` notification sites stay as they are; the exemption is written down and bounded,
  so a future reviewer can reject a call that fails any of the three conditions.
- Old references to `components/shared/` in unrelated notes remain; they are documentation drift,
  not a second standard.