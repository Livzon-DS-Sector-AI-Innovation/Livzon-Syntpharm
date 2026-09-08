# 45.13 — Fix exhaustive-deps in Registration ledger

**What to build:** Fix all React hooks dependency warnings in Registration ledger page so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] registration/ledger/page.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for this file

**Notes:**
- Added 'message' to useCallback dependency array
- All exhaustive-deps warnings resolved
