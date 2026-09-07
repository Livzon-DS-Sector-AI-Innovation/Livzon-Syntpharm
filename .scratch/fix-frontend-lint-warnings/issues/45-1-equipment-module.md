# 45.1 — Fix exhaustive-deps in Equipment module

**What to build:** Fix all React hooks dependency warnings in the Equipment module so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] WorkOrderDrawer.tsx has no exhaustive-deps warnings
- [ ] InspectionRoutesTab.tsx has no exhaustive-deps warnings
- [ ] InspectionTasksTab.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for equipment module files
