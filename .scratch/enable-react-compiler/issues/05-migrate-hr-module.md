# 05 — Migrate HR module to canonical React patterns

**What to build:** Eliminate all 2 `set-state-in-effect` warnings in the HR module by migrating training select and session detail pages to proper React patterns. After this ticket, all HR module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All 2 `set-state-in-effect` warnings in HR module eliminated
- [ ] Training select page uses proper state patterns
- [ ] Session detail page uses proper state patterns
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in HR module
- [ ] Manual smoke test confirms no behavioral regression in HR pages
