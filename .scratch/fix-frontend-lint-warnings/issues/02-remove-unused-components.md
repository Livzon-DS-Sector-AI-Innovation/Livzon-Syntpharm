---
title: "Remove unused in src/components/"
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

# 02 — Remove unused in src/components/

## What to build

After this ticket, all unused imports, variables, and type exports in `src/components/` are removed. The directory should have zero `@typescript-eslint/no-unused-vars` warnings.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-unused-vars` warnings in `src/components/`
- [ ] Remove all unused imports, variables, and type exports
- [ ] For unused function parameters, prefix with `_`
- [ ] For unused type exports, verify they're not dynamically referenced before removing
- [ ] No runtime behavior changes

## Notes

**Status update (2026-08-19):** Despite being marked done, `src/components/` still has unused-vars warnings. This ticket needs to be completed.

Current state: `src/components/` has 444 total warnings (mix of any and unused-vars).
