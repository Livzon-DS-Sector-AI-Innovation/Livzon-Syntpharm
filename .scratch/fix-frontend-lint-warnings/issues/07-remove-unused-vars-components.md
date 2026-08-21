# 07 — Remove unused vars in src/components/

**What to build:** Delete all unused imports and variables in component files. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** in-progress

**Progress:**
- Identified 267 unused variables across 111 files in components directory
- Breakdown by subdirectory:
  - safety: 98 unused vars
  - equipment: 46 unused vars
  - research: 42 unused vars
  - registration: 35 unused vars
  - production: 17 unused vars
  - hr: 14 unused vars
  - energy: 10 unused vars
  - layout: 2 unused vars
  - quality: 2 unused vars
  - administration: 1 unused var

**Approach:**
- Need to be more careful with sed commands to avoid breaking imports
- Should test typecheck after each batch of changes
- May need to use more specific patterns or manual editing for complex cases

**Remaining work:**
- Fix all 267 unused vars across 111 files
- Ensure typecheck passes after each batch
- Verify no functional changes

- [ ] All unused imports removed from components
- [ ] All unused variables removed from components
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (warning count decreases)
