# 45.5 — Fix exhaustive-deps in Research module (Part 1)

**What to build:** Fix all React hooks dependency warnings in the Research module core pages so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] DeliverableTemplatePage.tsx has no exhaustive-deps warnings
- [x] ProjectTable.tsx has no exhaustive-deps warnings
- [x] ReportModulePage.tsx has no exhaustive-deps warnings
- [x] StatsPage.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files
