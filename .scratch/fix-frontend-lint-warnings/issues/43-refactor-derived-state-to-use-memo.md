# 43 — Refactor derived state to useMemo

**What to build:** Convert sync useEffect + setState patterns (where state is derived from other state/props) to useMemo. Derived state is computed during render, not in effects.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** ready-for-agent

- [ ] All sync derived state computed with useMemo instead of useEffect + setState
- [ ] Dependencies properly specified
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings for derived state)
