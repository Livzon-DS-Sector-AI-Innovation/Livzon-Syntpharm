# 04 — Remove unused vars in src/app/(dashboard)/hr/

**What to build:** Delete all unused imports and variables in hr dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** No unused variables found in hr directory. ESLint analysis shows zero `@typescript-eslint/no-unused-vars` warnings in this directory.

- [x] All unused imports removed from hr pages
- [x] All unused variables removed from hr pages
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (warning count decreases)

**Verification:**
```
ESLint analysis of src/app/(dashboard)/hr/:
- @typescript-eslint/no-unused-vars: 0 warnings
- @typescript-eslint/no-explicit-any: 9 warnings (ticket 03/04)
```
