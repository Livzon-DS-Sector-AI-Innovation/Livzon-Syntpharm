---
title: "Auto-fix prefer-const"
status: done
labels:
  - done
  - frontend
  - lint
created: 2026-08-17
completed: 2026-08-17
blocked_by: []
spec: .scratch/fix-frontend-lint-warnings/spec.md
---

# 01 — Auto-fix prefer-const

## What to build

After this ticket, the 3 `prefer-const` warnings are resolved. Variables that are never reassigned are declared as `const` instead of `let`.

## Acceptance criteria

- [x] Run `pnpm lint --fix` to auto-fix the 3 `prefer-const` warnings
- [x] `pnpm lint` produces 3,294 warnings (down from 3,297)
- [x] No runtime behavior changes — this is purely mechanical

## Notes

Zero risk. This is an auto-fixable change that ESLint handles safely.
