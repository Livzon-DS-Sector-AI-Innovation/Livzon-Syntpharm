---
title: "Auto-fix prefer-const"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
created: 2026-08-17
blocked_by: []
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 01 — Auto-fix prefer-const

## What to build

After this ticket, the 3 `prefer-const` warnings are resolved. Variables that are never reassigned are declared as `const` instead of `let`.

## Acceptance criteria

- [ ] Run `pnpm lint --fix` to auto-fix the 3 `prefer-const` warnings
- [ ] `pnpm lint` produces 3,294 warnings (down from 3,297)
- [ ] No runtime behavior changes — this is purely mechanical

## Notes

Zero risk. This is an auto-fixable change that ESLint handles safely.
