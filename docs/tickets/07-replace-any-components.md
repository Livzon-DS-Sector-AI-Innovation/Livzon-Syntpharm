---
title: "Replace any types in src/components/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - typescript
created: 2026-08-17
blocked_by: ["05-fix-hooks-components"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 07 — Replace any types in src/components/

## What to build

After this ticket, all 519 `any` types in `src/components/` are replaced with proper types. Component props, event handlers, and API response types use the OpenAPI-generated types from `lib/api/` and Ant Design's generic type parameters.

## Acceptance criteria

- [ ] Replace all 519 `@typescript-eslint/no-explicit-any` warnings in `src/components/`
- [ ] Use OpenAPI-generated types from `lib/api/server/` for API responses
- [ ] Use Ant Design generic type parameters (e.g., `ColumnsType<RecordType>`, `FormInstance<Values>`) for Ant Design components
- [ ] Use `unknown` + type guards for genuinely dynamic data
- [ ] `pnpm lint` produces 2,036 warnings (down from 2,555)
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] Components render correctly with proper types

## Notes

This is the largest single batch. For table column definitions, use `ColumnsType<YourRecordType>`. For form handlers, use `FormInstance<YourFormValues>`. For event handlers, use the specific event types from React or the library.
