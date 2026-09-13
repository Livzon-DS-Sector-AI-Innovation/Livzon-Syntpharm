# 45.18 — Fix exhaustive-deps in Safety hazard components

**What to build:** Fix all React hooks dependency warnings in Safety hazard-related components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] safety/HazardLedgerPage.tsx has no exhaustive-deps warnings
- [x] safety/HazardLedgerPanel.tsx has no exhaustive-deps warnings
- [x] safety/HazardSelectModal.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- HazardLedgerPage.tsx: Wrapped loadData in useCallback with [hazardQueryParams, statusFilter, typeFilter, levelFilter, categoryFilter, inspectionCategoryFilter, deptFilter, sortField, sortOrder, msgApi, setHazards, setHazardTotal] dependencies
- HazardLedgerPanel.tsx: Wrapped loadData in useCallback with [queryParams, department, position, riskLevel, dateRange, sortField, sortOrder, msgApi] dependencies
- HazardLedgerPanel.tsx: Wrapped loadStats in useCallback with [department, position, riskLevel, dateRange] dependencies
- HazardSelectModal.tsx: Wrapped loadData in useCallback with [keyword, department, page, message] dependencies
- Added all wrapped functions to useEffect dependency arrays
- All exhaustive-deps warnings resolved in all three files
