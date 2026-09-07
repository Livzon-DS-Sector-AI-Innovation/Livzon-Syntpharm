# 46.5 — Fix exhaustive-deps in HR training modules

**What to build:** Fix all React hooks dependency warnings in HR training components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] hr/TrainingSelectClient.tsx has no exhaustive-deps warnings
- [ ] hr/TrainingSessionDetailModal.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
