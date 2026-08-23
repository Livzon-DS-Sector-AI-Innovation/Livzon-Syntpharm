# 34.3 — Type safety accident actions

**What to build:** Type all safety accident-related action functions (getAccidents, createAccident, updateAccident, deleteAccident, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/safety/index.ts (Accident section)

## Acceptance Criteria

- [ ] All safety accident action functions have explicit return types
- [ ] All `as any` type assertions removed from accident functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in accident functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
