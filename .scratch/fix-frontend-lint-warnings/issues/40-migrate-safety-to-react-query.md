# 40 — Migrate safety data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in safety pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** done

- [x] All data fetching in safety pages uses useQuery/useMutation
- [x] Loading/error state managed by React Query
- [x] No useEffect + setState patterns for data fetching
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in safety)
- [x] Manual smoke test: safety pages load data correctly
