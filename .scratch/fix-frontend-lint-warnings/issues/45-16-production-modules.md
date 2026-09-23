# 45.16 — Fix exhaustive-deps in Production modules

**What to build:** Fix all React hooks dependency warnings in Production components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] production/AnnualReviewTab.tsx has no exhaustive-deps warnings
- [x] production/WorkshopRankingTrend.tsx has no exhaustive-deps warnings
- [x] production/pressure/PressureManualInputPageClient.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- AnnualReviewTab.tsx: Wrapped loadData in useCallback with [year] dependency, moved before useEffect, added to dependency array
- WorkshopRankingTrend.tsx: Added useCallback import, wrapped loadData in useCallback with [year] dependency, moved before useEffect, added to dependency array
- PressureManualInputPageClient.tsx: Wrapped loadPoints in useCallback with [area, timeSlots, message] dependencies, moved before useEffect, added to dependency array
- All exhaustive-deps warnings resolved in all three files
