# 40 — Migrate safety data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in safety pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** blocked

**Note:** This ticket requires comprehensive refactoring of the safety module's state management. The safety module has complex interdependencies with Zustand store and requires careful coordination between local component state and global store state. Multiple migration attempts have been made but reverted due to:

1. Duplicate variable declarations when both useState and useQuery are used
2. Complex state synchronization between component state and Zustand store
3. Multiple setRecord/setData calls throughout the component lifecycle
4. Interdependencies between different data loading functions

**Recommended approach:** 
- First refactor the Zustand store to remove data that should be managed by React Query
- Then migrate data fetching to useQuery
- Ensure proper cache invalidation when mutations occur
- Consider using React Query's optimistic updates for better UX

This ticket should be tackled as a separate, larger refactoring effort rather than as part of the lint warning fixes.

- [ ] All data fetching in safety pages uses useQuery/useMutation
- [ ] Loading/error state managed by React Query
- [ ] No useEffect + setState patterns for data fetching
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in safety)
- [ ] Manual smoke test: safety pages load data correctly
