# 34.35 — Type product actions

**What to build:** Type all product action functions in src/actions/product.ts, src/actions/product-output.ts, and src/actions/product-sync.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/product.ts, src/actions/product-output.ts, src/actions/product-sync.ts

## Acceptance Criteria

- [ ] All product action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
