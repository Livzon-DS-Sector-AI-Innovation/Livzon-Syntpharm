# 01 — Migrate safety module to canonical React patterns

**What to build:** Eliminate all 15 `set-state-in-effect` warnings in the safety module by migrating data fetching to React Query, derived state to useMemo, and form initialization to controlled patterns. This covers hazard management, regulation management, special operations, knowledge base, SOP editor, and scheduled tasks pages. After this ticket, all safety module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All 15 `set-state-in-effect` warnings in safety module eliminated
- [ ] Data fetching uses React Query with proper cache invalidation
- [ ] Derived state uses useMemo instead of useEffect + setState
- [ ] Form initialization uses controlled components or useMemo
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in safety module
- [ ] Manual smoke test confirms no behavioral regression in safety pages
