# 02 — Migrate quality module to canonical React patterns

**What to build:** Eliminate all `set-state-in-effect` warnings in the quality module by migrating CPV/CPP batch data pages and deviation flow pages to React Query and proper state patterns. After this ticket, all quality module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** done

- [x] All `set-state-in-effect` warnings in quality module eliminated (8 → 0)
- [x] CPV/CPP batch data pages use React Query for data fetching
- [x] Deviation flow pages use proper state patterns
- [x] `pnpm typecheck` passes with 0 errors
- [x] `pnpm lint` shows 0 `set-state-in-effect` warnings in quality module
- [ ] Manual smoke test confirms no behavioral regression in quality pages

## Summary of Changes

Successfully migrated 8 files in the quality module to canonical React patterns:

1. **CppBatchDataClient.tsx** - Migrated to React Query, removed useEffect for data fetching
2. **CqaBatchDataClient.tsx** - Migrated to React Query, removed useEffect for data fetching
3. **deviation-automation/preview/[id]/page.tsx** - Migrated to React Query for task and preview data
4. **deviation-automation/templates/page.tsx** - Migrated to React Query with pagination state
5. **deviation-flow/create/page.tsx** - Migrated to React Query, used useMemo for derived values
6. **deviation-flow/progress/page.tsx** - Migrated to React Query, removed unnecessary useEffect
7. **instrument/list/edit/page.tsx** - Migrated to React Query, used useEffect to set form values
8. **static-data/[module]/[id]/page.tsx** - Migrated to React Query, used useState initializer for attachFiles

## Patterns Applied

- **React Query migration**: Replaced `useEffect` + `setState` data fetching with `useQuery` hooks
- **Derived state**: Used `useMemo` to derive values from query data
- **Form initialization**: Used `useEffect` with ref to set form values only once
- **State initialization**: Used useState initializer function to initialize state from query data
- **Direct data usage**: Used query data directly instead of syncing to local state

