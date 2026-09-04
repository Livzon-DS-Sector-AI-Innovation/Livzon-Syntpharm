# 40.2 — Migrate check module to React Query

**What to build:** Safety check list page uses React Query for data fetching, Zustand store manages only UI state. Remove duplicate state management where both useState and store hold the same data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `check/page.tsx`
- [ ] Remove duplicate state from `checkStore.ts` (keep only UI state like filters, modal visibility)
- [ ] Ensure proper cache invalidation when mutations occur (create, update, delete, submit, review)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from check module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: check list loads, filters work, CRUD operations succeed
