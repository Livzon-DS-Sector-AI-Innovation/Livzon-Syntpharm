# 55 — Remove unused vars in registration components

**What to build:** Remove all unused imports and variables from `src/components/registration/` directory. This includes 35 unused variables across multiple registration-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from registration components
- [ ] All unused variables removed from registration components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in registration components
- [ ] No functional changes to registration features
