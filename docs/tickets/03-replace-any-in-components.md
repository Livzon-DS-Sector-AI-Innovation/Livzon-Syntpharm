---
title: "Replace any types in src/components/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - typescript
created: 2026-08-14
updated: 2026-08-17
blocked_by: ["02-fix-react-hooks-correctness"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 03 — Replace any types in src/components/

## What to build

After this ticket, all `any` types in `src/components/` are replaced with proper types. Component props, event handlers, and API response types use the OpenAPI-generated types from `lib/api/` and Ant Design's generic type parameters.

## Acceptance criteria

- [ ] Replace all `@typescript-eslint/no-explicit-any` warnings in `src/components/`
- [ ] Use OpenAPI-generated types from `lib/api/server/` for API responses
- [ ] Use Ant Design generic type parameters (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`) for Ant Design components
- [ ] Use `unknown` + type guards for genuinely dynamic data
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] Components render correctly with proper types

## Notes

This is the largest single batch. For table column definitions, use `ColumnsType<YourRecordType>`. For form handlers, use `FormInstance<YourFormValues>`. For event handlers, use the specific event types from React or the library.
