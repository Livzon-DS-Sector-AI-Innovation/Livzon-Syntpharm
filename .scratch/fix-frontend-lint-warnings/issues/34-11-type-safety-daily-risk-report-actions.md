# 34.11 — Type safety daily risk report actions

**What to build:** Type all safety daily risk report action functions (getDailyRiskReports, createDailyRiskReport, updateDailyRiskReport, deleteDailyRiskReport, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (DailyRiskReport section)

## Acceptance Criteria

- [ ] All safety daily risk report action functions have explicit return types
- [ ] All `as any` type assertions removed from daily risk report functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in daily risk report functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
