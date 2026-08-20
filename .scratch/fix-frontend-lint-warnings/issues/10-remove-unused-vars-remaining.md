# 10 — Remove unused vars in remaining directories/

**What to build:** Delete all unused imports and variables in remaining files (types, utils, etc.). No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All unused imports removed from remaining files
- [ ] All unused variables removed from remaining files
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (warning count decreases)
