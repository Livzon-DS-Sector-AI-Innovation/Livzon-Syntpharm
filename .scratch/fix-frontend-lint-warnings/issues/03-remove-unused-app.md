---
title: "Remove unused in src/app/"
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

# 03 — Remove unused in src/app/

## What to build

After this ticket, all unused imports, variables, and type exports in `src/app/` are removed. The directory should have zero `@typescript-eslint/no-unused-vars` warnings.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-unused-vars` warnings in `src/app/`
- [ ] Remove all unused imports, variables, and type exports
- [ ] For unused function parameters, prefix with `_`
- [ ] For unused type exports, verify they're not dynamically referenced before removing
- [ ] No runtime behavior changes

## Notes

**Status update (2026-08-19):** Despite being marked done, `src/app/` still has unused-vars warnings. This ticket needs to be completed.

Current state: `src/app/` has 197 total warnings (mix of any and unused-vars).
