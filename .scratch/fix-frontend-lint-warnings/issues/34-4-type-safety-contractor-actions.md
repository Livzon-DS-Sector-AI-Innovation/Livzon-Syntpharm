# 34.4 — Type safety contractor actions

**What to build:** Type all safety contractor-related action functions (getContractors, createContractor, updateContractor, deleteContractor, getContractorWorkRecords, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/safety/index.ts (Contractor section)

## Acceptance Criteria

- [ ] All safety contractor action functions have explicit return types
- [ ] All `as any` type assertions removed from contractor functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in contractor functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
