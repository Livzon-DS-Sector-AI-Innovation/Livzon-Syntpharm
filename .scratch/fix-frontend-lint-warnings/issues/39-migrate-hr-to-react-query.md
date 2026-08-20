# 39 — Migrate hr data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in hr pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** ready-for-agent

- [ ] All data fetching in hr pages uses useQuery/useMutation
- [ ] Loading/error state managed by React Query
- [ ] No useEffect + setState patterns for data fetching
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in hr)
- [ ] Manual smoke test: hr pages load data correctly
