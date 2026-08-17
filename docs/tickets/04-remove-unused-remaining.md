---
title: "Remove unused code in remaining directories"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
blocked_by: ["01-auto-fix-prefer-const"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 04 — Remove unused code in remaining directories

## What to build

After this ticket, all 240 unused imports, variables, and type exports in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/` are removed. These directories are clean of `no-unused-vars` warnings.

## Acceptance criteria

- [ ] Remove all unused imports in `src/lib/` (89 warnings)
- [ ] Remove all unused imports in `src/actions/` (114 warnings)
- [ ] Remove all unused imports in `src/types/` (19 warnings)
- [ ] Remove all unused imports in `src/stores/` (17 warnings)
- [ ] Remove all unused imports in `e2e/` (1 warning)
- [ ] Remove unused variables or prefix with `_` if intentionally unused
- [ ] Remove unused type exports or prefix with `_`
- [ ] `pnpm lint` produces 3,054 warnings (down from 3,294)
- [ ] No runtime behavior changes — this is purely cleanup

## Notes

For unused function parameters, prefix with `_` (e.g., `_id`, `_operator`). For unused type exports, verify they're not dynamically referenced before removing.
