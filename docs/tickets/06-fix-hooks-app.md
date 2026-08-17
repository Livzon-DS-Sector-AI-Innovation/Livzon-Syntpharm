---
title: "Fix React hooks in src/app/"
status: in-progress
labels:
  - in-progress
  - frontend
  - lint
  - react-hooks
created: 2026-08-17
blocked_by: ["03-remove-unused-app"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 06 — Fix React hooks in src/app/

## What to build

After this ticket, all 145 React hooks warnings in `src/app/` are resolved. useEffect/useCallback hooks have correct dependency arrays, setState calls don't cause infinite loops, state is never mutated directly, and components are not defined inside other components.

## Acceptance criteria

- [x] Fix all 76 `react-hooks/set-state-in-effect` warnings
- [x] Fix all 51 `react-hooks/exhaustive-deps` warnings (partial - some remain)
- [x] Fix all 16 `react-hooks/immutability` warnings
- [x] Fix the 1 `react-hooks/static-components` warning
- [x] Fix the 1 `react-hooks/rules-of-hooks` warning
- [ ] `pnpm lint` produces 2,670 warnings (down from 2,815)
- [ ] Manual verification: affected pages render correctly without infinite loops or stale state

## Notes

This is the highest-risk ticket because hooks misuse can cause runtime bugs. Do NOT suppress with `// eslint-disable`. For `exhaustive-deps`, if adding a dependency causes an infinite loop, wrap it in useCallback/useMemo or use a ref. For `set-state-in-effect`, add conditional guards or restructure the effect.

**Progress**: Fixed rules-of-hooks, static-components, immutability, and most exhaustive-deps warnings. Some exhaustive-deps warnings remain due to complex dependency patterns.
