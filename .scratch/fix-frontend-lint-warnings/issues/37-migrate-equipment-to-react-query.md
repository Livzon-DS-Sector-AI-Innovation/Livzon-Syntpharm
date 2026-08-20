# 37 — Migrate equipment data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in equipment pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** ready-for-agent

- [ ] All data fetching in equipment pages uses useQuery/useMutation
- [ ] Loading/error state managed by React Query
- [ ] No useEffect + setState patterns for data fetching
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in equipment)
- [ ] Manual smoke test: equipment pages load data correctly
