# 45.14 — Fix exhaustive-deps in Energy DeviceDrawer

**What to build:** Fix all React hooks dependency warnings in Energy device drawer component so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] energy/DeviceDrawer.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for this file

**Notes:**
- Wrapped loadDeviceData in useCallback with dependencies [form, message]
- Moved loadDeviceData before useEffect to avoid 'used before declaration' error
- Added loadDeviceData to useEffect dependency array
- All exhaustive-deps warnings resolved
