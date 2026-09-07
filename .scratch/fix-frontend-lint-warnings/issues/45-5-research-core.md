# 45.5 — Fix exhaustive-deps in Research module (Part 1)

**What to build:** Fix all React hooks dependency warnings in the Research module core pages so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] DeliverableTemplatePage.tsx has no exhaustive-deps warnings
- [ ] ProjectTable.tsx has no exhaustive-deps warnings
- [ ] ReportModulePage.tsx has no exhaustive-deps warnings
- [ ] StatsPage.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
