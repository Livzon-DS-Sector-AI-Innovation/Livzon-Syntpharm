---
title: "Replace any in remaining directories"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by:
  - 04-remove-unused-remaining
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 09 — Replace any in remaining directories

## What to build

After this ticket, all `@typescript-eslint/no-explicit-any` warnings in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/` are resolved. All `any` types are replaced with proper types.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-explicit-any` warnings in:
  - `src/lib/`
  - `src/actions/`
  - `src/types/`
  - `src/stores/`
  - `e2e/`
- [ ] Replace `any` with proper types
- [ ] For API functions, use proper request/response types
- [ ] For utility functions, use proper parameter and return types
- [ ] No runtime behavior changes

## Notes

**Updated count (2026-08-19):** These directories have the following total warnings:
- `src/lib/`: 44
- `src/actions/`: 29
- `src/types/`: 18
- `src/stores/`: 5
- `e2e/`: 2

The exact count of `any` warnings needs to be determined by running lint with a filter.

**Blocked by:** Ticket 04 must complete first to avoid merge conflicts.
