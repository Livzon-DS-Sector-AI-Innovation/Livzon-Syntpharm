# 46.3 — Fix exhaustive-deps in Registration ledger

**What to build:** Fix all React hooks dependency warnings in Registration ledger page so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] registration/ledger/page.tsx has no exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes for this file
