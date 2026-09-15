# 45.15 — Fix exhaustive-deps in HR training modules

**What to build:** Fix all React hooks dependency warnings in HR training components so that useEffect and useCallback hooks have complete dependency arrays, preventing stale closures and ensuring proper reactivity.

**Blocked by:** None — can start immediately

**Status:** done

- [x] hr/TrainingSelectClient.tsx has no exhaustive-deps warnings
- [x] hr/TrainingSessionDetailModal.tsx has no exhaustive-deps warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes for these files

**Notes:**
- TrainingSelectClient.tsx: Wrapped loadEmployees in useCallback with [isNew] dependency
- TrainingSelectClient.tsx: Moved loadEmployees before useEffect to avoid 'used before declaration' error
- TrainingSelectClient.tsx: Added loadEmployees to useEffect dependency array
- TrainingSessionDetailModal.tsx: Added startEditing to useEffect dependency array
- All exhaustive-deps warnings resolved in both files
