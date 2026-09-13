# 45.12 — Fix exhaustive-deps in Quality instrument module

**What to build:** Fix all React hooks dependency warnings in Quality instrument edit page so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] quality/instrument/list/edit/page.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for this file

**Notes:**
- Wrapped loadData in useCallback with dependencies [instrumentId, form, ruleForm, router]
- Moved loadData declaration before useEffect to avoid 'used before declaration' error
- Added loadData to useEffect dependency array
- All exhaustive-deps warnings resolved
