# 04 — Migrate production module to canonical React patterns

**What to build:** Eliminate all 4 `set-state-in-effect` warnings in the production module by migrating annual review, workshop ranking, pressure input, and product output pages to proper React patterns. After this ticket, all production module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All 4 `set-state-in-effect` warnings in production module eliminated
- [ ] Annual review and workshop ranking use proper state patterns
- [ ] Pressure input and product output pages use proper patterns
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in production module
- [ ] Manual smoke test confirms no behavioral regression in production pages
