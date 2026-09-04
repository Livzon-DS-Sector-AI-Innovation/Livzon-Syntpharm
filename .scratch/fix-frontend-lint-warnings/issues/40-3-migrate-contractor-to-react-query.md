# 40.3 — Migrate contractor module to React Query

**What to build:** Contractor management page uses React Query for data fetching. This is the smallest file (210 lines) and serves as a good starting point for the migration pattern.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `contractor/page.tsx`
- [ ] Remove duplicate state from `contractorStore.ts` (keep only UI state like filters, modal visibility)
- [ ] Ensure proper cache invalidation when mutations occur (create, update, delete, blacklist, activate)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from contractor module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: contractor list loads, filters work, CRUD operations succeed
