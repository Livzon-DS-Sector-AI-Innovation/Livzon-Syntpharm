# 34.15 — Type HR annual training plan actions

**What to build:** Type all HR annual training plan action functions (fetchAnnualTrainingPlans, createAnnualTrainingPlan, updateAnnualTrainingPlan, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/hr.ts (annual training plan section)

## Acceptance Criteria

- [ ] All HR annual training plan action functions have explicit return types
- [ ] All `as any` type assertions removed from annual training plan functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in annual training plan functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
