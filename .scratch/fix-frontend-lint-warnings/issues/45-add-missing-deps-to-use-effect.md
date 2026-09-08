# 45 — Add missing deps to useEffect (exhaustive-deps)

**What to build:** Add all missing dependencies to useEffect dependency arrays. Stabilize function deps with useCallback where needed.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** done

- [x] All useEffect hooks have complete dependency arrays
- [x] Missing deps added
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/exhaustive-deps warnings)

**Notes:**
- All sub-tickets (45.1-45.21) completed successfully
- Fixed exhaustive-deps warnings across all modules: equipment, hr, quality, research, safety, registration, energy, production
- Wrapped async functions in useCallback with proper dependencies
- Added missing dependencies to useEffect arrays
- Zero exhaustive-deps warnings remaining
