# 68 — Flip `@typescript-eslint/no-explicit-any` rule to error

**What to build:** After all `any` types have been eliminated from the codebase (tickets 62.1-62.5), flip the ESLint rule from "warn" to "error" to prevent regression. This ensures that any new `any` usage will fail CI immediately. Keep the `eslint-disable` comments from ticket 59 for `apiFetch` and related server API functions where the blast radius is too large.

**Blocked by:** Tickets 62.1, 62.2, 62.3, 62.4, 62.5 (all must complete first)

**Status:** ready-for-agent

- [ ] `@typescript-eslint/no-explicit-any` rule changed from "warn" to "error" in `eslint.config.mjs`
- [ ] `eslint-disable` comments from ticket 59 retained for `apiFetch` and server API functions
- [ ] `pnpm lint` passes with 0 errors and 0 warnings (except for the eslint-disable cases)
- [ ] `tsc --noEmit` passes with no errors
- [ ] CI will now fail on any new `any` usage
