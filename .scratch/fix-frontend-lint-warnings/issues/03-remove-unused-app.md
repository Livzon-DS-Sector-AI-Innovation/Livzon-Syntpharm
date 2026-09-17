---
title: "Remove unused code in src/app/"
status: done
labels:
  - done
  - frontend
  - lint
created: 2026-08-17
completed: 2026-08-17
blocked_by: ["01-auto-fix-prefer-const"]
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 03 — Remove unused code in src/app/

## What to build

After this ticket, all 479 unused imports, variables, and type exports in `src/app/` are removed. The directory is clean of `no-unused-vars` warnings.

## Acceptance criteria

- [x] Remove all unused imports in `src/app/` (479 warnings)
- [x] Remove unused variables or prefix with `_` if intentionally unused
- [x] Remove unused type exports or prefix with `_`
- [x] `pnpm lint` produces 2,815 warnings (down from 3,294)
- [x] No runtime behavior changes — this is purely cleanup

## Notes

For unused function parameters, prefix with `_` (e.g., `_id`, `_operator`). For unused type exports, verify they're not dynamically referenced before removing.
