# 06 — Remove unused vars in src/app/(dashboard)/registration/

**What to build:** Delete all unused imports and variables in registration dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** in-progress

**Progress:**
- Removed unused `renderBorderBar` function from regulation/list/page.tsx (commit 1e9f3ab)
- Remaining: 7 unused type imports in ledger/page.tsx (lines 15-16)

**Remaining work:**
- Remove unused type imports: DomesticApproval, OverseasApproval, InternationalReview, CoppCertificate, WcCertificate, ReviewingDrug from ledger/page.tsx

- [ ] Remove unused type imports from ledger/page.tsx
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (warning count decreases)
