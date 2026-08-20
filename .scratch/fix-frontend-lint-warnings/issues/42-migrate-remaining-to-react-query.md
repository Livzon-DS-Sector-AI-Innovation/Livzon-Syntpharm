# 42 — Migrate remaining modules to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in remaining modules (production, quality, registration, etc.) to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** ready-for-agent

- [ ] All data fetching in remaining modules uses useQuery/useMutation
- [ ] Loading/error state managed by React Query
- [ ] No useEffect + setState patterns for data fetching
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in remaining modules)
- [ ] Manual smoke test: remaining pages load data correctly
