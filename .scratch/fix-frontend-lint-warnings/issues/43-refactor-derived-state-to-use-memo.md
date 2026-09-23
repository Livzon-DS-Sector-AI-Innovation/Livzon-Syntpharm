# 43 — Refactor derived state to useMemo

**What to build:** Convert sync useEffect + setState patterns (where state is derived from other state/props) to useMemo. Derived state is computed during render, not in effects.

**Blocked by:** Tickets 36-42 (data fetching migrated)

**Status:** done

- [x] All sync derived state computed with useMemo instead of useEffect + setState
- [x] Dependencies properly specified
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no react-hooks/set-state-in-effect warnings for derived state)

**Notes:**
After analysis, no pure derived state patterns were found in the codebase. All remaining useEffect + setState usages are legitimate:
- Data fetching (async operations)
- Side effects (form manipulation, DOM updates)
- Animations/timers (setInterval-based UI effects)
- Event handlers (user-triggered state updates)

These are correct useEffect use cases and should not be replaced with useMemo.
