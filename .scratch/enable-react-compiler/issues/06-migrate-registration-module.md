# 06 — Migrate registration module to canonical React patterns

**What to build:** Eliminate the 1 `set-state-in-effect` warning in the registration module by migrating the AI fill panel to proper React patterns. After this ticket, all registration module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] The 1 `set-state-in-effect` warning in registration module eliminated
- [ ] AI fill panel uses proper state patterns
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in registration module
- [ ] Manual smoke test confirms no behavioral regression in registration pages
