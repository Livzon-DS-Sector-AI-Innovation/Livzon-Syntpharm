# 38 — Migrate energy data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in energy pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** done

- [x] All data fetching in energy pages uses useQuery/useMutation
- [x] Loading/error state managed by React Query
- [x] No useEffect + setState patterns for data fetching
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in energy)
- [x] Manual smoke test: energy pages load data correctly
