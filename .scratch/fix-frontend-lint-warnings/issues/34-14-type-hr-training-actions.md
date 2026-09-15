# 34.14 — Type HR training actions

**What to build:** Type all HR training-related action functions (fetchTrainingRecords, fetchTrainingPlans, createTrainingRecord, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/hr.ts (training section)

## Acceptance Criteria

- [ ] All HR training action functions have explicit return types
- [ ] All `as any` type assertions removed from training functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in training functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
