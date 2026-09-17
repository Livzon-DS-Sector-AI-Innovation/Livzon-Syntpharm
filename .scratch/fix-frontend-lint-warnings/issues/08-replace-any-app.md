---
title: "Replace any types in src/app/"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - typescript
created: 2026-08-17
blocked_by: ["06-fix-hooks-app"]
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 08 — Replace any types in src/app/

## What to build

After this ticket, all 380 `any` types in `src/app/` are replaced with proper types. Page components, server action parameters, and route handlers use the OpenAPI-generated types and proper TypeScript types.

## Acceptance criteria

- [ ] Replace all 380 `@typescript-eslint/no-explicit-any` warnings in `src/app/`
- [ ] Use OpenAPI-generated types for API response data in page components
- [ ] Type server action parameters and return values properly
- [ ] Use `unknown` + type guards for genuinely dynamic data
- [ ] `pnpm lint` produces 2,290 warnings (down from 2,670)
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] Pages render correctly with proper types

## Notes

Focus on page components and their data fetching patterns. Server actions should have explicit parameter and return types. Use the generated API types where available.
