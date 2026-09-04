# 40.7 — Migrate occupational health module to React Query

**What to build:** Occupational health page with two data sources (monitors + exams) uses React Query. This is a large file (1412 lines) with tabbed interface managing two separate data sets.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Replace useEffect+useState data fetching with useQuery in `occupational-health/page.tsx`
- [ ] Remove duplicate state from `ohHazardMonitorStore.ts` and `ohHealthExamStore.ts` (keep only UI state)
- [ ] Implement separate useQuery hooks for monitors and exams with independent queryKeys
- [ ] Ensure proper cache invalidation for both data sources when mutations occur
- [ ] Remove all `@typescript-eslint/no-set-state-in-effect` warnings from occupational health module
- [ ] `tsc --noEmit` passes with no errors
- [ ] Manual smoke test: both monitors and exams tabs load, filters work, CRUD operations succeed
