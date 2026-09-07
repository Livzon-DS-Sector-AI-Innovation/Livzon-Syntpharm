# 46.9 — Fix exhaustive-deps in Safety special ops components

**What to build:** Fix all React hooks dependency warnings in Safety special operations components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] safety/SpecialOpsLedger.tsx has no exhaustive-deps warnings
- [ ] safety/SpecialOpsManagement.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
