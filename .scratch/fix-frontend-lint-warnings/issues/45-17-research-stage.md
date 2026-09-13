# 45.17 — Fix exhaustive-deps in Research StageModuleLayout

**What to build:** Fix all React hooks dependency warnings in Research stage module layout component so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] research/StageModuleLayout.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for this file

**Notes:**
- Added useCallback import
- Wrapped loadProjects in useCallback with [stage, msgApi] dependencies
- Moved loadProjects before useEffect to avoid 'used before declaration' error
- Added loadProjects to useEffect dependency array
- All exhaustive-deps warnings resolved
