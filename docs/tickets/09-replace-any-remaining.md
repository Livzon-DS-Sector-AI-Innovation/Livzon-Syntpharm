---
title: "Replace any types in remaining directories"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - typescript
created: 2026-08-17
blocked_by: ["04-remove-unused-remaining"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 09 — Replace any types in remaining directories

## What to build

After this ticket, all 754 `any` types in `src/lib/`, `src/actions/`, `src/types/`, `src/stores/`, and `e2e/` are replaced with proper types. Utility functions, server actions, type definitions, stores, and test helpers use proper TypeScript types.

## Acceptance criteria

- [ ] Replace all 589 `any` warnings in `src/lib/` (utility functions, API helpers)
- [ ] Replace all 126 `any` warnings in `src/actions/` (server action return types and parameters)
- [ ] Replace all 35 `any` warnings in `src/types/` (type definitions)
- [ ] Replace the 1 `any` warning in `src/stores/` (Zustand stores)
- [ ] Replace the 3 `any` warnings in `e2e/` (test helpers)
- [ ] `pnpm lint` produces 0 warnings (down from 3,054)
- [ ] TypeScript compilation succeeds with `pnpm typecheck`
- [ ] All modules work correctly with proper types

## Notes

This is the final cleanup pass. For `src/types/`, some types may be unused — verify before replacing. For `src/stores/`, ensure Zustand store state and actions are properly typed. For `e2e/`, test helpers can use `unknown` with type assertions where needed.
