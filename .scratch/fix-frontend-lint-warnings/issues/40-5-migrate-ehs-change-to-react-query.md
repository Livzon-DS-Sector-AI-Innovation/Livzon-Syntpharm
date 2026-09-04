# 40.5 — Migrate EHS change module to React Query

**What to build:** EHS change management page uses React Query for data fetching. This is a larger file (1067 lines) with complex workflow actions.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `ehs-change/page.tsx`
- [ ] Remove duplicate state from `ehsChangeStore.ts` (keep only UI state like filters, modal visibility)
- [ ] Ensure proper cache invalidation when mutations occur (create, update, submit, approve, reject, close)
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from EHS change module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: EHS change list loads, filters work, workflow actions succeed
