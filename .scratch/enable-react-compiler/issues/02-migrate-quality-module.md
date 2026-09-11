# 02 — Migrate quality module to canonical React patterns

**What to build:** Eliminate all 6 `set-state-in-effect` warnings in the quality module by migrating CPV/CPP batch data pages and deviation flow pages to React Query and proper state patterns. After this ticket, all quality module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All 6 `set-state-in-effect` warnings in quality module eliminated
- [ ] CPV/CPP batch data pages use React Query for data fetching
- [ ] Deviation flow pages use proper state patterns
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in quality module
- [ ] Manual smoke test confirms no behavioral regression in quality pages
