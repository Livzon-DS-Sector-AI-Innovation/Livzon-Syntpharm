# 07 — Enable React Compiler and flip set-state-in-effect rule to error

**What to build:** After all modules have been migrated to canonical React patterns, enable React Compiler in next.config.ts and flip the `react-hooks/set-state-in-effect` ESLint rule from "warn" to "error". This ensures that any future violations will fail CI immediately, preventing regression. After this ticket, the codebase has zero lint warnings and React Compiler is actively optimizing component rendering.

**Blocked by:** Tickets 01, 02, 03, 04, 05, 06 (all module migrations must complete first)

**Status:** ready-for-agent

- [ ] React Compiler enabled in next.config.ts (`reactCompiler: true`)
- [ ] `react-hooks/set-state-in-effect` rule changed from "warn" to "error" in eslint.config.mjs
- [ ] `pnpm lint` passes with 0 errors and 0 warnings
- [ ] `pnpm typecheck` passes with 0 errors
- [ ] `pnpm build` succeeds with React Compiler optimizations
- [ ] CI will now fail on any new `set-state-in-effect` violations
- [ ] Manual smoke test confirms no behavioral regression across all modules
