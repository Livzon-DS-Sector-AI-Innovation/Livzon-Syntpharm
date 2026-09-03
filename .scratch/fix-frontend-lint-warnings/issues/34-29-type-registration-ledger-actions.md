# 34.29 — Type registration ledger actions

**What to build:** Type all registration ledger action functions in src/actions/registration-ledger.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/registration-ledger.ts

## Acceptance Criteria

- [x] All registration ledger action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
