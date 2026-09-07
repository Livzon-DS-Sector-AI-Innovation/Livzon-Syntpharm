# 45.3 — Fix exhaustive-deps in Quality module (Part 1)

**What to build:** Fix all React hooks dependency warnings in the Quality module core pages so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] ai-log/page.tsx has no exhaustive-deps warnings
- [ ] stability/page.tsx has no exhaustive-deps warnings
- [ ] static-data/[module]/[id]/page.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for these files
