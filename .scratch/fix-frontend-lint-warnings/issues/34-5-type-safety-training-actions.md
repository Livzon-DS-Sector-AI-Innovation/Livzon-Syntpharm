# 34.5 — Type safety training actions

**What to build:** Type all safety training-related action functions (getTrainings, createTraining, updateTraining, deleteTraining, getTrainingRecords, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (SafetyTraining section)

## Acceptance Criteria

- [ ] All safety training action functions have explicit return types
- [ ] All `as any` type assertions removed from training functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in training functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
