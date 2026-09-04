# 40.1 — Migrate accident module to React Query

**What to build:** Accident list page uses React Query for data fetching, Zustand store only manages UI state (filters, modals). Remove duplicate state management where both useState and store hold the same data.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `accident/page.tsx`
- [ ] Remove duplicate state from `accidentStore.ts` (keep only UI state like filters, modal visibility)
- [ ] Ensure proper cache invalidation when mutations occur (create, update, delete)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from accident module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: accident list loads, filters work, CRUD operations succeed
