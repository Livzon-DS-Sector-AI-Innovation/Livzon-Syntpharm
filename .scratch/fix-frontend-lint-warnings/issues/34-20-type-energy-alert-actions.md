# 34.20 — Type energy alert actions

**What to build:** Type all energy alert action functions in src/actions/energy.ts (alert-related functions)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/energy.ts (alert section)

## Acceptance Criteria

- [ ] All energy alert action functions have explicit return types
- [ ] All `as any` type assertions removed from alert functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in alert functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
