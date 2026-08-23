# 34.9 — Type safety EHS change actions

**What to build:** Type all safety EHS change action functions (getEhsChanges, createEhsChange, updateEhsChange, deleteEhsChange, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/safety/index.ts (EhsChange section)

## Acceptance Criteria

- [ ] All safety EHS change action functions have explicit return types
- [ ] All `as any` type assertions removed from EHS change functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in EHS change functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
