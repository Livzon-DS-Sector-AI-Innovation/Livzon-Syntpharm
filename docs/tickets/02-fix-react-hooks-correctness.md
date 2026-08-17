---
title: "Fix React hooks correctness"
status: ready-for-agent
labels:
  - ready-for-agent
  - frontend
  - lint
  - react-hooks
created: 2026-08-14
updated: 2026-08-17
blocked_by: ["01-auto-fix-and-remove-unused"]
spec: docs/specs/fix-frontend-lint-warnings.md
---

# 02 — Fix React hooks correctness

## What to build

After this ticket, all 445 React hooks warnings are resolved. useEffect/useCallback hooks have correct dependency arrays, setState calls don't cause infinite loops, state is never mutated directly, and components are not defined inside other components.

## Acceptance criteria

- [ ] Fix all 182 `react-hooks/exhaustive-deps` warnings by adding missing dependencies or wrapping in useCallback/useMemo
- [ ] Fix all 222 `react-hooks/set-state-in-effect` warnings by refactoring useEffect callbacks to avoid infinite re-render loops
- [ ] Fix all 28 `react-hooks/immutability` warnings by replacing direct state mutations with immutable updates
- [ ] Fix all 10 `react-hooks/static-components` warnings by extracting components to module scope
- [ ] Fix all 2 `react-hooks/purity` warnings by removing side effects from render functions
- [ ] Fix the 1 `react-hooks/rules-of-hooks` warning by moving the hook call to the top level
- [ ] `pnpm lint` produces exactly 1,691 warnings (down from 2,136)
- [ ] Manual verification: affected pages render correctly without infinite loops or stale state

## Notes

This is the highest-risk ticket because hooks misuse can cause runtime bugs. Do NOT suppress with `// eslint-disable`. For `exhaustive-deps`, if adding a dependency causes an infinite loop, wrap it in useCallback/useMemo or use a ref. For `set-state-in-effect`, add conditional guards or restructure the effect.
