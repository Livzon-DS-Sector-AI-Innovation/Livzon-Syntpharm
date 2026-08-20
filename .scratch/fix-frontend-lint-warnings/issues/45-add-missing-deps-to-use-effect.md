# 45 — Add missing deps to useEffect (exhaustive-deps)

**What to build:** Add all missing dependencies to useEffect dependency arrays. Stabilize function deps with useCallback where needed.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** ready-for-agent

- [ ] All useEffect hooks have complete dependency arrays
- [ ] Missing deps added
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/exhaustive-deps warnings)
