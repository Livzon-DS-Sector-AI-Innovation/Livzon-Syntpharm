# 46.8 — Fix exhaustive-deps in Safety hazard components

**What to build:** Fix all React hooks dependency warnings in Safety hazard-related components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] safety/HazardLedgerPage.tsx has no exhaustive-deps warnings
- [ ] safety/HazardLedgerPanel.tsx has no exhaustive-deps warnings
- [ ] safety/HazardSelectModal.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
