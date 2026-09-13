# 45.6 — Fix exhaustive-deps in Research module (Part 2)

**What to build:** Fix all React hooks dependency warnings in the Research module workflow components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] ProcessOptimizationWorkflowPage.tsx has no exhaustive-deps warnings
- [x] ModuleResearch.tsx has no exhaustive-deps warnings
- [x] RouteWorkflowPage.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files
