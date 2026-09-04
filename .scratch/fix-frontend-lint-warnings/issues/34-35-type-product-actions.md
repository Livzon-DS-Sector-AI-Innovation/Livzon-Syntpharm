# 34.35 — Type product actions

**What to build:** Type all product action functions in src/actions/product.ts, src/actions/product-output.ts, and src/actions/product-sync.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/product.ts, src/actions/product-output.ts, src/actions/product-sync.ts

## Acceptance Criteria

- [x] All product action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
