# 34.34 — Type validation-audit actions

**What to build:** Type all validation-audit action functions in src/actions/validation-audit.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/validation-audit.ts

## Acceptance Criteria

- [ ] All validation-audit action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
