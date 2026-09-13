# 52 — Remove unused vars in safety components

**What to build:** Remove all unused imports and variables from `src/components/safety/` directory. This includes 98 unused variables across multiple safety-related component files.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from safety components
- [x] All unused variables removed from safety components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in safety components
- [x] No functional changes to safety features

## Summary

Fixed 98 unused vars across safety components in two commits:
- First commit (642e282): Fixed 72 vars
- Second commit (d9b6019): Fixed remaining 26 vars

All safety components now have zero unused vars warnings.
