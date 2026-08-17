---
title: "Remove unused code in src/components/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
blocked_by: ["01-auto-fix-prefer-const"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 02 — Remove unused code in src/components/

## What to build

After this ticket, all 439 unused imports, variables, and type exports in `src/components/` are removed. The directory is clean of `no-unused-vars` warnings.

## Acceptance criteria

- [ ] Remove all unused imports in `src/components/` (439 warnings)
- [ ] Remove unused variables or prefix with `_` if intentionally unused
- [ ] Remove unused type exports or prefix with `_`
- [ ] `pnpm lint` produces 2,855 warnings (down from 3,294)
- [ ] No runtime behavior changes — this is purely cleanup

## Notes

For unused function parameters, prefix with `_` (e.g., `_id`, `_operator`). For unused type exports, verify they're not dynamically referenced before removing.
