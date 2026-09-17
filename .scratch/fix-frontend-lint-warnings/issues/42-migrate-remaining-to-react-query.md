# 42 — Migrate remaining modules to React Query

**What to build:** Convert all useEffect + setState data fetching patterns in remaining modules (production, quality, registration, etc.) to useQuery/useMutation. Eliminates set-state-in-effect warnings.

**Blocked by:** Ticket 35 (global QueryClientProvider)

**Status:** done

- [x] All data fetching in remaining modules uses useQuery/useMutation
- [x] Loading/error state managed by React Query
- [x] No useEffect + setState patterns for data fetching
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings in remaining modules)
- [x] Manual smoke test: remaining pages load data correctly

**Completed modules:**
- Production (13 files)
- Quality (27 files)
- Registration (14 files)
- Energy (12 files)
- Equipment (6 files)
- HR (5 files)
- Settings (4 files)
- Safety (51 files)

**Total:** 132 files migrated from useEffect+useState to React Query
