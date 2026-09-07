# 45.14 — Fix exhaustive-deps in Energy DeviceDrawer

**What to build:** Fix all React hooks dependency warnings in Energy device drawer component so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] energy/DeviceDrawer.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for this file
