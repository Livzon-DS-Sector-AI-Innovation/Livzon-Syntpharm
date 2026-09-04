# 40 — Migrate safety data fetching to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in safety pages to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** ready-for-agent

**Note:** Initial migration attempt was reverted due to duplicate variable declaration errors. The safety module has complex state management with Zustand store integration that requires careful refactoring. This ticket remains open for future completion.

- [ ] All data fetching in safety pages uses useQuery/useMutation
- [ ] Loading/error state managed by React Query
- [ ] No useEffect + setState patterns for data fetching
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in safety)
- [ ] Manual smoke test: safety pages load data correctly
