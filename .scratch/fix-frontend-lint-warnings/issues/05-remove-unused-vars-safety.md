# 05 — Remove unused vars in src/app/(dashboard)/safety/

**What to build:** Delete all unused imports and variables in safety dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** in-progress

**Progress:**
- Identified 145 unused variables across 12 files
- Files affected: accident, check, contractor, ehs-change, hazard-identification-legacy, hazard-identification/[id], hazard-legacy, hazard/[id], knowledge-base, occupational-health, regulation, training

**Remaining work:**
- Remove unused imports and variables from all 12 files
- Requires careful editing to avoid breaking import statements

**Files to fix:**
1. accident/page.tsx - 6 unused vars
2. check/page.tsx - 1 unused var
3. contractor/page.tsx - 5 unused vars
4. ehs-change/page.tsx - 9 unused vars
5. hazard-identification-legacy/page.tsx - 46 unused vars (entire file appears unused)
6. hazard-identification/[id]/page.tsx - 5 unused vars
7. hazard-legacy/page.tsx - 30+ unused vars (entire file appears unused)
8. hazard/[id]/page.tsx - 10+ unused vars
9. knowledge-base/page.tsx - 10+ unused vars
10. occupational-health/page.tsx - 5+ unused vars
11. regulation/page.tsx - 5+ unused vars
12. training/page.tsx - 5+ unused vars

- [ ] Remove unused vars from all safety files
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (warning count decreases)
