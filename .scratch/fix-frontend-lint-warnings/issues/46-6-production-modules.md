# 46.6 — Fix exhaustive-deps in Production modules

**What to build:** Fix all React hooks dependency warnings in Production components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] production/AnnualReviewTab.tsx has no exhaustive-deps warnings
- [ ] production/WorkshopRankingTrend.tsx has no exhaustive-deps warnings
- [ ] production/pressure/PressureManualInputPageClient.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
