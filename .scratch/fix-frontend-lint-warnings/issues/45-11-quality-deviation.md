# 45.11 — Fix exhaustive-deps in Quality deviation modules

**What to build:** Fix all React hooks dependency warnings in Quality deviation-related pages so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] deviation-automation/preview/[id]/page.tsx has no exhaustive-deps warnings
- [x] deviation-automation/templates/page.tsx has no exhaustive-deps warnings
- [x] deviation-flow/create/page.tsx has no exhaustive-deps warnings
- [x] deviation-flow/progress/page.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- Wrapped all async functions in useCallback with proper dependencies
- Moved function declarations before useEffect hooks to avoid "used before declaration" errors
- All exhaustive-deps warnings resolved in these 4 files
