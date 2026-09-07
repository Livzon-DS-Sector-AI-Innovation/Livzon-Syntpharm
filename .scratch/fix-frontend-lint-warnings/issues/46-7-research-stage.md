# 46.7 — Fix exhaustive-deps in Research StageModuleLayout

**What to build:** Fix all React hooks dependency warnings in Research stage module layout component so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] research/StageModuleLayout.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for this file
