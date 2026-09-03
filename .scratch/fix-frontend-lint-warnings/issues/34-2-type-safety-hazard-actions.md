# 34.2 — Type safety hazard actions

**What to build:** Type all safety hazard-related action functions (getHazards, createHazard, updateHazard, fetchHazardStats, uploadHazardPhoto, getDepartmentLeader, getDepartmentSafetyOfficer, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (HazardReport section)

## Acceptance Criteria

- [ ] All safety hazard action functions have explicit return types
- [ ] All `as any` type assertions removed from hazard functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in hazard functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
