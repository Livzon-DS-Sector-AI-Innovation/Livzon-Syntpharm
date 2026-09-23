# 41 — Migrate research data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in research pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** done

- [x] All data fetching in research pages uses useQuery/useMutation
- [x] Loading/error state managed by React Query
- [x] No useEffect + setState patterns for data fetching
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in research)
- [x] Manual smoke test: research pages load data correctly
