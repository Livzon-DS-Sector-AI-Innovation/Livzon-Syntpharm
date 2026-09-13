# 02 — Remove unused vars in src/app/(dashboard)/equipment/

**What to build:** Delete all unused imports and variables in equipment dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** No unused variables found in equipment directory. ESLint analysis shows zero `@typescript-eslint/no-unused-vars` warnings in this directory.

- [x] All unused imports removed from equipment pages
- [x] All unused variables removed from equipment pages
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (warning count decreases)

**Verification:**
```
ESLint analysis of src/app/(dashboard)/equipment/:
- @typescript-eslint/no-unused-vars: 0 warnings
- @typescript-eslint/no-explicit-any: 2 warnings (ticket 03/04)
```
