---
title: "Replace any types in remaining areas"
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

# 05 — Replace any types in remaining areas

## What to build

After this ticket, all `any` types in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/` are replaced with proper types. Utility functions, server actions, type definitions, stores, and test helpers use proper TypeScript types.

## Acceptance criteria

- [ ] Replace all `any` warnings in `src/lib/` (utility functions, API helpers)
- [ ] Replace all `any` warnings in `src/actions/` (server action return types and parameters)
- [ ] Replace all `any` warnings in `src/types/` (type definitions)
- [ ] Replace all `any` warnings in `src/stores/` (Zustand stores)
- [ ] Replace all `any` warnings in `e2e/` (test helpers)
- [ ] `pnpm lint` produces exactly 0 warnings (down from 1,691)
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] All modules work correctly with proper types

## Notes

This is the final cleanup pass. For `src/types/`, some types may be unused — verify before replacing. For `src/stores/`, ensure Zustand store state and actions are properly typed. For `e2e/`, test helpers can use `unknown` with type assertions where needed.
