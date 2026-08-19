---
title: "Replace any in src/components/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
updated: 2026-08-19
blocked_by:
  - 02-remove-unused-components
  - 05-fix-hooks-components
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 07 — Replace any in src/components/

## What to build

After this ticket, all `@typescript-eslint/no-explicit-any` warnings in `src/components/` are resolved. All `any` types are replaced with proper types.

## Acceptance criteria

- [ ] Run `pnpm lint` and verify zero `@typescript-eslint/no-explicit-any` warnings in `src/components/`
- [ ] Replace `any` with proper types in component files
- [ ] Use Ant Design generic type parameters where applicable (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`)
- [ ] For event handlers, use proper event types (e.g., `React.ChangeEvent<HTMLInputElement>`)
- [ ] For API responses, use generated types from `src/types/generated/`
- [ ] No runtime behavior changes

## Notes

**Updated count (2026-08-19):** `src/components/` has 444 total warnings. The exact count of `any` warnings needs to be determined by running lint with a filter.

**Blocked by:** Tickets 02 and 06 must complete first to avoid merge conflicts.
