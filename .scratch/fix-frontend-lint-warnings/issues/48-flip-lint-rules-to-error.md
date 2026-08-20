# 48 — Flip lint rules from warn to error

**What to build:** Change all ESLint rules in eslint.config.mjs from "warn" to "error". This makes lint violations fail the build.

**Blocked by:** Ticket 47 (zero warnings achieved, React Compiler enabled)

**Status:** ready-for-agent

- [ ] All ESLint rules in eslint.config.mjs set to "error"
- [ ] `pnpm lint` passes with zero warnings
- [ ] `tsc --noEmit` passes
- [ ] Build completes successfully
