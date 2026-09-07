# 45.2 — Fix exhaustive-deps in HR module

**What to build:** Fix all React hooks dependency warnings in the HR module so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] DepartureClient.tsx has no exhaustive-deps warnings
- [x] OnboardingClient.tsx has no exhaustive-deps warnings
- [x] RosterClient.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for HR module files
