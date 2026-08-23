# 34.13 — Type HR employee actions

**What to build:** Type all HR employee-related action functions (fetchEmployees, createEmployee, updateEmployee, deleteEmployee, uploadEmployeePhoto, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/hr.ts (employee section)

## Acceptance Criteria

- [ ] All HR employee action functions have explicit return types
- [ ] All `as any` type assertions removed from employee functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in employee functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
