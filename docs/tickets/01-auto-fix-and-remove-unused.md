---
title: "Auto-fix and remove unused code"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-14
updated: 2026-08-17
blocked_by: []
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 01 — Auto-fix and remove unused code

## What to build

After this ticket, running `pnpm lint` produces ~2,136 warnings instead of 3,297. All auto-fixable issues are resolved, and all unused imports, variables, and type exports are removed.

## Acceptance criteria

- [ ] Run `pnpm lint --fix` to auto-fix `prefer-const` and other auto-fixable warnings
- [ ] Remove all unused imports across the codebase (1,158 warnings)
- [ ] Remove unused variables or prefix with `_` if intentionally unused
- [ ] Remove unused type exports in `src/types/` or prefix with `_`
- [ ] `pnpm lint` produces exactly 2,136 warnings (down from 3,297)
- [ ] No runtime behavior changes — this is purely cleanup

## Notes

This is a mechanical pass. For unused function parameters, prefix with `_` (e.g., `_id`, `_operator`). For unused type exports, verify they're not dynamically referenced before removing.
