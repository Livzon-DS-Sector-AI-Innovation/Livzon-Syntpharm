# 03 — Migrate research module to canonical React patterns

**What to build:** Eliminate all `set-state-in-effect` warnings in the research module by migrating data fetching to React Query and derived state to useMemo. This covers stage module layout and deliverable template pages. After this ticket, all research module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `set-state-in-effect` warnings in research module eliminated (2 → 0)
- [x] Stage module layout uses React Query and useMemo for filtering
- [x] Deliverable template page uses React Query for data fetching
- [x] `pnpm typecheck` passes with 0 errors
- [x] `pnpm lint` shows 0 `set-state-in-effect` warnings in research module
- [ ] Manual smoke test confirms no behavioral regression in research pages

## Summary of Changes

Successfully migrated 2 files in the research module to canonical React patterns:

1. **DeliverableTemplatePage.tsx** - Migrated to React Query for template data fetching
2. **StageModuleLayout.tsx** - Migrated to React Query for project data, used useMemo for filtered projects

## Patterns Applied

- **React Query migration**: Replaced `useEffect` + `setState` data fetching with `useQuery` hooks
- **Derived state**: Used `useMemo` to compute filtered projects from query data
- **Direct data usage**: Used query data directly instead of syncing to local state

