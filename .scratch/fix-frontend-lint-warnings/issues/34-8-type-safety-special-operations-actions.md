# 34.8 — Type safety special operations actions

**What to build:** Type all safety special operations action functions (getSpecialOperationPermits, createSpecialOperationPermit, updateSpecialOperationPermit, getSpecialOperationPersonnel, getSpecialOperationReports, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (SpecialOperation sections)

## Acceptance Criteria

- [ ] All safety special operations action functions have explicit return types
- [ ] All `as any` type assertions removed from special operations functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in special operations functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
