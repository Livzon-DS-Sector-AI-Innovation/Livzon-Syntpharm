# 46.2 — Fix exhaustive-deps in Quality instrument module

**What to build:** Fix all React hooks dependency warnings in Quality instrument edit page so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] quality/instrument/list/edit/page.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for this file
