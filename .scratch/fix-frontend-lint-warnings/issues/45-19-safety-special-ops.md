# 45.19 — Fix exhaustive-deps in Safety special ops components

**What to build:** Fix all React hooks dependency warnings in Safety special operations components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] safety/SpecialOpsLedger.tsx has no exhaustive-deps warnings
- [x] safety/SpecialOpsManagement.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- SpecialOpsLedger.tsx: Added 'message' to useCallback dependency array
- SpecialOpsManagement.tsx: Added 'message' to useCallback dependency array
- All exhaustive-deps warnings resolved in both files
