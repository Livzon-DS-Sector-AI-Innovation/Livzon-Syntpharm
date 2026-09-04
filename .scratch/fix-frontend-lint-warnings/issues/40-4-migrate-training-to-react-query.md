# 40.4 — Migrate training module to React Query

**What to build:** Training list page uses React Query for data fetching, Zustand store manages only UI state. Remove duplicate state management where both useState and store hold the same data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `training/page.tsx`
- [ ] Remove duplicate state from `trainingStore.ts` (keep only UI state like filters, modal visibility)
- [ ] Ensure proper cache invalidation when mutations occur (create, update, delete)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from training module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: training list loads, filters work, CRUD operations succeed
