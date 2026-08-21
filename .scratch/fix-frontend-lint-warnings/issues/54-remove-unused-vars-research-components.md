# 54 — Remove unused vars in research components

**What to build:** Remove all unused imports and variables from `src/components/research/` directory. This includes 42 unused variables across multiple research-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from research components
- [ ] All unused variables removed from research components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in research components
- [ ] No functional changes to research features
