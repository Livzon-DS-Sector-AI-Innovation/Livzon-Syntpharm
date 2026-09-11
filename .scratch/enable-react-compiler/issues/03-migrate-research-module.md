# 03 — Migrate research module to canonical React patterns

**What to build:** Eliminate all 2 `set-state-in-effect` warnings in the research module by migrating stage module layout and deliverable template page to useMemo and proper form patterns. After this ticket, all research module pages follow React Compiler-compatible patterns with no cascading renders from useEffect.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All 2 `set-state-in-effect` warnings in research module eliminated
- [ ] Stage module layout uses useMemo for filtering
- [ ] Deliverable template page uses proper form patterns
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm lint` shows 0 `set-state-in-effect` warnings in research module
- [ ] Manual smoke test confirms no behavioral regression in research pages
