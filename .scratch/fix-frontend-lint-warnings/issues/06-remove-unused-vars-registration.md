# 06 — Remove unused vars in src/app/(dashboard)/registration/

**What to build:** Delete all unused imports and variables in registration dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Removed all unused variables from registration directory.

**Changes made:**
1. regulation/list/page.tsx: Removed unused `renderBorderBar` function (6 lines)
2. ledger/page.tsx: Removed 6 unused type imports (DomesticApproval, OverseasApproval, InternationalReview, CoppCertificate, WcCertificate, ReviewingDrug)

**Verification:**
- [x] All unused imports removed from registration pages
- [x] All unused variables removed from registration pages
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (0 no-unused-vars warnings in registration directory)

**Commits:**
- 1e9f3ab: fix: remove unused renderBorderBar function in regulation list
- ad83766: fix: remove unused type imports in registration ledger
