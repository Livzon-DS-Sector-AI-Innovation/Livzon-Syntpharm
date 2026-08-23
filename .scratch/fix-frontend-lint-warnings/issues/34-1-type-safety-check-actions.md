# 34.1 — Type safety check actions

**What to build:** Type all safety check-related action functions (getChecks, createCheck, updateCheck, submitCheck, reviewCheck, deleteCheck, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/safety/index.ts (SafetyCheck section)

## Acceptance Criteria

- [ ] All safety check action functions have explicit return types
- [ ] All `as any` type assertions removed from check functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in check functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
