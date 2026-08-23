# 34.6 — Type safety regulation actions

**What to build:** Type all safety regulation-related action functions (getRegulations, createRegulation, updateRegulation, deleteRegulation, getRegulationRevisions, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/safety/index.ts (OperationRegulation and RegulationRevision sections)

## Acceptance Criteria

- [ ] All safety regulation action functions have explicit return types
- [ ] All `as any` type assertions removed from regulation functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in regulation functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
