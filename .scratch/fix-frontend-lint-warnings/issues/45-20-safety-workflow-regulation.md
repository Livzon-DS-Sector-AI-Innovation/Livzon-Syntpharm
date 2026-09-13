# 45.20 — Fix exhaustive-deps in Safety workflow and regulation

**What to build:** Fix all React hooks dependency warnings in Safety workflow, hazard detail, regulation, and SOP editor components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] safety/WorkflowListPanel.tsx has no exhaustive-deps warnings
- [x] safety/hazard-identification/HazardIdentificationDetailPageClient.tsx has no exhaustive-deps warnings
- [x] safety/hazard/HazardDetailPageClient.tsx has no exhaustive-deps warnings
- [x] safety/regulation/SafetyRegulationPageClient.tsx has no exhaustive-deps warnings
- [x] safety/SopContentEditor.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- WorkflowListPanel.tsx: Wrapped loadData in useCallback with [queryParams, statusFilter, progressFilter, deptFilter, activeBatchId, sortField, sortOrder, msgApi] dependencies
- HazardIdentificationDetailPageClient.tsx: Wrapped loadRecord in useCallback with [id, message, router] dependencies
- HazardDetailPageClient.tsx: Wrapped loadRecord in useCallback with [id, message, router] dependencies
- SafetyRegulationPageClient.tsx: Wrapped loadRegulations in useCallback with [regulationQueryParams, regSearchText, positionFilter, statusFilter, setRegulations, setRegulationTotal] dependencies
- SafetyRegulationPageClient.tsx: Wrapped loadRevisions in useCallback with [revisionQueryParams, typeFilter, scopeFilter, opinionFilter, setRevisions, setRevisionTotal] dependencies
- SopContentEditor.tsx: Added 'message' to useCallback dependency arrays for handleRevert, handleSave, handleExport, handleSaveAndExport
- SopContentEditor.tsx: Wrapped render functions (renderTableChapter, renderCh2, renderCh6, renderCh7, renderCh9) in useCallback with [handleChapterChange, collapsedKeys, toggleCollapse] dependencies
- SopContentEditor.tsx: Removed unnecessary dependencies (chapters, collapsedKeys) from renderChapterContent useCallback
- All exhaustive-deps warnings resolved in all five files
