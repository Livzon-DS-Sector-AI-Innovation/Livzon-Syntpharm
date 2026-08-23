# 34.19 — Type energy device actions

**What to build:** Type all energy device action functions in src/actions/energy.ts (device-related functions)

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/energy.ts (device section)

## Acceptance Criteria

- [ ] All energy device action functions have explicit return types
- [ ] All `as any` type assertions removed from device functions
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings in device functions
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
