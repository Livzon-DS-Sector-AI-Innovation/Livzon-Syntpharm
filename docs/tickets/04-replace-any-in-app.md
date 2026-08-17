---
title: "Replace any types in src/app/"
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

# 04 — Replace any types in src/app/

## What to build

After this ticket, all `any` types in `src/app/` are replaced with proper types. Page components, server action parameters, and route handlers use the OpenAPI-generated types and proper TypeScript types.

## Acceptance criteria

- [ ] Replace all `@typescript-eslint/no-explicit-any` warnings in `src/app/`
- [ ] Use OpenAPI-generated types for API response data in page components
- [ ] Type server action parameters and return values properly
- [ ] Use `unknown` + type guards for genuinely dynamic data
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] Pages render correctly with proper types

## Notes

Focus on page components and their data fetching patterns. Server actions should have explicit parameter and return types. Use the generated API types where available.
