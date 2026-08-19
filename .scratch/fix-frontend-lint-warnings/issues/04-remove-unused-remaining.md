---
title: "Remove unused in remaining directories"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by: []
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 04 — Remove unused in remaining directories

## What to build

After this ticket, all unused imports, variables, and type exports in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/` are removed. These directories should have zero `@typescript-eslint/no-unused-vars` warnings.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-unused-vars` warnings in:
  - `src/lib/`
  - `src/actions/`
  - `src/types/`
  - `src/stores/`
  - `e2e/`
- [ ] Remove all unused imports, variables, and type exports
- [ ] For unused function parameters, prefix with `_`
- [ ] For unused type exports, verify they're not dynamically referenced before removing
- [ ] No runtime behavior changes

## Notes

**Status update (2026-08-19):** Despite being marked done, these directories still have unused-vars warnings. This ticket needs to be completed.

Current state:
- `src/lib/`: 44 total warnings
- `src/actions/`: 29 total warnings
- `src/types/`: 18 total warnings
- `src/stores/`: 5 total warnings
- `e2e/`: 2 total warnings
