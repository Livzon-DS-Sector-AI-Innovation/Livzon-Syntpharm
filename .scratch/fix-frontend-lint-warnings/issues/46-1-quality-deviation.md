# 46.1 — Fix exhaustive-deps in Quality deviation modules

**What to build:** Fix all React hooks dependency warnings in Quality deviation-related pages so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] deviation-automation/preview/[id]/page.tsx has no exhaustive-deps warnings
- [ ] deviation-automation/templates/page.tsx has no exhaustive-deps warnings
- [ ] deviation-flow/create/page.tsx has no exhaustive-deps warnings
- [ ] deviation-flow/progress/page.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
