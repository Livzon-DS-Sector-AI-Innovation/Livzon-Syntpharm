# 45.9 — Fix remaining exhaustive-deps warnings

**What to build:** Fix any remaining React hooks dependency warnings that were not covered by tickets 45.1-45.8, including edge cases and integration issues.

**Blocked by:** 45.1, 45.2, 45.3, 45.4, 45.5, 45.6, 45.7, 45.8

**Status:** done

- [x] regulation/generator/page.tsx has no exhaustive-deps warnings
- [x] All other remaining files have no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for all affected files

**Notes:**
Fixed exhaustive-deps warnings in 7 files:
- Added message dependency to useCallback hooks
- Wrapped fetchData in useCallback with proper dependencies
- Added initialValues and form dependencies to useEffect hooks
- Fixed dependency arrays in registration and safety components
