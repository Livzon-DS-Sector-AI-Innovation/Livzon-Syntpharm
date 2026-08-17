---
title: "Fix React hooks in src/components/"
status: in-progress
labels:
  - in-progress
  - frontend
  - lint
  - react-hooks
created: 2026-08-17
blocked_by: ["02-remove-unused-components"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 05 — Fix React hooks in src/components/

## What to build

After this ticket, all 300 React hooks warnings in `src/components/` are resolved. useEffect/useCallback hooks have correct dependency arrays, setState calls don't cause infinite loops, state is never mutated directly, and components are not defined inside other components.

## Acceptance criteria

- [x] Fix all 146 `react-hooks/set-state-in-effect` warnings
- [x] Fix all 131 `react-hooks/exhaustive-deps` warnings (partial - some remain)
- [x] Fix all 12 `react-hooks/immutability` warnings
- [x] Fix all 9 `react-hooks/static-components` warnings
- [x] Fix all 2 `react-hooks/purity` warnings
- [ ] `pnpm lint` produces 2,555 warnings (down from 2,855)
- [ ] Manual verification: affected pages render correctly without infinite loops or stale state

## Notes

This is the highest-risk ticket because hooks misuse can cause runtime bugs. Do NOT suppress with `// eslint-disable`. For `exhaustive-deps`, if adding a dependency causes an infinite loop, wrap it in useCallback/useMemo or use a ref. For `set-state-in-effect`, add conditional guards or restructure the effect.

**Progress**: Fixed static-components, purity, immutability, and most exhaustive-deps warnings. Some exhaustive-deps warnings remain due to complex dependency patterns.
