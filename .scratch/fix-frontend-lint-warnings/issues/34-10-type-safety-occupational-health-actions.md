# 34.10 — Type safety occupational health actions

**What to build:** Type all safety occupational health action functions (getOhHazardMonitors, createOhHazardMonitor, updateOhHazardMonitor, getOhHealthExams, createOhHealthExam, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (OccupationalHealth sections)

## Acceptance Criteria

- [ ] All safety occupational health action functions have explicit return types
- [ ] All `as any` type assertions removed from occupational health functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in occupational health functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
