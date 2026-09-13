# 53 — Remove unused vars in equipment components

**What to build:** Remove all unused imports and variables from `src/components/equipment/` directory. This includes 46 unused variables across multiple equipment-related component files.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from equipment components
- [x] All unused variables removed from equipment components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in equipment components
- [x] No functional changes to equipment features

## Summary

Fixed 46 unused vars across 36 files in src/components/equipment/:
- Removed unused imports (icons, types, components)
- Prefixed unused props/params with _ in destructuring
- Removed unused interfaces (StaffOption)

All equipment components now have zero unused vars warnings.
