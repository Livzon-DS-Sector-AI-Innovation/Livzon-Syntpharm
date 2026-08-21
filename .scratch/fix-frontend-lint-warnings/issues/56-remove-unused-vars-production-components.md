# 56 — Remove unused vars in production components

**What to build:** Remove all unused imports and variables from `src/components/production/` directory. This includes 17 unused variables across multiple production-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from production components
- [ ] All unused variables removed from production components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in production components
- [ ] No functional changes to production features
