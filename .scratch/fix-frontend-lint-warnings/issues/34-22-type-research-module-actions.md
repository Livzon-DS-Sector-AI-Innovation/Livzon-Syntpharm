# 34.22 — Type research module actions

**What to build:** Type all research module action functions in src/actions/research/modules.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/research/modules.ts

## Acceptance Criteria

- [ ] All research module action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
