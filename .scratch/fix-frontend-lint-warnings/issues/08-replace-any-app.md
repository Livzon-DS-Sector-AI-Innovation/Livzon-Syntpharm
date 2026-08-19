---
title: "Replace any in src/app/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by:
  - 03-remove-unused-app
  - 06-fix-hooks-app
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 08 — Replace any in src/app/

## What to build

After this ticket, all `@typescript-eslint/no-explicit-any` warnings in `src/app/` are resolved. All `any` types are replaced with proper types.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-explicit-any` warnings in `src/app/`
- [ ] Replace `any` with proper types in page and layout files
- [ ] Use Ant Design generic type parameters where applicable
- [ ] For event handlers, use proper event types
- [ ] For API responses, use generated types from `src/types/generated/`
- [ ] No runtime behavior changes

## Notes

**Updated count (2026-08-19):** `src/app/` has 197 total warnings. The exact count of `any` warnings needs to be determined by running lint with a filter.

**Blocked by:** Tickets 03 and 06 must complete first to avoid merge conflicts.
