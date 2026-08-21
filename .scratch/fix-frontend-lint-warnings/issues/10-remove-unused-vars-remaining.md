# 10 — Remove unused vars in remaining directories/

**What to build:** Delete all unused imports and variables in remaining files (types, utils, etc.). No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** in-progress

**Progress:**
- Part 1: Fixed 23 unused vars in hooks/stores/types/lib (11 files)
- Part 2: Fixed 22 unused vars in app pages (4 files)
- Total fixed: 45 vars
- Remaining: ~180 vars in app/ directory (mostly quality/ pages)

**Remaining work:**
- Continue fixing unused vars in quality/ pages (42 files remaining)
- Most files have 5-17 unused vars each
- Common patterns: unused imports, unused catch variables, unused state setters

- [ ] All unused imports removed from remaining files
- [ ] All unused variables removed from remaining files
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (warning count decreases)
