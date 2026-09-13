# 40 — Migrate safety data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in safety pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** done

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

**Completed sub-tickets:**
- 40.1: Migrate accident module to React Query
- 40.2: Migrate check module to React Query
- 40.3: Migrate contractor module to React Query
- 40.4: Migrate training module to React Query
- 40.5: Migrate ehs-change module to React Query
- 40.6: Migrate knowledge-base module to React Query
- 40.7: Migrate occupational-health module to React Query
- 40.8: Migrate regulation module to React Query
- 40.9: Migrate hazard detail to React Query
- 40.10: Migrate hazard identification module to React Query

- [x] All data fetching in safety pages uses useQuery/useMutation
- [x] Loading/error state managed by React Query
- [x] No useEffect + setState patterns for data fetching
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-set-state-in-effect warnings in safety)
- [x] Manual smoke test: safety pages load data correctly
