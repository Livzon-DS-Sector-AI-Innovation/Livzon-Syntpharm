# 05 — Migrate HR module to canonical React patterns

**What to build:** Eliminate all 2 `set-state-in-effect` warnings in the HR module by migrating training select and session detail pages to proper React patterns. After this ticket, all HR module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All 2 `set-state-in-effect` warnings in HR module eliminated (2 → 0)
- [x] Training select page uses React Query for data fetching
- [x] Session detail page uses initialValues and useMemo for form initialization
- [x] `pnpm typecheck` passes with 0 errors
- [x] `pnpm lint` shows 0 `set-state-in-effect` warnings in HR module
- [ ] Manual smoke test confirms no behavioral regression in HR pages

## Summary of Changes

Successfully migrated 2 files in the HR module to canonical React patterns:

1. **TrainingSelectClient.tsx** - Migrated departments and employees fetching to React Query
2. **TrainingSessionDetailModal.tsx** - Refactored form initialization to use initialValues and useMemo

## Patterns Applied

- **React Query migration**: Replaced `useEffect` + `setState` data fetching with `useQuery` hooks
- **Form initialization**: Used `initialValues` prop and `useMemo` to compute initial form values
- **Derived state**: Used `useMemo` to compute values from props instead of storing in state

